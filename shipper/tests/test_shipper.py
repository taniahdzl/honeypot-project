import hashlib
import json

from shipper.shipper import cowrie_line_to_payload, parse_event_time


def test_parse_event_time_accepts_cowrie_zulu_timestamp():
    assert parse_event_time("2026-05-19T12:34:56Z") == "2026-05-19T12:34:56+00:00"


def test_parse_event_time_rejects_empty_or_invalid_values():
    assert parse_event_time(None) is None
    assert parse_event_time("") is None
    assert parse_event_time("not-a-date") is None


def test_cowrie_line_to_payload_maps_expected_fields():
    data = {
        "timestamp": "2026-05-19T12:34:56Z",
        "src_ip": "203.0.113.44",
        "eventid": "cowrie.login.failed",
        "username": "root",
        "password": "password",
        "input": "uname -a",
    }

    payload = cowrie_line_to_payload(data)

    expected_hash = hashlib.sha256(
        json.dumps(data, sort_keys=True, default=str).encode()
    ).hexdigest()

    assert payload == {
        "event_time": "2026-05-19T12:34:56+00:00",
        "src_ip": "203.0.113.44",
        "event_type": "cowrie.login.failed",
        "username": "root",
        "password": "password",
        "command": "uname -a",
        "raw_json": data,
        "source_hash": expected_hash,
    }
