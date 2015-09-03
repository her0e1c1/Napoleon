import enum
import os
import logging
import redis
from napoleon import card
logger = logging.getLogger(__name__)


class InvalidSession(Exception):
    pass


class Role(enum.Enum):
    napoleon_forces = 1
    allied_forces = 2


def get_connection(host="localhost", port=6379, db=0):
    uri = os.environ.get("REDISTOGO_URL")
    if not uri:
        return redis.Redis(host, port=port, db=db)
    else:
        return redis.from_url(uri)


def get_user_id(room_id, session_id):
    conn = get_connection()
    key = get_key("map", room_id)
    user_dict = conn.hgetall(key)
    inv = {decode(v): k for k, v in user_dict.items()}
    user_id = inv.get(session_id)
    if not user_id:
        raise InvalidSession("Session is invalid")
    return int(user_id)


def get_key(key, room_id, user_id=None):
    fmt = {
        # public
        "phase": "{room_id}_phase",  # value
        "napoleon": "{room_id}_napoleon",  # value
        "player_ids": "{room_id}_player_ids",  # sorted set
        "pass_ids": "{room_id}_pass_ids",  # set
        "declaration": "{room_id}_declaration",  # int (winning_number, trump suit)
        "turn": "{room_id}_turn",  # value
        "board": "{room_id}_board",  # list
        "adjutant": "{room_id}_adjutant",  # hash
        "unused": "{room_id}_unused",  # list
        "face": "{room_id}_{user_id}_face",  # value
        "player_cards": "{room_id}_player_cards",  # hash (int: int)
        "waiting_next_turn": "{room_id}_waiting_next_turn",  # bool

        # private
        "role": "{room_id}_{user_id}_role",  # value (0: napo, 1:rengo)
        "rest": "{room_id}_rest",  # list
        "hand": "{room_id}_{user_id}_hand",  # list
        "map": "{room_id}_map",  # hash
    }
    if key in ["role", "hand"] and user_id is None:
        raise ValueError("You must take user_id as an argument when key is role or hand.")

    return fmt[key].format(**locals())


def decode(s, type=None):
    if s is None:
        return None

    if isinstance(s, (dict,)):
        if type:
            return {k.decode("utf-8"): type(v.decode("utf-8")) for k, v in s.items()}
        else:
            return {k.decode("utf-8"): v.decode("utf-8") for k, v in s.items()}

    if isinstance(s, (list, set)):
        if type:
            return [type(i.decode("utf-8")) for i in s]
        else:
            return [i.decode("utf-8") for i in s]
    if type:
        return type(s.decode("utf-8"))
    else:
        return s.decode("utf-8")


class RedisAdaptor(object):

    def __init__(self, room_id, user_id=None):
        self.conn = get_connection()
        self.room_id = room_id
        self.user_id = user_id

    def key(self, k):
        return get_key(k, room_id=self.room_id, user_id=self.user_id)

    def get_list(self, key, type=None):
        return decode(self.conn.lrange(self.key(key), 0, -1), type=type)

    def set_list(self, key, iterable, delete=True):
        key = self.key(key)
        if delete:
            self.conn.delete(key)
        if not isinstance(iterable, (list, tuple, set)):
            iterable = [iterable]
        for i in iterable:
            self.conn.lpush(key, i)

    def rem_list(self, key, value):
        self.conn.lrem(self.key(key), value, 0)

    def get(self, key, type=None):
        return decode(self.conn.get(self.key(key)), type=type)

    def set(self, key, value):
        self.conn.set(self.key(key), value)

    def get_dict(self, key, type=None):
        return decode(self.conn.hgetall(self.key(key)), type=type)

    def set_dict(self, key, k, v):
        self.conn.hset(self.key(key), k, v)

    def delete(self, key):
        self.conn.delete(self.key(key))

    def flush(self):
        prefix = ("%s_" % self.room_id).encode("utf-8")
        for k in self.conn.keys("*"):
            if k.startswith(prefix):
                self.conn.delete(k)


class PrivateGameState(object):

    def __init__(self, room_id, user_id=None, session_id=None, **kw):

        self.conn = get_connection()
        self.room_id = room_id
        self.session_id = session_id

        if not user_id and session_id:
            user_id = get_user_id(self.room_id, session_id)

        if user_id:
            self.user_id = int(user_id)
        else:
            self.user_id = None

    def key(self, key):
        return get_key(key, room_id=self.room_id, user_id=self.user_id)

    def decode(self, s, type=None):
        return decode(s, type)

    @property
    def is_valid_session(self):
        key = get_key("map", self.room_id)
        user_dict = decode(self.conn.hgetall(key))
        sid = user_dict.get(str(self.user_id))
        if sid and sid == self.session_id:
            return True
        else:
            return False

    @property
    def is_finished(self):
        if self.phase != "rounds":
            return False
        n = 0
        for pid in self.player_ids:
            key = get_key("hand", self.room_id, pid)
            ints = decode(self.conn.lrange(key, 0, -1), type=int)
            n += len(ints)
        return n == 0

    @property
    def did_napoleon_win(self):
        if not self.declaration:
            return False
        n, _ = self._each_side_face_cards
        if n == card.NUMBER_OF_FACE_CARDS:
            return False
        return n >= self.declaration.pip

    @property
    def did_napoleon_lose(self):
        if not self.declaration:
            return False
        _, n = self._each_side_face_cards
        if n == 0:
            return True
        return n > card.NUMBER_OF_FACE_CARDS - self.declaration.pip

    @property
    def _each_side_face_cards(self):
        napo = 0
        allies = 0
        for pid in self.player_ids:
            key = get_key("role", self.room_id, pid)
            role = decode(self.conn.get(key), type=int)
            key = get_key("face", self.room_id, pid)
            num = decode(self.conn.get(key), type=int)
            if role == 1:  # napo
                napo += num
            else:
                allies += num
        return napo, allies

    @property
    def player_faces(self):
        f = {}
        for pid in self.player_ids:
            key = get_key("face", self.room_id, pid)
            f[pid] = decode(self.conn.get(key), type=int)
        return f


