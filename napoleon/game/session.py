import functools


class InvalidSession(Exception):
    pass


class Session(object):

    def __init__(self, adaptor, session_id):
        self.user_id = get_user_id(adaptor, session_id)

        from napoleon.game import state
        self.myself = state.Player(
            self.user_id,
            state=state.GameState(adaptor, self)
        )


def get_user_id(adaptor, session_id):
    user_dict = adaptor.get_dict("map")
    inv = {v: k for k, v in user_dict.items()}
    user_id = inv.get(session_id)
    if user_id:
        return int(user_id)


def player_property(**kwargs):
    return functools.partial(PlayerProperty, **kwargs)


class PlayerProperty(object):

    def __init__(self, fget=None, finished=False, default=None):
        self.fget = fget
        self.finished = finished
        self.default = default

    def _check(self, obj):
        if obj._session is None:
            return True

        if self.finished:
            return obj.state.phase.current == "finished"

        return obj.is_valid

    def __get__(self, obj, type=None):
        if self.fget is None:
            raise AttributeError
        if self._check(obj):
            return self.fget(obj)
        else:
            return self.default

    def __set__(self, obj, value):
        if self.fset is None:
            raise AttributeError
        return self.fset(obj, value)

    def __delete__(self, obj):
        if self.fdel is None:
            raise AttributeError
        return self.fdel(obj)

    def setter(self, fset):
        self.fset = fset
        return self

    def deleter(self, fdel):
        self.fdel = fdel
        return self


def state_property(**kwargs):
    return functools.partial(StateProperty, **kwargs)


# TODO: inherit property
class StateProperty(PlayerProperty):

    def __init__(self, fget=None, is_napoleon=False, default=None):
        self.fget = fget
        self.is_napoleon = is_napoleon
        self.default = default

    def _check(self, obj):
        if obj._session is None:
            return True

        if self.is_napoleon:
            return obj._session.myself.is_napoleon
