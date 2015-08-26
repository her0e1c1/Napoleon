import enum


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
