import uuid
import enum
import logging

from napoleon.game import card
from napoleon.game.adaptor import RedisAdaptor


logger = logging.getLogger(__name__)


class GameStateWithSession(object):

    def __init__(self, adaptor, user_id, session_id):
        self.state = GameState(adaptor)
        self.privilege = Privilege(Myself(user_id=user_id, session_id=session_id, state=self.state))

    def __getattr__(self, name):
        meth = getattr(self.privilege, name, None)
        value = getattr(self.state, name)
        if meth:
            return meth(value)
        else:
            return value


class Privilege(object):

    def __init__(self, player):
        self.player = player

    # for a game state instance
    def rest(self, value):
        return value if self.player.is_napoleon else []

    # for a player instance
    def role(self, value):
        return value if self.state.phases.current == "finished" or self.is_valid else None

    def possible_cards(self, value):
        return value if self.is_valid else None


class Myself(object):

    def __init__(self, state, session_id, user_id=None):
        if user_id is None:
            user_id = get_user_id(state.adaptor, session_id)
        self.player = Player(user_id, state)
        self.session_id = session_id
        self.privilege = Privilege(self.player)

    def __getattr__(self, name):
        meth = getattr(self.privilege, name, None)
        value = getattr(self.player, name)
        if meth:
            return meth(value)
        else:
            return value

    @property
    def is_valid(self):
        try:
            get_user_id(self.state.adaptor, self.session_id)
        except InvalidSession:
            return False
        else:
            return True


class InvalidSession(Exception):
    pass


def to_json(obj):
    if isinstance(obj, (int, str)):
        return obj
    elif isinstance(obj, list):
        return [to_json(o) for o in obj]
    elif isinstance(obj, dict):
        # js側でintが桁溢れする
        return {k: to_json(v) if k != "user_id" else str(v) for k, v in obj.items()
                if not str(k).startswith("_") and not callable(v)}
    elif hasattr(obj, "to_json"):
        return obj.to_json()
    elif isinstance(obj, enum.Enum):
        return obj.name
    else:
        return None


class Role(enum.Enum):
    napoleon_forces = 1
    allied_forces = 2


def get_user_id(adaptor, session_id):
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
        self.adaptor = RedisAdaptor(state.room_id, user_id, state.adaptor.conn)
        self.user_id = user_id
        self.session_id = session_id
        self.state = state

    def join(self, user=None):
        self.adaptor.set_list("player_ids", self.user_id, delete=False)
        self.adaptor.set_dict("map", self.user_id, self.session_id)
        self.adaptor.set_dict("isAI", self.user_id, False)

        # TODO: define a user dict and reduce a code
        self.adaptor.set_dict("user", "username", user.get_username())
        self.adaptor.set_dict("user", "user_id", user.id)

    def quit(self):
        self.adaptor.rem_list("player_ids", self.user_id)
        self.adaptor.rem_dict("map", self.user_id)
        self.adaptor.delete("user")

    def reset(self):
        self.adaptor.rem_dict("map", self.user_id)
        self.adaptor.set_dict("map", self.user_id, self.session_id)


class AI(object):

    def __init__(self, state):
        """
        Make sure user id is valid.
        """
        self. user_id = int(uuid.uuid4())
        self.adaptor = RedisAdaptor(state.room_id, self.user_id, state.adaptor.conn)

    def add(self, name):
        self.adaptor.set_list("player_ids", self.user_id, delete=False)
        self.adaptor.set_dict("AI", "user_id", self.user_id)
        self.adaptor.set_dict("AI", "username", name)
        self.adaptor.set_dict("isAI", self.user_id, True)

    def remove(self, user_id):
        self.adaptor.rem_dict("AI", user_id)
        self.adaptor.rem_list("player_ids", user_id)


