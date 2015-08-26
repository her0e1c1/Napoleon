import os
import logging
from urllib.parse import urlparse
import redis
from napoleon import card
logger = logging.getLogger(__name__)


class InvalidSession(Exception):
    pass


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


def set_user_id(room_id, session_id, user_id):
    conn = get_connection()
    key = get_key("map", room_id)
    conn.hset(key, user_id, session_id)


def del_user_id(room_id, session_id, user_id):
    if get_user_id(room_id, session_id) == user_id:
        conn = get_connection()
        key = get_key("map", room_id)
        conn.hdel(key, user_id)


def reset_session_id_if_changed(room_id, session_id, user_id):
    conn = get_connection()
    key = get_key("map", room_id)
    sid = conn.hget(key, user_id)
    if sid and decode(sid) != session_id:
        conn.hdel(key, user_id)


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
    def is_joined(self):
        try:
            get_user_id(self.room_id, self.session_id)
        except InvalidSession:
            return False
        else:
            return True

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
    def is_appropriate_player_number(self):
        return len(self.player_ids) in card.RANGE_OF_PLAYERS

    @property
    def is_napoleon_determined(self):
        return bool(self.napoleon) and len(self.pass_ids) >= len(self.player_ids) - 1

    @property
    def are_all_players_passed(self):
        return len(self.pass_ids) == len(self.player_ids)

    @property
    def did_napoleon_win(self):
        if not self.declaration:
            return False
        n, _ = self._each_side_face_cards
        return n >= self.declaration.pip

    @property
    def did_napoleon_lose(self):
        if not self.declaration:
            return False
        _, n = self._each_side_face_cards
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

    def _get_list(self, key, type=None):
        return decode(self.conn.lrange(self.key(key), 0, -1), type=type)

    def _set_list(self, key, iterable):
        key = self.key(key)
        self.conn.delete(key)
        for i in iterable:
            self.conn.lpush(key, i)

    def _rem_list(self, key, value):
        self.conn.lrem(self.key(key), value, 0)

    def _get(self, key, type=None):
        return decode(self.conn.get(self.key(key)), type=type)

    def _set(self, key, value):
        self.conn.set(self.key(key), value)

    @property
    def waiting_next_turn(self):
        return bool(self._get("waiting_next_turn", type=int))

    @waiting_next_turn.setter
    def waiting_next_turn(self, value):
        value = 1 if value else 0
        return self._set("waiting_next_turn", value)

    @property
    def napoleon(self):
        return self._get("napoleon", type=int)

    @napoleon.setter
    def napoleon(self, value):
        return self._set("napoleon", value)

    @property
    def phase(self):
        return self._get("phase")

    @phase.setter
    def phase(self, value):
        self._set("phase", value)

    @property
    def face(self):
        return self._get("face")

    @face.setter
    def face(self, value):
        self._set("face", value)

    @property
    def turn(self):
        return self._get("turn", type=int)

    @turn.setter
    def turn(self, value):
        self._set("turn", value)

    @property
    def role(self):
        return self._get("role")

    @property
    def adjutant(self):
        d = self._get("adjutant")
        if d:
            return card.Card.from_int(int(d))

    @adjutant.setter
    def adjutant(self, value):
        if self.user_id == self.napoleon:
            return self._set("adjutant", value)

    @property
    def pass_ids(self):
        return self._get_list("pass_ids", type=int)

    def set_pass_ids(self):
        return self.conn.lpush(self.key("pass_ids"), self.user_id)

    @property
    def declaration(self):
        d = self._get("declaration")
        if d:
            return card.Declaration.from_int(int(d))

    @declaration.setter
    def declaration(self, value):
        d = self.declaration
        if not d or int(d) < int(value):
            self.conn.set(self.key("declaration"), value)
            if self.session_id:
                self.napoleon = self.turn = self.user_id
            else:
                raise InvalidSession

    @property
    def player_cards(self):
        d = decode(self.conn.hgetall(self.key("player_cards")), type=int)
        if d:
            return {k: card.from_int(v) for k, v in d.items()}
        else:
            return {}

    @player_cards.setter
    def player_cards(self, value):
        self.conn.hset(self.key("player_cards"), self.user_id, value)

    @player_cards.deleter
    def player_cards(self):
        self.conn.delete(self.key("player_cards"))

    @property
    def player_ids(self):
        return self._get_list("player_ids", type=int)

    @property
    def board(self):
        ints = self._get_list("board", type=int)
        return card.from_list(ints)

    @board.setter
    def board(self, value):
        key = self.key("board")
        self.conn.lpush(key, value)

    @board.deleter
    def board(self):
        key = self.key("board")
        self.conn.delete(key)

    def next(self):
        pids = self.player_ids
        index = pids.index(self.user_id)
        board = self.board

        if 0 <= len(board) < len(pids):
            # board is not full
            if 0 <= index < len(pids) - 1:
                self.turn = pids[index + 1]
            else:
                self.turn = pids[0]
        else:
            winner = card.winner(board, self.player_cards, self.declaration.suit)
            cards = self.board
            if self.phase == "first_round":
                cards += self.unused

            faces = [c for c in cards if c.is_faced]
            key = get_key("face", self.room_id, winner)
            new = len(faces) + decode(self.conn.get(key), type=int)
            self.conn.set(key, new)
            self.turn = winner
            self.waiting_next_turn = True

    def next_round(self):
        del self.board
        del self.player_cards
        self.waiting_next_turn = False

    @property
    def rest(self):
        if self.user_id == self.napoleon and self.phase == "discard":
            ints = self._get_list("rest", type=int)
            return card.from_list(ints)
        else:
            return []

    @rest.setter
    def rest(self, rest):
        l = sorted(int(i) for i in rest)
        self._set_list("rest", l)

    def select(self, selected):
        if self.turn != self.user_id:
            logger.debug("{} is not in turn".format(self.user_id))
            return

        self.conn.lrem(self.key("hand"), selected, 0)
        self.board = selected
        self.player_cards = selected

    @property
    def unused(self):
        if self.phase == "first_round":
            ints = self._get_list("unused", type=int)
            return [c for c in card.from_list(ints) if c.is_faced]
        else:
            return []

    @unused.setter
    def unused(self, value):
        l = sorted(int(i) for i in value)
        self._set_list("unused", l)

    def discard(self, unused):
        if self.user_id != self.napoleon:
            logger.debug("{} is not in turn".format(self.user_id))
            return

        hand = self.hand + self.rest
        for u in card.from_list(unused):
            try:
                hand.remove(u)
            except ValueError:  # malice request
                return

        self.hand = hand
        self.unused = unused

    @property
    def hand(self):
        if not self.session_id:
            return []
        ints = self._get_list("hand", type=int)
        return card.from_list(ints)

    @hand.setter
    def hand(self, hand):
        l = sorted(int(i) for i in hand)
        self._set_list("hand", l)

    def join(self):
        self.conn.lpush(self.key("player_ids"), self.user_id)

    def quit(self):
        self._rem_list("player_ids", self.user_id)
        del_user_id(self.room_id, self.session_id, self.user_id)

    def set_role(self, adjutant):
        napoleon = self.napoleon
        conn = self.conn
        room_id = self.room_id
        for pid in self.player_ids:
            if pid == napoleon:
                role = 1
            else:
                key = get_key("hand", room_id, pid)
                ints = decode(conn.lrange(key, 0, -1), type=int)
                if adjutant in ints:
                    role = 1
                else:
                    role = 2
            key = get_key("role", room_id, pid)
            conn.set(key, role)

    @property
    def player_faces(self):
        f = {}
        for pid in self.player_ids:
            key = get_key("face", self.room_id, pid)
            f[pid] = decode(self.conn.get(key), type=int)
        return f

    @property
    def possible_cards(self):
        d = self.declaration
        if len(self.board) == len(self.player_ids):
            return self.hand
        elif d:
            return card.possible_cards(self.board, self.hand, d.suit)
        else:
            return []
