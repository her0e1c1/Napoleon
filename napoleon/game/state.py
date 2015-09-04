import enum
import logging
from napoleon import card
from napoleon.game.adaptor import RedisAdaptor


logger = logging.getLogger(__name__)


class GameStateWithSession(object):

    def __init__(self, room_id, user_id, session_id):
        self.state = GameState(room_id)
        self.privilege = Privilege(Myself(user_id=user_id, session_id=session_id, state=self.state))

    def __getattr__(self, name):
        if getattr(self.privilege, name, None) is not False:
            return getattr(self.state, name)


class Privilege(object):

    def __init__(self, player):
        self.player = player

    # for a game state instance
    @property
    def rest(self):
        return self.player.is_napoleon

    # for a player instance
    @property
    def role(self):
        if self.state.phase == "finished" or self.is_valid:
            return True
        else:
            return False


class Myself(object):

    def __init__(self, state, session_id, user_id=None):
        if user_id is None:
            user_id = get_user_id(state.room_id, session_id)
        self.player = Player(user_id, state)
        self.session_id = session_id
        self.privilege = Privilege(self.player)

    def __getattr__(self, name):
        if getattr(self.privilege, name, None) is not False:
            return getattr(self.player, name)

    @property
    def is_valid(self):
        try:
            get_user_id(self.player.state.room_id, self.session_id)
        except InvalidSession:
            return False
        else:
            return True


class InvalidSession(Exception):
    pass


class JsonMixin(object):
    attrs = []
    def to_json(self):
        for a in self.attrs:
            pass
        return {}


def to_json(obj):
    if isinstance(obj, list):
        return [to_json(o) for o in obj]
    elif isinstance(obj, dict):
        return {k: to_json(v) for k, v in obj.items()}
    elif hasattr(obj, "to_json"):
        return obj.to_json()
    else:
        return obj
        # raise ValueError("You can't convert %s to json" % obj)


class Role(enum.Enum):
    napoleon_forces = 1
    allied_forces = 2


def get_user_id(room_id, session_id):
    adaptor = RedisAdaptor(room_id)
    user_dict = adaptor.get_dict("map")
    inv = {v: k for k, v in user_dict.items()}
    user_id = inv.get(session_id)
    if not user_id:
        raise InvalidSession("Session is invalid")
    return int(user_id)


class User(object):

    def __init__(self, user_id, session_id, state):
        """
        Make sure user id is valid.
        """
        self.adaptor = RedisAdaptor(room_id=state.room_id, user_id=user_id)
        self.user_id = user_id
        self.session_id = session_id
        self.state = state

    def join(self):
        self.adaptor.set_list("player_ids", self.user_id, delete=False)
        self.adaptor.set_dict("map", self.user_id, self.session_id)

    def quit(self, force=False):
        self.adaptor.rem_list("player_ids", self.user_id, delete=True)
        self.adaptor.rem_dict("map", self.user_id)

    def reset(self):
        self.quit(force=True)
        self.join()