class Player(object):

    def __init__(self, user_id, state):
        if user_id is None:
            raise ValueError("user_id must not be None")
        self.adaptor = RedisAdaptor(state.room_id, user_id, state.adaptor.conn)
        self.user_id = user_id
        self.state = state

    def to_json(self):
        # GameState has a players attribute.
        # so state must be ignored here so as not to be recurcively called
        return to_json({key: getattr(self, key) for key in dir(self) if key != "state"})

    def __repr__(self):
        return "Player {self.user_id}".format(self=self)

    def __eq__(self, other):
        return self.user_id == other.user_id

    @property
    def is_valid(self):
        # A player without a session is not valid
        return False

    @property
    def is_napoleon(self):
        return self.state.napoleon == self.user_id

    @property
    def is_joined(self):
        return self in self.state.players

    @property
    def is_passed(self):
        return self in self.state.passed_players

    @property
    def is_my_turn(self):
        if self.state.turn:
            return self == self.state.turn
        else:
            return False

    @property
    def is_winner(self):
        if self.state.phase.current != "finished":
            return None
        if self.state.phase.did_napoleon_forces_win is True:
            return True if self.is_napoleon_forces else False
        if self.state.phase.did_allied_forces_win is True:
            return True if self.is_allied_forces else False
        return None  # a game is being played

    @property
    def is_napoleon_forces(self):
        return self.role == Role.napoleon_forces

    @property
    def is_allied_forces(self):
        return self.role == Role.allied_forces

    @property
    def current_card(self):
        return self.state.player_cards.get(str(self.user_id))

    def select(self, card):
        """
        A player selects a card
        """
        if len(self.state.board) >= len(self.state.players):
            raise ValueError("A player can't select a card because the board is full.")

        if card not in self.possible_cards:
            raise ValueError("A player can't select a card he doesn't have.")

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
            except ValueError:
                raise ValueError("A player can't discard a card he doesn't have.")

        self.hand = hand
        self.state.unused = unused

    def add_rest_to_hand(self):
        """
        After napoleon decides an adjutant, he gets cards from the rest.
        """
        self.hand = self.hand + self.state.rest

    @property
    def number_of_hand(self):
        return len(self.hand)

    @property
    def hand(self):
        return card.from_list(self.adaptor.get_list("hand", type=int))

    @hand.setter
    def hand(self, hand):
        self.adaptor.set_list("hand", sorted(int(i) for i in hand))

    @property
    def face(self):
        return self.adaptor.get("face", type=int)

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


class Phase(object):

    def __init__(self, state):
        self.state = state
        self.adaptor = state.adaptor

    def to_json(self):
        return to_json({key: getattr(self, key) for key in dir(self) if key != "state"})

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

    @property
    def is_finished(self):
        if self.did_napoleon_forces_win or self.did_allied_forces_win:
            return True
        return sum([len(p.hand) for p in self.state.players]) == 0

    @property
    def did_napoleon_forces_win(self):
        n = self.state.number_of_face_cards_of_napoleon_forces
        if n == card.NUMBER_OF_FACE_CARDS:
            return False
        if self.state.declaration:
            return n >= self.state.declaration.pip
        else:
            return False

    @property
    def did_allied_forces_win(self):
        n = self.state.number_of_face_cards_of_napoleon_forces
        a = self.state.number_of_face_cards_of_allied_forces
        if self.state.declaration:
            if n == card.NUMBER_OF_CARDS:
                return True
            else:
                return a > card.NUMBER_OF_FACE_CARDS - self.state.declaration.pip
        else:
            return False


class GameState(object):

    def __init__(self, adaptor):
        self.adaptor = adaptor
        self.room_id = adaptor.room_id
        self.phase = Phase(self)

    def to_json(self):
        return to_json({key: getattr(self, key) for key in dir(self)})

    def create_player(self, user_id):
        if user_id is None:
            raise ValueError("user_id must not be None")

        # TODO: make user_id type of str
        d = self.adaptor.get_dict("isAI", type=bool)
        if d[str(user_id)]:
            return PlayerAI(user_id, self)

        return PlayerHuman(user_id, self)

    def flush(self):
        """
        Delete all data about this room.
        """
        self.adaptor.flush()

    def start(self, restart=False):
        """
        Distribute cards to each player and leave the rest of cards which napoleon can change
        """
        if restart:
            del self.passed_players

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
            l.append(self.create_player(user_id=pid))
        return l

    @property
    def player_AIs(self):
        return [p for p in self.players if p.is_AI]

    @property
    def passed_players(self):
        # TODO: self.playersを介す
        l = []
        for pid in self.adaptor.get_list("pass_ids", type=int):
            l.append(Player(user_id=pid, state=self))
        return l

    @passed_players.deleter
    def passed_players(self):
        self.adaptor.delete("pass_ids")

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
        user_id = self.adaptor.get("turn", type=int)
        if user_id:
            return self.create_player(user_id)

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
        return card.from_list(self.adaptor.get_list("board", type=int))

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
        user_id, card = value
        self.adaptor.set_dict("player_cards", user_id, int(card))

    @player_cards.deleter
    def player_cards(self):
        self.adaptor.delete("player_cards")

    @property
    def number_of_face_cards_of_napoleon_forces(self):
        return sum([p.face for p in self.players if p.is_napoleon_forces])

    @property
    def number_of_face_cards_of_allied_forces(self):
        return sum([p.face for p in self.players if p.is_allied_forces])


class PlayerHuman(Player):

    is_AI = False

    def __init__(self, user_id, state):
        super().__init__(user_id, state)
        self.user = self.adaptor.get_dict("user")


class PlayerAI(Player):

    is_AI = True

    def __init__(self, user_id, state):
        super().__init__(user_id, state)
        self.user = self.adaptor.get_dict("AI")
        name = self.user["username"]
        from napoleon import AI
        self._AI = getattr(AI, name)(self)
