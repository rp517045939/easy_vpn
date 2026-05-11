import os
import sys
import unittest
from pathlib import Path


os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "password")
os.environ.setdefault("CLIENT_TOKEN", "client-token")

ROOT = Path(__file__).resolve().parents[1]
SERVER_DIR = ROOT / "server"
sys.path.insert(0, str(SERVER_DIR))

from tunnel_manager import TunnelManager  # noqa: E402


class FakeWebSocket:
    def __init__(self, manager=None, replacement=None, *, fail_send=False):
        self.manager = manager
        self.replacement = replacement
        self.fail_send = fail_send
        self.sent = []
        self.closed = False

    async def send_text(self, text):
        if self.replacement is not None:
            await self.manager.connect("nas", self.replacement)
        if self.fail_send:
            raise RuntimeError("send failed")
        self.sent.append(text)

    async def close(self):
        self.closed = True


class TunnelManagerHeartbeatTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_heartbeat_does_not_remove_reconnected_client(self):
        manager = TunnelManager()
        new_ws = FakeWebSocket()
        old_ws = FakeWebSocket(manager)

        await manager.connect("nas", old_ws)
        old_ws.replacement = new_ws
        old_ws.fail_send = True

        await manager._heartbeat_once()

        self.assertTrue(manager.is_online("nas"))
        self.assertIs(manager._clients["nas"]["ws"], new_ws)
        self.assertTrue(old_ws.closed)


if __name__ == "__main__":
    unittest.main()