class Player(object):

    def __init__(self, user_id, state):
        self.adaptor = RedisAdaptor(room_id=state.room_id, user_id=user_id)
        self.user_id = user_id
        self.state = state

    def __eq__(self, other):
        return self.user_id == other.user_id

    @property
    def is_napoleon(self):
        return self.state.napoleon == self.user_id

    @property
    def is_player(self):
        return self in self.state.players

    @property
    def is_my_turn(self):
        return self == self.state.turn

    def select(self, card):
        """
        A player selects a card
        """
        if self.can_betray(card):
            if self.role == Role.napoleon_forces:
                self.role = Role.allied_forces
            else:
                self.role = Role.napoleon_forces

        self.adaptor.rem_list("hand", int(card))
        self.state.board = card
        self.state.player_cards = (self.user_id, card)

    def can_betray(self, c):
        if (c == card.CLUB10
            and not self.state.board
            and not self.is_napoleon
            and len(self.state.allied_forces) > 1
            # and len(self.state.napoleon_forces) > 1
        ):
            return True
        else:
            return False

    def pass_(self):
        self.adaptor.set_list("pass_ids", self.user_id, delete=False)

    def declare(self, declaration):
        """
        A player declaresf as Napoleon if he calls a larger card.
        """
        d = self.state.declaration
        if not d or int(d) < int(declaration):
            self.state.declaration = declaration
            self.state.napoleon = self.user_id
            self.state.turn = Player(self.user_id, self.state)

    def decide(self, adjutant):
        self.state.adjutant = adjutant

    def discard(self, unused):
        hand = self.hand
        for u in unused:
            try:
                hand.remove(u)
            except ValueError:  # malice request
                # logger
                return

        self.hand = hand
        self.state.unused = unused

    def add_rest_to_hand(self):
        self.hand = self.hand + self.state.rest

    @property
    def number_of_hand(self):
        return len(self.hand)

    @property
    def hand(self):
        # + rest
        ints = self.adaptor.get_list("hand", type=int)
        return card.from_list(ints)

    @hand.setter
    def hand(self, hand):
        self.adaptor.set_list("hand", sorted(int(i) for i in hand))

    @property
    def face(self):
        return self.adaptor.get("face")

    @face.setter
    def face(self, value):
        self.adaptor.set("face", value)

    @property
    def role(self):
        d = self.adaptor.get("role", type=int)
        if d:
            return Role(d)

    @role.setter
    def role(self, role):
        return self.adaptor.set("role", role.value)

    @property
    def possible_cards(self):
        # wait for the next turn before playing a lead card
        if len(self.state.board) == len(self.state.players):
            return self.hand
        d = self.state.declaration
        if d:
            return card.possible_cards(self.state.board, self.hand, d.suit)
        else:
            return []

    def to_json(self):
        d = {}
        return {"p": 1}
        # for key in dir(self):
        #     attr = getattr(self, key)
        #     if not key.startswith("_") and not callable(attr):
        #         d[key] = to_json(attr)
        # return d


class Phase(object):

    def __init__(self, state):
        self.state = state
        self.adaptor = state.adaptor

    @property
    def current(self):
        return self.adaptor.get("phase")

    @current.setter
    def current(self, value):
        self.adaptor.set("phase", value)

    @property
    def waiting_next_turn(self):
        return bool(self.adaptor.get("waiting_next_turn", type=int))

    @waiting_next_turn.setter
    def waiting_next_turn(self, value):
        value = 1 if value else 0
        return self.adaptor.set("waiting_next_turn", value)

    @property
    def is_appropriate_player_number(self):
        return len(self.state.players) in card.RANGE_OF_PLAYERS

    @property
    def is_napoleon_determined(self):
        return bool(self.state.napoleon) and len(self.state.passed_players) >= len(self.state.players) - 1

    @property
    def are_all_players_passed(self):
        return len(self.state.passed_players) == len(self.state.players)

#     @property
#     def is_finished(self):
#         if self.phase != "rounds":
#             return False
#         n = 0
#         for pid in self.player_ids:
#             key = get_key("hand", self.room_id, pid)
#             ints = decode(self.conn.lrange(key, 0, -1), type=int)
#             n += len(ints)
#         return n == 0

#     @property
#     def did_napoleon_win(self):
#         if not self.declaration:
#             return False
#         n, _ = self._each_side_face_cards
#         if n == card.NUMBER_OF_FACE_CARDS:
#             return False
#         return n >= self.declaration.pip

#     @property
#     def did_napoleon_lose(self):
#         if not self.declaration:
#             return False
#         _, n = self._each_side_face_cards
#         if n == 0:
#             return True
#         return n > card.NUMBER_OF_FACE_CARDS - self.declaration.pip

#     @property
#     def _each_side_face_cards(self):
#         napo = 0
#         allies = 0
#         for pid in self.player_ids:
#             key = get_key("role", self.room_id, pid)
#             role = decode(self.conn.get(key), type=int)
#             key = get_key("face", self.room_id, pid)
#             num = decode(self.conn.get(key), type=int)
#             if role == 1:  # napo
#                 napo += num
#             else:
#                 allies += num
#         return napo, allies


