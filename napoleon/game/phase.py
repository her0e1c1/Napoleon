from napoleon.game import card


def get_action(phase, action=None):
    name = "%sAction" % action.title()
    action_class = globals().get(name)
    if action_class is None:
        return None

    if phase == action_class.phase or phase in action_class.phase:
        return action_class


class Action(object):
    phase = ""
    next_phase = ""
    can_next = True

    def __init__(self, player):
        self.player = player
        self._phase = player.state._phase
        self.state = player.state

    def act(self, **kw):
        raise NotImplemented

    def validate(self, **kw):
        raise NotImplemented

    def next(self):
        if self.next_phase:
            self.player.state._phase.current = self.next_phase


class StartAction(Action):
    phase = None
    next_phase = "declare"

    def act(self):
        self.player.state.start()


class DeclareAction(Action):
    phase = "declare"

    @property
    def next_phase(self):
        if self._phase.is_napoleon_determined:
            return "adjutant"

    def act(self, declaration):
        self.player.declare(card.from_int(int(declaration)))


class PassAction(Action):
    phase = "declare"

    @property
    def next_phase(self):
        if self._phase.is_napoleon_determined:
            return "adjutant"
        elif self._phase.are_all_players_passed:
            return "restart"

    def act(self):
        self.player.pass_()


class AdjutantAction(Action):
    phase = "adjutant"
    next_phase = "discard"

    def act(self, adjutant):
        self.player.decide(card.from_int(int(adjutant)))
        self.player.state.set_role(card.from_int(int(adjutant)))
        self.player.add_rest_to_hand()


class DiscardAction(Action):
    phase = "discard"
    next_phase = "first_round"

    def act(self, unused):
        self.player.discard(card.from_list(unused))


class SelectAction(Action):
    phase = ["first_round", "rounds"]

    @property
    def next_phase(self):
        if self._phase.current == "first_round" and self._phase.waiting_next_turn:
            return "rounds"

    @property
    def can_next(self):
        return self.player.is_my_turn

    def act(self, selected):
        # check turn user
        if self.player.state._phase.waiting_next_turn:
            self.next_round()
        self.player.select(card.from_int(int(selected)))

    def next(self):
        self.next_turn()
        if self.next_phase:
            st = self.player.state
            st._phase.current = self.next_phase

    def next_turn(self):
        players = self.state.players
        index = players.index(self.state.turn)
        board = self.state.board

        if 0 <= len(board) < len(players):
            # board is not full
            if 0 <= index < len(players) - 1:
                self.state.turn = players[index + 1]
            else:
                self.state.turn = players[0]
        else:
            winner_id = card.winner(
                board=board,
                player_cards=self.state.player_cards,
                trump_suit=self.state.declaration.suit,
                is_first_round=self.state.phase == "first_round",
            )
            winner = self.state.create_player(winner_id)
            cards = list(board)
            if self.state.phase == "first_round":
                cards += self.state.unused
            faces = [c for c in cards if c.is_faced]
            winner.face = len(faces) + winner.face
            self.state.turn = winner
            self.state._phase.waiting_next_turn = True

    def next_round(self):
        del self.state.board
        del self.state.player_cards
        self.state._phase.waiting_next_turn = False
