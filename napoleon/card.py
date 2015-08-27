import enum
import random


def from_int(i):
    for j in Joker:
        if j.value == i:
            return j
    return Plain.from_int(i)


def from_list(ints):
    ls = []
    for i in ints:
        ls.append(from_int(i))
    return ls


class Suit(enum.Enum):
    club = 1
    diamond = 2
    heart = 3
    spade = 4

    def is_red(self):
        return self.value in [2, 3]

    def is_black(self):
        return not self.is_red

    @property
    def opposite(self):
        if self == Suit.club:
            return Suit.spade
        elif self == Suit.diamond:
            return Suit.heart
        elif self == Suit.heart:
            return Suit.diamond
        elif self == Suit.spade:
            return Suit.club
        raise ValueError("No suit")

    @property
    def right_jack(self):
        return Plain(11, self)

    @property
    def counter_jack(self):
        return Plain(11, self.opposite)


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


class Plain(Mixin):

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
        i -= 1
        p = (i // 4)
        s = list(Suit)[(i) % 4]
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
ALMIGHTY = Plain(1, Suit.spade)
QUEEN = Plain(12, Suit.heart)
CLUB10 = Plain(10, Suit.club)
CLUB3 = Plain(3, Suit.club)


deck = [
    Plain(p, s)
    for s in list(Suit)
    for p in range(1, 13 + 1)
] + list(Joker)

number_of_cards = len(deck)  # 54
NUMBER_OF_CARDS = len(deck)  # 54
NUMBER_OF_FACE_CARDS = len([c for c in deck if c.is_faced])  # 20

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


class Declaration(Plain):

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

    lead = cards[-1]
    if Joker.black in cards and Joker.red in cards:
        if trump_suit.is_black:
            return Joker.black
        else:
            return Joker.red
    elif Joker.black in cards:
        return Joker.black
    elif Joker.red in cards:
        return Joker.red

    rjack = trump_suit.right_jack
    if rjack in cards:
        return rjack

    cjack = trump_suit.counter_jack
    if cjack in cards:
        return cjack

    # same two
    if is_first_round:
        two = Plain(2, lead.suit)
        if two in cards and all([c.suit == lead.suit for c in cards]):
            return two

    trumps = [c for c in cards if c.suit == trump_suit]
    if trumps:
        ace = Plain(1, trump_suit)
        return ace if ace in trumps else max(trumps)

    cards = [c for c in cards if c.suit == lead.suit]
    ace = Plain(1, lead.suit)
    return ace if ace in trumps else max(cards)


def winner(board, player_cards, trump_suit, is_first_round=False, rule=None):
    """
    Decide which player wins at one round.
    :return: user id
    """
    pc = player_cards
    strongest = decide(board, trump_suit, is_first_round, rule)
    return {int(v): k for k, v in pc.items()}[int(strongest)]


def possible_cards(board, hand, trump_suit):
    """
    :return: a list of cards which a player can give
    """
    if not board:
        return hand

    lead = board[-1]
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
    return list(Joker) + [trump_suit.counter_jack]
