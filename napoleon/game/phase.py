from napoleon import card


def get_action(phase, action=None):
    action_list = [StartAction, DeclareAction, PassAction, AdjutantAction, DiscardAction,
                   SelectAction
    ]
    actions = [cls for cls in action_list if cls.phase == phase or phase in cls.phase]

    if len(actions) == 1:
        return actions[0]

    if action is None:
        return None

    for a in actions:
        name = "%sAction" % action.title()
        if a.__name__ == name:
            return a


class Action(object):

    def __init__(self, player):
        self.player = player

    def act(self, **kw):
        raise NotImplemented

    def validate(self, **kw):
        raise NotImplemented

    def next(self):
        self.player.state.next()


class StartAction(Action):
    phase = ""

    def act(self):
        self.player.state.start()


class DeclareAction(Action):
    phase = "declare"

    def act(self, declaration):
        self.player.declare(card.from_int(int(declaration)))


class PassAction(Action):
    phase = "declare"

    def act(self):
        self.player.pass_()


class AdjutantAction(Action):
    phase = "adjutant"

    def act(self, adjutant):
        self.player.decide(card.from_int(int(adjutant)))
        self.player.state.set_role(card.from_int(int(adjutant)))


class DiscardAction(Action):
    phase = "discard"

    def act(self, unused, selected):
        self.player.discard(card.from_list(unused))
        self.player.select(card.from_int(int(selected)))


class SelectAction(Action):
    phase = ["first_round", "rounds"]

    def act(self, selected):
        if self.player.state._phase.waiting_next_turn:
            self.player.state._phase.next_round()
        self.player.select(card.from_int(int(selected)))