class User(object):

    def __init__(self, user_id, session_id, state):
        """
        Make sure user id is valid.
        """
        # self.adaptor = RedisAdaptor(room_id=state.room_id, user_id=user_id)
        self.user_id = user_id
        self.session_id = session_id
        self.state = state

    def join(self):
        # check duplicated join
        key = get_key("player_ids", self.state.room_id)
        self.state.conn.lpush(key, self.user_id)
        key = get_key("map", self.state.room_id)
        self.state.conn.hset(key, self.user_id, self.session_id)

    def quit(self, force=False):
        # if force or (get_user_id(self.state.room_id, self.session_id)) == self.user_id:
        self.state._rem_list("player_ids", self.user_id)
        key = get_key("map", self.state.room_id)
        self.state.conn.hdel(key, self.user_id)

    def reset(self):
        self.quit(force=True)
        self.join()


class Player(object):

    # set/get any info
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

    def select(self, c):
        """
        A player selects a card
        """
        if c == card.CLUB10 and self.can_betray:
            if self.role == Role.napoleon_forces:
                self.role = Role.allied_forces
            else:
                self.role = Role.napoleon_forces

        self.adaptor.rem_list("hand", int(c))
        self.state.board = c
        self.state.player_cards = (self.user_id, c)

    @property
    def can_betray(self):
        return False
        # s = card.from_int(selected) == card.CLUB10
        board = self.state.board
        len(self.state.napoleon_forces) > 1
        return not board and s and not self.is_napoleon

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
        # if self.user_id != self.napoleon:
        hand = self.hand + self.state.rest
        for u in unused:
            try:
                hand.remove(u)
            except ValueError:  # malice request
                # logger
                return

        self.hand = hand
        self.state.unused = unused

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
        d = (self.adaptor.get("role", type=int))
        if d:
            return Role(d)

    @role.setter
    def role(self, role):
        return self.adaptor.set("role", role.value)

    @property
    def possible_cards(self):
        d = self.state.declaration
        # wait for the next turn before playing a lead card
        if len(self.state.board) == len(self.state.players):
            return self.hand
        elif d:
            return card.possible_cards(self.state.board, self.hand, d.suit)
        else:
            return []


# Secure
class Myself(Player):

    def __init__(self, session_id, state):
        self.session_id = session_id
        user_id = get_user_id(state.room_id, self.session_id)
        super().__init__(user_id, state)

    def is_valid_session(self):
        pass

    @property
    def is_joined(self):
        try:
            get_user_id(self.room_id, self.session_id)
        except InvalidSession:
            return False
        else:
            return True


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

    def next_phase(self):
        next = self._(self.current)
        if next != "still":
            self.current = next

    def _(self, phase):
        if not phase:
            return "declare"
        elif phase == "declare":
            if self.is_napoleon_determined:
                return "adjutant"
            elif self.are_all_players_passed:
                return "restart"
                # return None
        elif phase == "adjutant":
            return "discard"
        elif phase == "discard":
            return "first_round"
        elif phase == "first_round":
            if self.waiting_next_turn:
                return "rounds"
        elif phase == "rounds":
            # if self.is_finished:
            pass
        return "still"

    def next(self):
        phase = self.current
        if phase in ["discard", "first_round", "rounds"]:
            self.next_turn()
        self.next_phase()

    # next turn
    def next_turn(self):
        players = self.state.players
        index = players.index(self.state.turn)
        board = self.state.board

        if 0 <= len(board) < len(players):
            # board is not full
            if 0 <= index < len(players) - 1:
                self.state.turn = players[index + 1]
            else:
                self.state.turn = players[0]
        else:
            winner_id = card.winner(
                board=board,
                player_cards=self.state.player_cards,
                trump_suit=self.state.declaration.suit,
                is_first_round=self.state.phase == "first_round",
            )
            winner = Player(winner_id, self.state)
            cards = list(board)
            if self.state.phase == "first_round":
                cards += self.state.unused
            faces = [c for c in cards if c.is_faced]
            winner.face = len(faces) + len(winner.face)
            self.state.turn = winner
            self.waiting_next_turn = True

    def next_round(self):
        del self.state.board
        del self.state.player_cards
        self.waiting_next_turn = False


class GameState(object):

    def __init__(self, room_id):
        self.adaptor = RedisAdaptor(room_id=room_id)
        self.room_id = room_id
        self._phase = Phase(self)

    @property
    def phase(self):
        return self._phase.current

    def next(self):
        return self._phase.next()

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
    def rest(self):
        ints = self.adaptor.get_list("rest", type=int)
        return card.from_list(ints)

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
        return Player(user_id, state=self)

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
