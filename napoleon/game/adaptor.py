import logging
from django.conf import settings


logger = logging.getLogger(__name__)


def get_key(key, room_id, user_id=None):
    fmt = {
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
        "player_cards": "{room_id}_player_cards",  # hash (int user_id: int card.value)
        "waiting_next_turn": "{room_id}_waiting_next_turn",  # bool
        "role": "{room_id}_{user_id}_role",  # value (0: napo, 1:rengo)
        "rest": "{room_id}_rest",  # list
        "hand": "{room_id}_{user_id}_hand",  # list
        "map": "{room_id}_map",  # hash

        # user
        "user": "user_{user_id}",  # hash
        "isAI": "{room_id}_isAI",  # value (bool)

        # ai
        "AI": "{room_id}_{user_id}_AI",  # hash (int user_id: str name)

        # chat
        "chat_user_ids": "{room_id}_chat_user_ids",  # list
        "chat_messages": "{room_id}_chat_messages",  # list

    }
    if key in ["role", "hand", "user"] and user_id is None:
        raise ValueError("You must take user_id as an argument when key is role or hand.")

    return fmt[key].format(**locals())


def decode(s, type=None):
    if s is None:
        return None

    if type is bool:
        type = lambda x: True if x == 'True' else False

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

    def __init__(self, room_id, user_id=None, conn=None, timer=None):
        self.conn = conn or settings.REDIS_CONNECTION
        self.room_id = room_id
        self.user_id = user_id
        self.timer = timer

    def key(self, k):
        return get_key(k, room_id=self.room_id, user_id=self.user_id)

    def get_list(self, key, type=None):
        return decode(self.conn.lrange(self.key(key), 0, -1), type=type)

    def set_list(self, key, iterable, delete=True, unique=True):
        bak = key
        key = self.key(key)
        if delete:
            self.conn.delete(key)
        if not isinstance(iterable, (list, tuple, set)):
            # use a list as a unique container
            # this code is not always perfect
            if unique and str(iterable) in self.get_list(bak):
                return
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

    def rem_dict(self, key, k):
        self.conn.hdel(self.key(key), k)

    def delete(self, key):
        self.conn.delete(self.key(key))

    def expire(self, key, sec):
        if not isinstance(key, (list, set)):
            key = [key]
        for k in key:
            self.conn.expire(self.key(k), sec)

    def flush(self):
        prefix = ("%s_" % self.room_id).encode("utf-8")
        for k in self.conn.keys("*"):
            if k.startswith(prefix):
                self.conn.delete(k)
