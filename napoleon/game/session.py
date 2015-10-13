import enum
from napoleon.game.state import GameState


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


class Session(object):

    def __init__(self, adaptor, session_id=None, user_id=None):

        # if session is valid for user id, then True
        self.is_valid = False

        self.adaptor = adaptor

        if session_id:
            self.user_id = get_user_id(adaptor, session_id)
            if self.user_id:
                if user_id == self.user_id:
                    self.is_valid = True
            else:
                self.user_id = user_id
        else:
            self.user_id = user_id

        if self.user_id is None:
            raise ValueError("No user id")

    @property
    def myself(self):
        return PlayerWithSession(GameState(self.adaptor), self)

    def create_player(self, user_id):
        session = Session(self.adaptor, user_id=user_id)
        return PlayerWithSession(self.myself.state, session)


def get_user_id(adaptor, session_id):
    user_dict = adaptor.get_dict("map")
    inv = {v: k for k, v in user_dict.items()}
    user_id = inv.get(session_id)
    if user_id:
        return int(user_id)


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
        return [p if p.user_id == v.user_id else
                self.session.create_player(v.user_id) for v in value]


class PlayerWithSession(object):

    def __init__(self, state, session):
        self.state = GameStateWithSession(session)
        self.privilege = PlayerPrivilege(session)
        self.is_valid = session.is_valid
        self.player = state.create_player(session.user_id)

    def to_json(self):
        # GameState has a players attribute.
        # so state must be ignored here so as not to be recurcively called
        keys = dir(self.player) + ["is_valid"]
        return to_json({key: getattr(self, key) for key in keys if key != "state"})

    @classmethod
    def from_player(cls, player, session):
        return PlayerWithSession(player.state, session)

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
        self.privilege = StatePrivilege(session)
        self.phase = PhaseWithSession(self.state, session)

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
