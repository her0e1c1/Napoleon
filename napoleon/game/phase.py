from napoleon import card


def get_action(phase, action=None):
    action_list = [StartAction, DeclareAction, PassAction, AdjutantAction, DiscardAction]
    actions = [cls for cls in action_list if cls.phase == phase]

    if len(actions) == 1:
        return actions[0]

    if action is None:
        return None

    for a in actions:
        name = "%sAction" % action.title()
        if a.__name__ == name:
            return a


class Action(object):

    def act(self, player, **kw):
        raise NotImplemented

    def validate(self, **kw):
        pass

    def next(self, player):
        player.state.next()


class StartAction(Action):
    phase = ""

    def act(self, player):
        player.state.start()

    def validate(self, **kw):
        pass

    def next(self, **kw):
        pass


class DeclareAction(Action):
    phase = "declare"

    def __init__(self, declaration):
        self.declaration = declaration

    def act(self, player):
        declaration = card.from_int(int(self.declaration))
        player.declare(declaration)

    def validate(self, **kw):
        pass

    def next(self, **kw):
        pass


class PassAction(Action):
    phase = "declare"

    def act(self, player):
        player.pass_()


class AdjutantAction(Action):
    phase = "adjutant"

    def __init__(self, adjutant):
        self.adjutant = adjutant

    def act(self, player):
        player.decide(card.from_int(int(self.adjutant)))
        player.state.set_role(card.from_int(int(self.adjutant)))

    def validate(self, **kw):
        pass

    def next(self, **kw):
        pass


class DiscardAction(Action):
    phase = "discard"

    def __init__(self, unused, selected):
        self.unused = unused
        self.selected = selected

    def act(self, player):
        player.discard(card.from_list(self.unused))
        player.select(card.from_int(int(self.selected)))
