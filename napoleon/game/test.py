from django.test import TestCase, Client
from django.core.urlresolvers import reverse
from napoleon.game import state
from napoleon.room.models import Room
from napoleon.game import card
from napoleon.game.adaptor import RedisAdaptor


class DecideTestCase(TestCase):

    def test_constant(self):
        assert card.NUMBER_OF_CARDS == 54
        assert card.NUMBER_OF_FACE_CARDS == 20

    def test_ace(self):
        # ace wins if there are only plain cards
        P = card.Plain
        c, d, h, s = list(card.Suit)
        assert card.decide([P(1, d), P(3, d), P(10, d)], c) == P(1, d)
        assert card.decide([P(1, d), P(3, d), P(10, d)], d) == P(1, d)
        assert card.decide([P(1, d), P(3, d), P(10, d)], h) == P(1, d)
        assert card.decide([P(1, d), P(3, d), P(10, d)], s) == P(1, d)

    def test_trump(self):
        # a trump wins if there are other cards which is not a trump
        P = card.Plain
        c, d, h, s = list(card.Suit)
        assert card.decide([P(1, c), P(3, c), P(10, c)], c) == P(1, c)
        assert card.decide([P(1, d), P(3, c), P(10, d)], c) == P(3, c)
        assert card.decide([P(1, d), P(3, h), P(10, s)], c) == P(10, s)  # lead won
        assert card.decide([P(1, s), P(3, c), P(10, d)], c) == P(1, s)  # ALMIGHTY won

    def test_joker(self):
        P = card.Plain
        JB = card.Joker.black
        JR = card.Joker.red
        c, d, h, s = list(card.Suit)
        assert card.decide([P(1, c), JB, JR], c) == JB
        assert card.decide([P(1, c), JB, JR], d) == JR

    def test_same_two(self):
        P = card.Plain
        c, d, h, s = list(card.Suit)
        assert card.decide([P(2, c), P(3, c), P(10, c)], c) == P(2, c)

        # no same two occurs
        assert card.decide([P(2, c), P(3, c), c.right_jack], c) == c.right_jack
        assert card.decide([P(2, c), P(3, c), P(10, c)], c, is_first_round=True) == P(10, c)

    def test_yoromeki(self):
        P = card.Plain
        c, d, h, s = list(card.Suit)
        assert card.decide([P(1, s), P(12, h), P(10, c)], c) == P(12, h)
        assert card.decide([P(1, s), P(12, d), P(10, c)], c) == P(1, s)


class StateTestCase(TestCase):
    fixtures = ["user.yaml", "room.yaml"]

    def setUp(self):
        users = [
            {"username": "test", "password": "test"},
            {"username": "test1", "password": "test"},
            {"username": "test2", "password": "test"},
        ]
        self.player_clients = []
        for d in users:
            c = Client(enforce_csrf_checks=False)
            assert c.login(**d)
            self.player_clients.append(c)

        self.room = Room.objects.get(pk=1)
        self.state = state.GameState(RedisAdaptor(self.room.id))
        self.url_join = reverse("napoleon.room.views.join", kwargs={"room_id": self.room.id})
        self.url_quit = reverse("napoleon.room.views.quit", kwargs={"room_id": self.room.id})

    def tearDown(self):
        self.state.flush()

    def test_join_and_quit(self):
        c = self.player_clients[0]
        user_id = int(c.session["_auth_user_id"])
        # sid = c.session["_auth_user_hash"]
        response = c.post(self.url_join)
        assert response.status_code == 302
        assert self.state.players == [self.state.create_player(user_id)]

        response = c.post(self.url_quit)
        assert response.status_code == 302
        assert self.state.players == []

    def _test_start(self):
        for c in self.player_clients:
            assert c.post(self.url_join).status_code == 302
        self.state.start()

        # check if the distributed cards have not changed
        hands = [p.hand for p in self.state.players]
        rest = self.state.rest
        n = sum(len(h) for h in hands) + len(rest)
        assert n == card.NUMBER_OF_CARDS

    def _test_declare(self):
        self._test_start()

        # only one player declares as Napoleon
        # while others passes
        players = list(self.state.players)
        for p in players[1:]:
            p.pass_()
        assert len(list(self.state._passed_players)) == len(players) - 1
        declaration = card.from_int(1)
        p = players[0]
        p.declare(declaration)
        assert self.state.declaration == declaration
        assert p.is_napoleon

    def _test_adjutant(self):
        self._test_declare()

        # Napoleon decides the card of adjutant as culb ace
        p = list(self.state.players)[0]
        adjutant = card.from_int(1)
        p.decide(adjutant)
        assert self.state.adjutant == adjutant

    def test_discard(self):
        self._test_adjutant()

        # Napoleon discards his cards
        # There are three players in this current game.
        # so the number of discards are 6
        p = list(self.state.players)[0]
        num = card.REST[len(self.state.players)]
        assert num == 6
        unused = p.hand[:num]  # discards cards from last to last but 6th
        hand = p.hand[num:] + self.state.rest
        p.add_rest_to_hand()
        p.discard(unused)
        assert unused == self.state.unused
        assert sorted(hand) == sorted(p.hand)
