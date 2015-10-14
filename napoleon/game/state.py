import enum
import logging

from napoleon.game import card
from napoleon.game.adaptor import RedisAdaptor


logger = logging.getLogger(__name__)


class Role(enum.Enum):
    napoleon_forces = 1
    allied_forces = 2


class Player(object):

    def __init__(self, user_id, state):
        if user_id is None:
            raise ValueError("user_id must not be None")
        self.adaptor = RedisAdaptor(state.room_id, user_id, state.adaptor.conn)
        self.user_id = user_id
        self.state = state

    def __repr__(self):
        return "Player {self.user_id}".format(self=self)

    def __eq__(self, other):
        if hasattr(other, "user_id"):
            return self.user_id == other.user_id

    @property
    def is_napoleon(self):
        return self.state.napoleon == self.user_id

    @property
    def is_joined(self):
        return self in self.state.players

    @property
    def is_passed(self):
        return self in self.state._passed_players

    @property
    def is_my_turn(self):
        return self == self.state.turn

    @property
    def is_winner(self):
        if self.state.phase.did_napoleon_forces_win is True:
            return True if self.is_napoleon_forces else False
        if self.state.phase.did_allied_forces_win is True:
            return True if self.is_allied_forces else False

    @property
    def is_napoleon_forces(self):
        return self.role == Role.napoleon_forces

    @property
    def is_allied_forces(self):
        return self.role == Role.allied_forces

    @property
    def current_card(self):
        return self.state.player_cards.get(str(self.user_id))

    def select(self, card):
        """
        A player selects a card
        """
        if len(self.state.board) >= len(self.state.players):
            raise ValueError("A player can't select a card because the board is full.")

        if card not in self.possible_cards:
            raise ValueError("A player can't select a card he doesn't have.")

        if self.can_betray(card):
            if self.role == Role.napoleon_forces:
                self.role = Role.allied_forces
            else:
                self.role = Role.napoleon_forces

        self.adaptor.rem_list("hand", int(card))
        self.state.board = card
        self.state.player_cards = (self.user_id, card)

    def can_betray(self, c):
        if (c == card.CLUB10
            and not self.state.board
            and not self.is_napoleon
            and len(self.state._allied_forces) > 1
        ):
            return True
        else:
            return False

    def pass_(self):
        self.adaptor.set_list("pass_ids", self.user_id, delete=False)

    def declare(self, declaration):
        """
        A player declaresf as Napoleon if he calls a larger card.
        """
        d = self.state.declaration
        if not d or int(d) < int(declaration):
            self.state.declaration = declaration
            self.state.napoleon = self.user_id
            self.state.turn = Player(self.user_id, self.state)

    def decide(self, adjutant):
        self.state.adjutant = adjutant

    def discard(self, unused):
        hand = self.hand
        for u in unused:
            try:
                hand.remove(u)
            except ValueError:
                raise ValueError("A player can't discard a card he doesn't have.")

        self.hand = hand
        self.state.unused = unused

    def add_rest_to_hand(self):
        """
        After napoleon decides an adjutant, he gets cards from the rest.
        """
        self.hand = self.hand + self.state.rest

    @property
    def number_of_hand(self):
        return len(self.hand)

    @property
    def hand(self):
        return card.from_list(self.adaptor.get_list("hand", type=int))

    @hand.setter
    def hand(self, hand):
        self.adaptor.set_list("hand", sorted(int(i) for i in hand))

    @property
    def face(self):
        return self.adaptor.get("face", type=int)

    @face.setter
    def face(self, value):
        self.adaptor.set("face", value)

    @property
    def role(self):
        d = self.adaptor.get("role", type=int)
        if d:
            return Role(d)

    @role.setter
    def role(self, role):
        return self.adaptor.set("role", role.value)

    @property
    def possible_cards(self):
        # wait for the next turn before playing a lead card
        if len(self.state.board) == len(self.state.players):
            return self.hand
        d = self.state.declaration
        if d:
            return card.possible_cards(self.state.board, self.hand, d.suit)
        else:
            return []


class Phase(object):

    def __init__(self, state):
        self.state = state
        self.adaptor = state.adaptor

    @property
    def current(self):
        return self.adaptor.get("phase")

    @current.setter
    def current(self, value):
        self.adaptor.set("phase", value)

    @property
    def waiting_next_turn(self):
        return bool(self.adaptor.get("waiting_next_turn", type=int))

    @waiting_next_turn.setter
    def waiting_next_turn(self, value):
        value = 1 if value else 0
        return self.adaptor.set("waiting_next_turn", value)

    @property
    def is_appropriate_player_number(self):
        return len(self.state.players) in card.RANGE_OF_PLAYERS

    @property
    def is_napoleon_determined(self):
        return bool(self.state.napoleon) and len(self.state._passed_players) >= len(self.state.players) - 1

    @property
    def are_all_players_passed(self):
        return len(self.state._passed_players) == len(self.state.players)

    @property
    def is_finished(self):
        if self.did_napoleon_forces_win or self.did_allied_forces_win:
            return True
        return sum([len(p.hand) for p in self.state.players]) == 0

    @property
    def did_napoleon_forces_win(self):
        n = self.state.number_of_face_cards_of_napoleon_forces
        if n == card.NUMBER_OF_FACE_CARDS:
            return False
        if self.state.declaration:
            return n >= self.state.declaration.pip
        else:
            return False

    @property
    def did_allied_forces_win(self):
        n = self.state.number_of_face_cards_of_napoleon_forces
        a = self.state.number_of_face_cards_of_allied_forces
        if self.state.declaration:
            if n == card.NUMBER_OF_CARDS:
                return True
            else:
                return a > card.NUMBER_OF_FACE_CARDS - self.state.declaration.pip
        else:
            return False


