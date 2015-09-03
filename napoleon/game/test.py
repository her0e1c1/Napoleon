from django.test import TestCase, Client
from django.core.urlresolvers import reverse
from napoleon.game import state
from napoleon.room.models import Room
from napoleon import card


class StateTestCase(TestCase):
    fixtures = ["user.yaml", "room.yaml"]

    def setUp(self):
        self.room = Room.objects.get(pk=1)
        self.url_quit = reverse("napoleon.room.views.quit", kwargs={"room_id": self.room.id})
        self.url_join = reverse("napoleon.room.views.join", kwargs={"room_id": self.room.id})

        self.c = Client(enforce_csrf_checks=False)
        assert self.c.login(username="test", password='test')
        self.user_id = int(self.c.session["_auth_user_id"])
        sid = self.c.session["_auth_user_hash"]
        self.pgs = state.PrivateGameState(user_id=self.user_id, session_id=sid, room_id=self.room.id)

    def tearDown(self):
        prefix = ("%s_" % self.room.id).encode("utf-8")
        for k in self.pgs.conn.keys("*"):
            if k.startswith(prefix):
                self.pgs.conn.delete(k)
        self.c.logout

    def test_join_and_quit(self):
        pgs = self.pgs

        response = self.c.post(self.url_join)
        assert response.status_code == 302
        assert pgs.player_ids == [self.user_id]

        response = self.c.post(self.url_quit)
        assert response.status_code == 302
        assert pgs.player_ids == []


class State1TestCase(TestCase):
    fixtures = ["user.yaml", "room.yaml"]

    def setUp(self):
        users = [
            {"username": "test", "password": "test"},
            {"username": "test1", "password": "test"},
            {"username": "test2", "password": "test"},
        ]
        self.players = []
        for d in users:
            c = Client(enforce_csrf_checks=False)
            assert c.login(**d)
            self.players.append(c)

        self.room = Room.objects.get(pk=1)
        self.state = state.GameState(self.room.id)
        self.url_join = reverse("napoleon.room.views.join", kwargs={"room_id": self.room.id})

    def tearDown(self):
        self.state.flush()

    def _test_start(self):
        for c in self.players:
            assert c.post(self.url_join).status_code == 302
        self.state.start()
        hands = [p.hand for p in self.state.players]
        rest = self.state.rest
        n = sum(len(h) for h in hands) + len(rest)
        assert n == card.NUMBER_OF_CARDS

    def _test_declare(self):
        self._test_start()
        players = list(self.state.players)
        for p in players[1:]:
            p.pass_()
        assert len(list(self.state.passed_players)) == len(players) - 1
        declaration = card.from_int(1)
        p = players[0]
        p.declare(declaration)
        assert self.state.declaration == declaration
        assert p.is_napoleon

    def _test_adjutant(self):
        self._test_declare()
        p = list(self.state.players)[0]
        adjutant = card.from_int(1)
        p.decide(adjutant)
        assert self.state.adjutant == adjutant

    def test_discard(self):
        self._test_adjutant()
        p = list(self.state.players)[0]
        num = 6
        unused = p.hand[:num]
        hand = p.hand[num:] + self.state.rest
        p.discard(unused)
        assert unused == self.state.unused
        assert sorted(hand) == sorted(p.hand)
