

class BaseAI(object):

    def __init__(self, player):
        self.player = player
        self.state = self.player.state
        self.phase = self.player.state.phase

    def get_action(self):
        """
        :return: {"action": ACTION_NAME, "arg1": ARG1, ...}
                 returns the same json value like a client browser sends.
        """
        # 各メソッドはオーバーライドさせるが、
        # 子供の戻り値は信用しない。値のチェックが必要
        if self.phase.current == "declare":
            if not self.player.is_passed:
                declaration = self.declare()
                if declaration is None:
                    return {"action": "pass"}
                else:
                    return {"action": "declare", "declaration": declaration}
        elif self.phase.current == "adjutant":
            pass
        elif self.phase.current == "discard":
            pass
        elif self.phase.current in ["first_round", "rounds"]:
            if self.player == self.state.turn:
                selected = self.select()
                if selected in self.player.possible_cards:
                    return {"action": "select", "selected": selected}
                else:
                    assert False

        return None

    def to_json(self):
        return {"name": self.__class__.name}

    def declare(self):
        """
        By default, AIs don't declare, so always pass
        """
        return None

    def select(self):
        """
        :return: a card
        """

    def decide(self):
        """
        :return: a card which is an adjutant
        """

    def discard(self):
        """
        :return: cards which napoleon doesn't use
        """