class GameState(object):

    def __init__(self, adaptor):
        self.adaptor = adaptor
        self.room_id = adaptor.room_id
        self.phase = Phase(self)

    def create_player(self, user_id):
        if user_id is None:
            raise ValueError("user_id must not be None")

        # TODO: make user_id type of str
        d = self.adaptor.get_dict("isAI", type=bool)
        if d.get(str(user_id)):  # b/c
            return PlayerAI(user_id, self)

        return PlayerHuman(user_id, self)

    def flush(self):
        """
        Delete all data about this room.
        """
        self.adaptor.flush()

    def start(self, restart=False):
        """
        Distribute cards to each player and leave the rest of cards which napoleon can change
        """
        if restart:
            del self._passed_players

        players = list(self.players)
        number_of_players = len(players)
        if number_of_players <= 2:
            raise ValueError

        hands, rest = card.deal(number_of_players)
        self.rest = rest
        for (p, h) in zip(players, hands):
            p.hand = h
            p.face = 0

    def set_role(self, adjutant=None):
        """
        After deciding an adjutant, the role of each player is set
        """
        for p in self.players:
            if p.is_napoleon:
                role = Role.napoleon_forces
            else:
                if self.adjutant in p.hand:
                    role = Role.napoleon_forces
                else:
                    role = Role.allied_forces
            p.role = role

    @property
    def players(self):
        l = []
        for pid in self.adaptor.get_list("player_ids", type=int):
            l.append(self.create_player(user_id=pid))
        return l

    @property
    def player_AIs(self):
        return [p for p in self.players if p.is_AI]

    @property
    def _passed_players(self):
        pids = self.adaptor.get_list("pass_ids", type=int)
        return [p for p in self.players if p.user_id in pids]

    @_passed_players.deleter
    def _passed_players(self):
        self.adaptor.delete("pass_ids")

    @property
    def rest(self):
        return card.from_list(self.adaptor.get_list("rest", type=int))

    @rest.setter
    def rest(self, rest):
        self.adaptor.set_list("rest", sorted(int(c) for c in rest))

    @property
    def declaration(self):
        d = self.adaptor.get("declaration")
        if d:
            return card.Declaration.from_int(int(d))

    @declaration.setter
    def declaration(self, declaration):
        self.adaptor.set("declaration", int(declaration))

    @property
    def napoleon(self):
        return self.adaptor.get("napoleon", type=int)

    @napoleon.setter
    def napoleon(self, user_id):
        return self.adaptor.set("napoleon", user_id)

    @property
    def turn(self):
        user_id = self.adaptor.get("turn", type=int)
        if user_id:
            return self.create_player(user_id)

    @property
    def turn_user_id(self):
        if self.turn:
            return self.turn.user_id

    @turn.setter
    def turn(self, user_id):
        if isinstance(user_id, Player):
            user_id = user_id.user_id
        self.adaptor.set("turn", user_id)

    @property
    def adjutant(self):
        d = self.adaptor.get("adjutant")
        if d:
            return card.from_int(int(d))

    @adjutant.setter
    def adjutant(self, adjutant):
        return self.adaptor.set("adjutant", int(adjutant))

    @property
    def unused(self):
        return card.from_list(self.adaptor.get_list("unused", type=int))

    @property
    def unused_faces(self):
        return [c for c in self.unused if c.is_faced]

    @unused.setter
    def unused(self, cards):
        self.adaptor.set_list("unused", sorted(int(i) for i in cards))

    @property
    def board(self):
        return card.from_list(self.adaptor.get_list("board", type=int))

    @board.setter
    def board(self, card):
        self.adaptor.set_list("board", int(card), delete=False)

    @board.deleter
    def board(self):
        self.adaptor.delete("board")

    @property
    def player_cards(self):
        d = self.adaptor.get_dict("player_cards", type=int)
        if d:
            return {k: card.from_int(v) for k, v in d.items()}
        else:
            return {}

    @player_cards.setter
    def player_cards(self, value):
        user_id, card = value
        self.adaptor.set_dict("player_cards", user_id, int(card))

    @player_cards.deleter
    def player_cards(self):
        self.adaptor.delete("player_cards")

    @property
    def number_of_face_cards_of_napoleon_forces(self):
        return sum([p.face for p in self.players if p.is_napoleon_forces])

    @property
    def number_of_face_cards_of_allied_forces(self):
        return sum([p.face for p in self.players if p.is_allied_forces])


class PlayerHuman(Player):

    is_AI = False

    def __init__(self, user_id, state):
        super().__init__(user_id, state)
        self.user = self.adaptor.get_dict("user")


class PlayerAI(Player):

    is_AI = True

    def __init__(self, user_id, state):
        super().__init__(user_id, state)
        self.user = self.adaptor.get_dict("AI")
        name = self.user["username"]
        from napoleon import AI
        self._AI = getattr(AI, name)(self)
