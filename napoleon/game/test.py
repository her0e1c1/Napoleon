from django.test import TestCase
from napoleon.game import state


class StateTestCase(TestCase):

    def setUp(self):
        rid = sid = uid = self.id = "12345"
        # rid = sid = uid = self.id = int("12345")
        state.set_user_id(rid, sid, uid)
        self.pgs = state.PrivateGameState(session_id=sid, room_id=rid)

    def tearDown(self):
        for k in self.pgs.conn.keys("*"):
            if k.startswith(b"12345"):
                self.pgs.conn.delete(k)

    def test_join_and_quit(self):
        pgs = self.pgs
        rid = uid = int(self.id)

        key = state.get_key("map", rid)
        assert pgs.conn.hget(key, uid) == b"12345"
        assert pgs.user_id == uid

        pgs.join()
        key = state.get_key("player_ids", rid)
        assert pgs.player_ids == [uid]

        pgs.quit()
        key = state.get_key("player_ids", rid)
        assert pgs.player_ids == []