class GameState(object):

    def __init__(self, room_id):
        self.adaptor = RedisAdaptor(room_id=room_id)
        self.room_id = room_id
        self._phase = Phase(self)

    def to_json(self):
        d = {}
        for key in dir(self):
            attr = getattr(self, key)
            if not key.startswith("_") and not callable(attr):
                d[key] = to_json(attr)
        return d

    def create_player(self, user_id):
        return Player(user_id, self)

    @property
    def phase(self):
        return self._phase.current

    def flush(self):
        """
        Delete all data about this room.
        """
        self.adaptor.flush()

    def start(self):
        """
        Distribute cards to each player and leave the rest of cards which napoleon can change
        """
        players = list(self.players)
        number_of_players = len(players)
        if number_of_players <= 2:
            raise ValueError

        hands, rest = card.deal(number_of_players)
        self.rest = rest
        for (p, h) in zip(players, hands):
            p.hand = h
            p.face = 0

    def set_role(self, adjutant=None):
        """
        After deciding an adjutant, the role of each player is set
        """
        for p in self.players:
            if p.is_napoleon:
                role = Role.napoleon_forces
            else:
                if self.adjutant in p.hand:
                    role = Role.napoleon_forces
                else:
                    role = Role.allied_forces
            p.role = role

    @property
    def players(self):
        l = []
        for pid in self.adaptor.get_list("player_ids", type=int):
            l.append(Player(user_id=pid, state=self))
        return l

    @property
    def passed_players(self):
        l = []
        for pid in self.adaptor.get_list("pass_ids", type=int):
            l.append(Player(user_id=pid, state=self))
        return l

    @property
    def allied_forces(self):
        return [p for p in self.players if p.role == Role.allied_forces]

    @property
    def rest(self):
        return card.from_list(self.adaptor.get_list("rest", type=int))

    @rest.setter
    def rest(self, rest):
        self.adaptor.set_list("rest", sorted(int(c) for c in rest))

    @property
    def declaration(self):
        d = self.adaptor.get("declaration")
        if d:
            return card.Declaration.from_int(int(d))

    @declaration.setter
    def declaration(self, declaration):
        self.adaptor.set("declaration", int(declaration))

    @property
    def napoleon(self):
        return self.adaptor.get("napoleon", type=int)

    @napoleon.setter
    def napoleon(self, user_id):
        return self.adaptor.set("napoleon", user_id)

    @property
    def turn(self):
        return self.create_player(self.adaptor.get("turn", type=int))

    @turn.setter
    def turn(self, user_id):
        if isinstance(user_id, Player):
            user_id = user_id.user_id
        self.adaptor.set("turn", user_id)

    @property
    def adjutant(self):
        d = self.adaptor.get("adjutant")
        if d:
            return card.from_int(int(d))

    @adjutant.setter
    def adjutant(self, adjutant):
        return self.adaptor.set("adjutant", int(adjutant))

    @property
    def unused(self):
        return card.from_list(self.adaptor.get_list("unused", type=int))

    @property
    def unused_faces(self):
        return [c for c in self.unused if c.is_faced]

    @unused.setter
    def unused(self, cards):
        self.adaptor.set_list("unused", sorted(int(i) for i in cards))

    @property
    def board(self):
        ints = self.adaptor.get_list("board", type=int)
        return card.from_list(ints)

    @board.setter
    def board(self, card):
        self.adaptor.set_list("board", int(card), delete=False)

    @board.deleter
    def board(self):
        self.adaptor.delete("board")

    @property
    def player_cards(self):
        d = self.adaptor.get_dict("player_cards", type=int)
        if d:
            return {k: card.from_int(v) for k, v in d.items()}
        else:
            return {}

    @player_cards.setter
    def player_cards(self, value):
        k, v = value
        self.adaptor.set_dict("player_cards", k, int(v))

    @player_cards.deleter
    def player_cards(self):
        self.adaptor.delete("player_cards")

    @property
    def player_faces(self):
        return {p.user_id: p.face for p in self.players}

    @property
    def number_of_player_hand(self):
        return {p.user_id: p.number_of_hand for p in self.players}
