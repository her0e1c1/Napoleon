import enum
import random


def from_int(i):
    for j in Joker:
        if j.value == i:
            return j
    return Card.from_int(i)


def from_list(ints):
    ls = []
    for i in ints:
        ls.append(from_int(i))
    return ls


def opposite_suit(suit):
    if suit == Suit.club:
        return Suit.spade
    elif suit == Suit.diamond:
        return Suit.heart
    elif suit == Suit.heart:
        return Suit.diamond
    elif suit == Suit.spade:
        return Suit.club

    raise ValueError("No suit")


def right_jack(trump_suit):
    return Card(11, trump_suit)


def counter_jack(trump_suit):
    return Card(11, opposite_suit(trump_suit))


class Suit(enum.Enum):
    club = 1
    diamond = 2
    heart = 3
    spade = 4

    def is_red(self):
        return self.value in [2, 3]

    def is_black(self):
        return not self.is_red

    def __str__(self):
        if self.value == 1:
            return "\u2663"
        elif self.value == 2:
            return "\u2662"
        elif self.value == 3:
            return "\u2661"
        elif self.value == 4:
            return "\u2660"

    __repr__ = __str__


class Mixin(object):

    def order_by_suit(self):
        try:
            return (self.suit.value - 1) * 13 + self.pip
        except:
            return 100

    def __eq__(self, other):
        return int(self) == int(other)

    def __lt__(self, other):
        return int(self) <= int(other)

    __le__ = __lt__

    __repr__ = lambda self: self.__str__()


class Card(Mixin):

    def __init__(self, pip, suit):
        self.pip = pip
        self.suit = suit

    def __int__(self):
        return self.suit.value + (self.pip - 1) * 4

    def to_json(self):
        return {
            "pip": self.pip,
            "suit": self.suit.value,
            "str": str(self),
            "value": int(self),
            "order_by_suit": self.order_by_suit(),
        }

    @property
    def is_faced(self):
        return self.pip in [10, 11, 12, 13, 1]

    @classmethod
    def from_int(cls, i):
        p = (i // 4)
        s = list(Suit)[(i - 1) % 4]
        return cls(p + 1, s)

    def __str__(self):
        pip = self.pip
        if pip == 11:
            pip = "J"
        elif pip == 12:
            pip = "Q"
        elif pip == 13:
            pip = "K"
        elif pip == 1:
            pip = "A"
        else:
            pip = str(pip)
        return str(self.suit) + pip


class Joker(Mixin, enum.Enum):
    red = 53
    black = 54

    @property
    def pip(self):
        return None

    @property
    def suit(self):
        return None

    def __str__(self):
        if self.value == 53:
            return "JR"
        elif self.value == 54:
            return "JB"

    def to_json(self):
        return {
            "str": str(self),
            "value": int(self),
            "order_by_suit": self.order_by_suit(),
        }

    def __int__(self):
        return self.value

    @property
    def is_faced(self):
        return False


# special cards
ALMIGHTY = Card(1, Suit.spade)
QUEEN = Card(12, Suit.heart)
CLUB10 = Card(10, Suit.club)
CLUB3 = Card(3, Suit.club)


deck = [
    Card(p, s)
    for s in list(Suit)
    for p in range(1, 13 + 1)
] + list(Joker)

number_of_cards = len(deck)  # 54
NUMBER_OF_CARDS = len(deck)  # 54

REST = {
    3: 6,
    4: 6,
    5: 4,
    6: 6,
    7: 5,
    8: 6,
}
RANGE_OF_PLAYERS = REST.keys()


def deal(number_of_players=5):
    """
    :return: (hands, rest)
    """
    d = list(deck)
    random.shuffle(d)
    number_of_rest = REST[number_of_players]
    per_player = int((NUMBER_OF_CARDS - number_of_rest) / number_of_players)
    rest = d[:number_of_rest]
    hands = list(zip(*[iter(d[number_of_rest:])] * per_player))
    return hands, rest


class Declaration(Card):

    @property
    def over(self):
        return [d for d in declarations if d > self]

declarations = [
    Declaration(p, s)
    for p in range(1, 20 + 1)
    for s in list(Suit)
]


def decide(cards, trump_suit, is_first_round=False, rule=None):
    if len(cards) <= 0:
        raise

    if ALMIGHTY in cards:
        if QUEEN in cards:
            return QUEEN
        else:
            return ALMIGHTY

    lead = cards[0]
    if Joker.black in cards and Joker.red in cards:
        if trump_suit.is_black:
            return Joker.black
        else:
            return Joker.red
    elif Joker.black in cards:
        return Joker.black
    elif Joker.red in cards:
        return Joker.red

    rjack = right_jack(trump_suit)
    if rjack in cards:
        return rjack

    cjack = counter_jack(trump_suit)
    if cjack in cards:
        return cjack

    # same two
    if is_first_round:  # ignore first round
        two = Card(2, lead.suit)
        if two in cards and all([c.suit == lead.suit for c in cards]):
            return two

    trumps = [c for c in cards if c.suit == trump_suit]
    if trumps:
        return max(trumps)
    # return max(trumps, key=lambda c: c.strong(trump_suit))

    return max([c for c in cards if c.suit == lead.suit])


def winner(board, player_ids, last_turn, trump_suit, rule=None):
    """
    Decide which player wins at one round.
    :return: user id
    """
    pc = player_cards(board, player_ids, last_turn)
    strongest = decide(board, trump_suit, rule)
    return {int(v): k for k, v in pc.items()}[int(strongest)]


def possible_cards(board, hand, trump_suit):
    """
    :return: a list of cards which a player can give
    """
    if not board:
        return hand

    lead = board[0]
    if lead == CLUB3 in hand:
        return list(Joker)

    cs = []
    for h in hand:
        if h.suit == lead.suit:
            cs.append(h)
    if not cs:
        return hand

    return cs + always_cards(trump_suit)


def always_cards(trump_suit):
    return list(Joker) + [counter_jack(trump_suit)]


def player_cards(board, player_ids, turn, reverse=False):
    # The player in turn doesn't give a card yet
    try:
        current_player_index = player_ids.index(turn)
    except ValueError:
        raise

    number_of_players = len(player_ids)
    number_of_cards = len(board)
    if number_of_cards > number_of_players:
        raise

    pc = {}
    first_player_index = (current_player_index - number_of_cards) % number_of_players
    for bindex, i in enumerate(range(first_player_index, first_player_index + number_of_players)):
        if bindex < number_of_cards:
            card = board[bindex]
        else:
            card = None
        pid = player_ids[i % number_of_players]
        pc[pid] = card

    return pc
