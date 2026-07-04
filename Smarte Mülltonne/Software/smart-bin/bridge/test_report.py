import asyncio
from unittest.mock import AsyncMock, MagicMock

from tcp_bridge import PicoBridge  # gleiches Verzeichnis


def _bridge_with_mock_client():
    bridge = PicoBridge(backend_url="http://test", bin_id=22, poll_interval_s=1.0)
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    bridge.client = MagicMock()
    bridge.client.post = AsyncMock(return_value=resp)
    return bridge


def test_report_hygiene_posts_hygiene_report():
    bridge = _bridge_with_mock_client()
    asyncio.run(bridge._handle_pico_line("REPORT:HYGIENE", MagicMock()))
    bridge.client.post.assert_awaited_once()
    args, kwargs = bridge.client.post.call_args
    assert args[0].endswith("/security/events")
    assert kwargs["json"] == {"bin_id": 22, "event_type": "hygiene_report"}


def test_report_damage_posts_damage_report():
    bridge = _bridge_with_mock_client()
    asyncio.run(bridge._handle_pico_line("REPORT:DAMAGE", MagicMock()))
    args, kwargs = bridge.client.post.call_args
    assert kwargs["json"] == {"bin_id": 22, "event_type": "damage_report"}


def test_unknown_report_kind_does_not_post():
    bridge = _bridge_with_mock_client()
    asyncio.run(bridge._handle_pico_line("REPORT:FOO", MagicMock()))
    bridge.client.post.assert_not_awaited()
