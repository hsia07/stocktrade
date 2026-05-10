import pytest
import os

from automation.control.candidates.TELEGRAM_INBOUND_HARDENING.candidate import TelegramInboundStub


def make_authorized_update(text, chat_id="test_chat", update_id=1):
    return {
        "update_id": update_id,
        "message": {
            "text": text,
            "chat": {"id": chat_id},
        }
    }


def make_unauthorized_update(text, chat_id="other_chat", update_id=1):
    return {
        "update_id": update_id,
        "message": {
            "text": text,
            "chat": {"id": chat_id},
        }
    }


@pytest.fixture
def stub():
    return TelegramInboundStub(token="test_token", chat_id="test_chat")


def test_status_command_returns_state(stub):
    result = stub.parse_update(make_authorized_update("/status"))
    assert result == "/status"
    assert stub.get_last_command_result() == "status_emitted"


def test_unauthorized_chat_rejected(stub):
    for cmd in ["/pause", "/start", "/status"]:
        result = stub.parse_update(make_unauthorized_update(cmd))
        assert result is None, f"{cmd} should be rejected for unauthorized chat"
        assert stub.get_last_command_result() == "rejected", f"{cmd} should set rejected result"


def test_authorized_chat_pause_accepted(stub):
    result = stub.parse_update(make_authorized_update("/pause"))
    assert result == "/pause"
    assert stub.get_last_command_result() == "paused"


def test_authorized_chat_status_accepted(stub):
    result = stub.parse_update(make_authorized_update("/status"))
    assert result == "/status"
    assert stub.get_last_command_result() == "status_emitted"


def test_undefined_round_start_blocked(stub):
    result = stub.parse_update(make_authorized_update("/start"))
    assert result is None
    assert stub.get_last_command_result() == "blocked_no_round"


def test_mock_mode_no_real_api_calls():
    from automation.inbound.telegram_inbound import TelegramInboundReceiver
    receiver = TelegramInboundReceiver(use_mock=True)
    assert receiver.use_mock is True
    updates = receiver._fetch_updates()
    assert updates is None


def test_unknown_command_ignored(stub):
    result = stub.parse_update(make_authorized_update("/unknown"))
    assert result is None
    assert stub.get_last_command_result() is None


def test_random_text_ignored(stub):
    result = stub.parse_update(make_authorized_update("hello world"))
    assert result is None
    assert stub.get_last_command_result() is None


def test_no_hardcoded_secrets_in_source():
    source_path = os.path.join(os.path.dirname(__file__), "..", "..", "inbound", "telegram_inbound.py")
    assert os.path.exists(source_path), "telegram_inbound.py must exist"
    with open(source_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "TELEGRAM_BOT_TOKEN" in content
    assert "os.environ.get" in content


@pytest.mark.parametrize("text,expected_cmd", [
    ("/pause", "/pause"),
    ("/status", "/status"),
    ("/unknown", None),
])
def test_authorized_commands_parametrized(stub, text, expected_cmd):
    result = stub.parse_update(make_authorized_update(text))
    assert result == expected_cmd


def test_command_with_trailing_args(stub):
    result = stub.parse_update(make_authorized_update("/pause now"))
    assert result == "/pause"


def test_status_with_trailing_args(stub):
    result = stub.parse_update(make_authorized_update("/status full"))
    assert result == "/status"


def test_commands_case_insensitive_lower(stub):
    result = stub.parse_update(make_authorized_update("/PAUSE"))
    assert result == "/pause"
