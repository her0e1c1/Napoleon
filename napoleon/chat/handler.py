from django.conf import settings
from tornado.websocket import WebSocketHandler
from napoleon.game.handler import WSHandlerMixin
from napoleon.game.adaptor import RedisAdaptor
from napoleon.game import state
from napoleon.game import session


class Chat(object):

    def __init__(self, adaptor):
        self.adaptor = adaptor

    def set(self, msg, user_id):
        self.adaptor.set_list("chat_user_ids", user_id, delete=False, unique=False)
        self.adaptor.set_list("chat_messages", msg, delete=False, unique=False)
        self.adaptor.expire(["chat_user_ids", "chat_messages"], settings.REDIS_CHAT_EXPRITE_TIME)

    def get(self):
        ids = self.adaptor.get_list("chat_user_ids")
        msg = self.adaptor.get_list("chat_messages")
        users = {}
        for i, m in zip(ids, msg):
            if i not in users:
                a = RedisAdaptor(self.adaptor.room_id, i, self.adaptor.conn)
                users[i] = a.get_dict("user")
            d = {"msg": m}
            d.update(users[i])
            yield d


class ChatHandler(WSHandlerMixin, WebSocketHandler):

    def on_message(self, message):
        try:
            json = self.to_json(message)
        except ValueError:
            return

        adaptor = RedisAdaptor(self.room_id)
        sid = json.pop("session_id")
        try:
            uid = session.get_user_id(adaptor, session_id=sid)
        except state.InvalidSession:
            return self.close()

        chat = Chat(adaptor)
        msg = json.get("msg")
        if msg:
            chat.set(msg, uid)

        messages = list(chat.get())[:settings.REDIS_CHAT_LENGTH]
        self.write_on_same_room({"messages": messages})
