import enum
from napoleon.game.state import GameState


def to_json(obj):
    if isinstance(obj, (int, str)):
        return obj
    elif isinstance(obj, list):
        return [to_json(o) for o in obj]
    elif isinstance(obj, dict):
        return {k: to_json(v) for k, v in obj.items()
                if not str(k).startswith("_") and not callable(v)}
    elif hasattr(obj, "to_json"):
        return obj.to_json()
    elif isinstance(obj, enum.Enum):
        return obj.name
    else:
        return None


class Session(object):

    def __init__(self, adaptor, session_id=None, user_id=None):
        # request.user.id is int. so here make it type of string
        if user_id:
            user_id = str(user_id)

        # if session is valid for user id, then True
        self.is_valid = False

        self.adaptor = adaptor

        if session_id:
            self.user_id = get_user_id(adaptor, session_id)
            if self.user_id:
                if user_id is None or user_id == self.user_id:
                    self.is_valid = True
            else:
                self.user_id = user_id
        else:
            self.user_id = user_id

    @property
    def myself(self):
        if self.user_id:
            return PlayerWithSession(GameState(self.adaptor), self)

    @property
    def state(self):
        return GameStateWithSession(self)

    def create_player(self, user_id):
        session = Session(self.adaptor, user_id=user_id)
        state = GameState(self.adaptor)
        return PlayerWithSession(state, session)


def get_user_id(adaptor, session_id):
    user_dict = adaptor.get_dict("map")
    inv = {v: k for k, v in user_dict.items()}
    user_id = inv.get(session_id)
    if user_id:
        return user_id


class PlayerPrivilege(object):

    def __init__(self, session):
        self.session = session

    def role(self, value):
        p = self.session.myself
        if p or p.state.phase.current == "finished":
            return value
        return None

    def possible_cards(self, value):
        return value if self.session.is_valid else []

    def hand(self, value):
        return value if self.session.is_valid else []


class StatePrivilege(object):

    def __init__(self, session):
        self.session = session

    def rest(self, value):
        p = self.session.myself
        return value if self.session.is_valid and p.is_napoleon else []

    def unused(self, value):
        p = self.session.myself
        return value if self.session.is_valid and p.is_napoleon else []

    def players(self, value):
        p = self.session.myself
        return [p if p and p.user_id == v.user_id else
                self.session.create_player(v.user_id) for v in value]


class PlayerWithSession(object):

    def __init__(self, state, session):
        self.state = GameStateWithSession(session)
        self.player = state.create_player(session.user_id)
        self.privilege = PlayerPrivilege(session)
        self.is_valid = session.is_valid

    def to_json(self):
        # GameState has a players attribute.
        # so state must be ignored here so as not to be recurcively called
        keys = dir(self.player) + ["is_valid"]
        return to_json({key: getattr(self, key) for key in keys if key != "state"})

    def __getattr__(self, name):
        meth = getattr(self.privilege, name, None)
        value = getattr(self.player, name)
        if meth:
            return meth(value)
        else:
            return value


class GameStateWithSession(object):

    def __init__(self, session):
        self.state = GameState(session.adaptor)
        self.phase = PhaseWithSession(self.state, session)
        self.privilege = StatePrivilege(session)

    def __getattr__(self, name):
        meth = getattr(self.privilege, name, None)
        value = getattr(self.state, name)
        if meth:
            return meth(value)
        else:
            return value

    def to_json(self):
        return to_json({key: getattr(self, key) for key in dir(self.state)})


class PhaseWithSession(object):

    def __init__(self, state, session):
        self.phase = state.phase

    def to_json(self):
        return to_json({key: getattr(self, key) for key in dir(self.phase) if key != "state"})

    def __getattr__(self, name):
        value = getattr(self.phase, name)
        return value
