import redis
import card


class InvalidSession(Exception):
    pass


def get_connection(host="localhost", port=6379, db=0):
    return redis.Redis(host, port=port, db=db)


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
        "napoleon": "{room_id}_napoleon",  # value
        "player_ids": "{room_id}_player_ids",  # sorted set
        "pass_ids": "{room_id}_pass_ids",  # set
        "declaration": "{room_id}_declaration",  # int (winning_number, trump suit)
        "turn": "{room_id}_turn",  # value
        "board": "{room_id}_board",  # list

        # private
        "rest": "{room_id}_rest",  # list
        "hand": "{room_id}_{user_id}_hand",  # list
        "map": "{room_id}_map",  # hash
    }
    return fmt[key].format(**locals())


def decode(s, type=None):
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
        # must create user_id by django before
        # or request by a malice session
        # raise InvalidSession("Session is invalid")

        self.conn = get_connection()
        self.room_id = room_id
        self.session_id = session_id

        if not user_id and session_id:
            user_id = get_user_id(self.room_id, session_id)

        if user_id:
            self.user_id = int(user_id)
        else:
            self.user_id = None

    def _set_list(self, key, iterable):
        key = self.key(key)
        self.conn.delete(key)
        for i in iterable:
            self.conn.lpush(key, i)

    def decode(self, s, type=None):
        return decode(s, type)

    @property
    def pass_ids(self):
        return self.decode(self.conn.lrange(self.key("pass_ids"), 0, -1), type=int)

    def set_pass_ids(self):
        return self.conn.lpush(self.key("pass_ids"), self.user_id)

    @property
    def is_joined(self):
        try:
            get_user_id(self.room_id, self.session_id)
        except InvalidSession:
            return False
        else:
            return True

    @property
    def is_first_round(self):
        # TODO: to count the rest of cards is better
        return len(self.rest) > 0

    @property
    def is_finished(self):
        pass

    @property
    def is_declared(self):
        # TODO: more simple type
        ids = set([self.napoleon] + self.pass_ids)
        return ids == set(self.player_ids)

    @property
    def is_started(self):
        return bool(self.rest)

    @property
    def declaration(self):
        d = self.conn.get(self.key("declaration"))
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
                raise InvalidSession("No")

    @property
    def players(self):
        return self.decode(self.conn.zrange(self.key("player_ids"), 0, -1), type=int)

    player_ids = players

    @property
    def turn(self):
        n = self.conn.get(self.key("turn"))
        if n:
            return decode(n, type=int)

    @turn.setter
    def turn(self, value):
        self.conn.set(self.key("turn"), value)

    @property
    def napoleon(self):
        n = self.conn.get(self.key("napoleon"))
        if n:
            return self.decode(n, type=int)

    @napoleon.setter
    def napoleon(self, value):
        return self.conn.set(self.key("napoleon"), value)

    @property
    def rest(self):
        if self.user_id == self.napoleon:
            ints = self.decode(self.conn.lrange(self.key("rest"), 0, -1), type=int)
            return card.Card.from_list(ints)
        else:
            return []

    @rest.setter
    def rest(self, rest):
        l = sorted(int(i) for i in rest)
        self._set_list("rest", l)

    def key(self, key):
        return get_key(key, room_id=self.room_id, user_id=self.user_id)

    @property
    def hand(self):
        if not self.session_id:
            return []
        ints = self.decode(self.conn.lrange(self.key("hand"), 0, -1), type=int)
        return card.Card.from_list(ints)

    @hand.setter
    def hand(self, hand):
        l = sorted(int(i) for i in hand)
        self._set_list("hand", l)

    def join(self):
        self.conn.zadd(self.key("player_ids"), *(self.user_id, 0))
        # self.conn.hset(self.key("map"), self.session_id, uid)

    def quit(self):
        self.conn.zrem(self.key("player_ids"), self.user_id)
        del_user_id(self.room_id, self.session_id, self.user_id)
