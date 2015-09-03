from django.test import TestCase, Client
from django.core.urlresolvers import reverse
from napoleon.game import state
from napoleon.room.models import Room
from django.contrib.auth.models import User


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
        for k in self.pgs.conn.keys("*"):
            # if k.startswith(b"12345"):
            if k.startswith(b"1_"):
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
