from app.services.log_service import log_request


def test_log_request_flushes_without_committing():
    events = []

    class FakeSession:
        def add(self, instance):
            events.append(("add", instance))

        def flush(self):
            events.append(("flush",))

        def commit(self):
            events.append(("commit",))

        def refresh(self, instance):
            events.append(("refresh", instance))

    db = FakeSession()

    log = log_request(
        db=db,
        user_id=123,
        email="test@example.com",
        phone="+254712345678",
        ip="8.8.8.8",
        risk={
            "risk_score": 42,
            "trust_level": "medium",
            "flags": ["test_flag"],
        },
        endpoint="/risk/score",
        is_overage=True,
        device_id=456,
    )

    assert log.user_id == 123
    assert log.email == "test@example.com"
    assert log.phone == "+254712345678"
    assert log.ip == "8.8.8.8"
    assert log.risk_score == 42
    assert log.trust_level == "medium"
    assert log.flags == ["test_flag"]
    assert log.endpoint == "/risk/score"
    assert log.is_overage is True
    assert log.device_id == 456

    assert [event[0] for event in events] == ["add", "flush"]
    assert events[0][1] is log
