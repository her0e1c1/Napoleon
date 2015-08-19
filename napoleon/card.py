import enum
import random


class Suit(enum.Enum):
    club = 1
    diamond = 2
    heart = 3
    spade = 4

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


class Joker(enum.Enum):
    red = 53
    black = 54

    def __str__(self):
        if self.value == 53:
            return "JR"
        elif self.value == 54:
            return "JB"

    def __int__(self):
        return self.value

    __repr__ = __str__


class Card(object):

    def __init__(self, pip, suit):
        self.pip = pip
        self.suit = suit

    def __int__(self):
        # return self.pip + 13 * (self.suit.value - 1)
        return self.suit.value + (self.pip - 1) * 4

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

    def __eq__(self, other):
        return self.pip == other.pip and self.suit.value == other.suit.value

    def __lt__(self, other):
        if self.pip == other.pip:
            return self.suit.value <= other.suit.value
        return self.pip <= other.pip

    __le__ = __lt__

    __repr__ = __str__


class Deck(list):
    def to_ints(self):
        return [int(card) for card in self]

deck = Deck([
    Card(p, s)
    for s in list(Suit)
    for p in range(1, 13 + 1)
] + list(Joker))

number_of_cards = len(deck)  # 54

# 3 <= number of players <= 8
REST = {
    3: 6,
    4: 6,
    5: 4,
    6: 6,
    7: 5,
    8: 6,
}


def deal(number_of_players=5):
    """
    :return: (hands, rest)
    """
    d = list(deck)
    random.shuffle(d)
    number_of_rest = REST[number_of_players]
    per_player = int((number_of_cards - number_of_rest) / number_of_players)
    rest = d[:number_of_rest]
    hands = list(zip(*[iter(d[number_of_rest:])] * per_player))
    # return (Deck(hands), Deck(rest))
    return hands, rest


class Declaration(Card):
    pass

declarations = [
    Declaration(p, s)
    for p in range(1, 20 + 1)
    for s in list(Suit)
]
