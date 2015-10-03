import random
from . base import BaseAI
from napoleon.game import card


class Taro(BaseAI):

    def select(self):
        cards = list(self.player.possible_cards)

        # lead時、特殊カードがあれば、優先して出す
        if not self.state.board:
            for c in [card.CLUB10, card.CLUB3]:
                if c in cards:
                    return c

            # same 2
            for c in cards:
                if c in list(cards.Joker):
                    continue
                if c.pip == 2:
                    return c

        # 他の出せるカードがあれば、副官のカードは出さない
        if len(cards) > 1:
            if self.state.declaration in cards:
                cards.pop(self.state.declaration)

        index = random.randint(0, len(cards) - 1)
        return cards[index]
