"""SMS gateways: request shape and phone formatting (no network calls)."""

from app.core.config import get_settings
from app.services.notify import BulkSmsNigeria, TermiiSms, to_international


def test_nigerian_numbers_become_international():
    assert to_international("0803 123 4567") == "2348031234567"
    assert to_international("+234 803 123 4567") == "2348031234567"
    assert to_international("2348031234567") == "2348031234567"


def test_termii_request(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "termii_api_key", "k")
    url, _headers, body = TermiiSms().request("2348031234567", "hi")
    assert url.endswith("/api/sms/send")
    assert body == {"api_key": "k", "to": "2348031234567", "from": s.sms_sender_id, "sms": "hi",
                    "type": "plain", "channel": s.termii_channel}


def test_bulksmsnigeria_request(monkeypatch):
    monkeypatch.setattr(get_settings(), "bulksmsnigeria_api_token", "t")
    url, headers, body = BulkSmsNigeria().request("2348031234567", "hi")
    assert url == "https://www.bulksmsnigeria.com/api/v2/sms"
    assert headers["Authorization"] == "Bearer t"
    assert body["to"] == "2348031234567" and body["body"] == "hi"
