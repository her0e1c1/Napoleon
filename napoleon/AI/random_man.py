import random
from . base import BaseAI


class RandomMan(BaseAI):

    def select(self):
        cards = self.player.possible_cards
        index = random.randint(0, len(cards) - 1)
        return cards[index]
