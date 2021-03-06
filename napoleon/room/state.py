import uuid
from napoleon.game.adaptor import RedisAdaptor


class User(object):

    def __init__(self, user_id, session_id, adaptor):
        """
        Make sure user id is valid.
        """
        self.adaptor = RedisAdaptor.create(adaptor, user_id)
        self.user_id = user_id
        self.session_id = session_id

    def join(self, user=None):
        self.adaptor.set_list("player_ids", self.user_id, delete=False)
        self.adaptor.set_dict("map", self.user_id, self.session_id)
        self.adaptor.set_dict("isAI", self.user_id, False)

        # TODO: define a user dict and reduce a code
        self.adaptor.set_dict("user", "username", user and user.get_username() or "ANONYMOUS USER")
        self.adaptor.set_dict("user", "user_id", self.user_id)

    def quit(self):
        self.adaptor.rem_list("player_ids", self.user_id)
        self.adaptor.rem_dict("map", self.user_id)
        self.adaptor.delete("user")

    def reset(self):
        self.adaptor.rem_dict("map", self.user_id)
        self.adaptor.set_dict("map", self.user_id, self.session_id)


class AI(object):

    def __init__(self, adaptor):
        """
        Make sure user id is valid.
        """
        self.user_id = str(uuid.uuid4())
        self.adaptor = RedisAdaptor.create(adaptor, self.user_id)

    def add(self, name):
        self.adaptor.set_list("player_ids", self.user_id, delete=False)
        self.adaptor.set_dict("AI", "user_id", self.user_id)
        self.adaptor.set_dict("AI", "username", name)
        self.adaptor.set_dict("isAI", self.user_id, True)

    def remove(self, user_id):
        self.adaptor.rem_dict("AI", user_id)
        self.adaptor.rem_list("player_ids", user_id)
