from django.test import TestCase
import state


class StateTestCase(TestCase):

    def setUp(self):
        self.pgs = state.PrivateGameState(session_id="test_id", room_id="test_id")

    def tearDown(self):
        for k in self.pgs.conn.keys("*"):
            if k.startswith(b"test_id"):
                self.pgs.conn.delete(k)

    def test_join_and_quit(self):
        pgs = self.pgs
        user_id = 12345
        pgs.user_id = user_id
        assert pgs.conn.hget("test_id_map", "test_id") == b"12345"
        assert pgs.user_id == user_id
        pgs.join()
        assert pgs.conn.zscore("test_id_player_ids", user_id) == 0
        assert pgs.players == [user_id]

        pgs.quit()
        assert pgs.conn.zscore("test_id_player_ids", user_id) is None
        assert pgs.players == []
