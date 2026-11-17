from unittest.mock import MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from app.models.device_fingerprint import DeviceFingerprint
from app.services import device_fingerprint_service as service


def make_device(
    *,
    device_id: int = 10,
    user_id: int = 20,
    device_hash: str = "fingerprint-hash",
) -> DeviceFingerprint:
    return DeviceFingerprint(
        id=device_id,
        user_id=user_id,
        device_hash=device_hash,
        request_count=1,
        is_trusted=False,
        is_blocked=False,
    )


def configure_device_query(db, device):
    query = db.query.return_value
    query.populate_existing.return_value.filter.return_value.one.return_value = (
        device
    )
    return query


def test_get_device_by_hash_scopes_lookup_to_user_and_hash():
    db = MagicMock()
    device = make_device()
    db.query.return_value.filter.return_value.first.return_value = device

    result = service.get_device_by_hash(
        db,
        user_id=20,
        device_hash="fingerprint-hash",
    )

    assert result is device
    db.query.assert_called_once_with(DeviceFingerprint)

    filters = db.query.return_value.filter.call_args.args
    assert len(filters) == 2
    assert {condition.left.key for condition in filters} == {
        "user_id",
        "device_hash",
    }
    assert not db.commit.called


def test_register_device_flushes_without_committing():
    events = []

    class FakeSession:
        def add(self, instance):
            events.append(("add", instance))

        def flush(self):
            events.append(("flush",))
            events[0][1].id = 901

        def commit(self):
            events.append(("commit",))

        def refresh(self, instance):
            events.append(("refresh", instance))

    db = FakeSession()

    device = service.register_device(
        db,
        user_id=20,
        device_hash="new-hash",
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        ),
        accept_language="en-US",
        screen_resolution="1920x1080",
        timezone_name="Africa/Nairobi",
        platform="Win32",
    )

    assert device.id == 901
    assert device.user_id == 20
    assert device.device_hash == "new-hash"
    assert device.browser == "Chrome"
    assert device.browser_version == "120.0.0.0"
    assert device.os == "Windows"
    assert device.os_version == "10"
    assert device.platform == "Desktop"
    assert device.language == "en-US"
    assert device.timezone == "Africa/Nairobi"
    assert device.screen_resolution == "1920x1080"
    assert device.request_count == 1
    assert device.is_trusted is False
    assert device.is_blocked is False
    assert [event[0] for event in events] == ["add", "flush"]


def test_update_device_activity_uses_atomic_owner_scoped_update():
    db = MagicMock()
    device = make_device()
    configure_device_query(db, device)
    db.execute.return_value.scalar_one_or_none.return_value = device.id

    result = service.update_device_activity(
        db,
        device,
        user_agent="Mozilla/5.0 (X11; Linux x86_64) Firefox/125.0",
        accept_language="en-GB",
        screen_resolution="1366x768",
        timezone_name="Europe/London",
        platform="Linux x86_64",
    )

    assert result is device
    statement = db.execute.call_args.args[0]
    compiled = str(statement.compile(dialect=postgresql.dialect()))
    normalized = compiled.lower()

    assert "update device_fingerprints" in normalized
    assert "coalesce" in normalized
    assert "request_count" in normalized
    assert "last_seen" in normalized
    assert "device_fingerprints.id =" in normalized
    assert "device_fingerprints.user_id =" in normalized
    assert not db.commit.called
    assert not db.refresh.called


def test_update_device_activity_raises_when_association_disappears():
    db = MagicMock()
    device = make_device()
    db.execute.return_value.scalar_one_or_none.return_value = None

    with pytest.raises(RuntimeError, match="found no device row"):
        service.update_device_activity(db, device)

    assert not db.commit.called


def test_get_or_create_device_inserts_new_user_owned_association():
    db = MagicMock()
    device = make_device(device_id=31, user_id=20, device_hash="generated-hash")
    configure_device_query(db, device)
    db.execute.return_value.scalar_one_or_none.return_value = device.id

    result = service.get_or_create_device(
        db,
        user_id=20,
        user_agent="Mozilla/5.0 (X11; Linux x86_64) Firefox/125.0",
        accept_language="en-GB",
        screen_resolution="1366x768",
        timezone_name="Europe/London",
        platform="Linux x86_64",
    )

    assert result["device"] is device
    assert result["is_new_device"] is True
    assert result["device_hash"] == service.generate_device_hash(
        user_agent="Mozilla/5.0 (X11; Linux x86_64) Firefox/125.0",
        accept_language="en-GB",
        screen_resolution="1366x768",
        timezone_name="Europe/London",
        platform="Linux x86_64",
    )

    statement = db.execute.call_args.args[0]
    compiled = str(statement.compile(dialect=postgresql.dialect()))
    normalized = compiled.lower()

    assert "on conflict (user_id, device_hash) do nothing" in normalized
    assert "returning device_fingerprints.id" in normalized
    assert not db.commit.called


def test_get_or_create_device_updates_existing_user_association(monkeypatch):
    db = MagicMock()
    existing_device = make_device(device_id=42, user_id=20)
    configure_device_query(db, existing_device)
    db.execute.return_value.scalar_one_or_none.return_value = None

    monkeypatch.setattr(
        service,
        "generate_device_hash",
        lambda **kwargs: "fingerprint-hash",
    )

    lookup = MagicMock(return_value=existing_device)
    activity_update = MagicMock(return_value=existing_device)

    monkeypatch.setattr(service, "get_device_by_hash", lookup)
    monkeypatch.setattr(service, "update_device_activity", activity_update)

    result = service.get_or_create_device(
        db,
        user_id=20,
        user_agent="Mozilla/5.0 Firefox/125.0",
        accept_language="en-GB",
        screen_resolution="1366x768",
        timezone_name="Europe/London",
        platform="Linux x86_64",
    )

    assert result == {
        "device": existing_device,
        "is_new_device": False,
        "device_hash": "fingerprint-hash",
    }

    lookup.assert_called_once_with(db, 20, "fingerprint-hash")
    activity_update.assert_called_once()
    assert activity_update.call_args.args == (db, existing_device)
    assert not db.commit.called


def test_get_or_create_device_rejects_missing_conflicting_association(
    monkeypatch,
):
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = None

    monkeypatch.setattr(
        service,
        "generate_device_hash",
        lambda **kwargs: "fingerprint-hash",
    )
    monkeypatch.setattr(
        service,
        "get_device_by_hash",
        lambda *args: None,
    )

    with pytest.raises(
        RuntimeError,
        match="disappeared during conflict handling",
    ):
        service.get_or_create_device(
            db,
            user_id=20,
            user_agent="Mozilla/5.0 Firefox/125.0",
            accept_language="en-GB",
            screen_resolution="1366x768",
            timezone_name="Europe/London",
            platform="Linux x86_64",
        )

    assert not db.commit.called


@pytest.mark.parametrize(
    ("helper", "attribute", "expected"),
    [
        (service.mark_device_as_trusted, "is_trusted", True),
        (service.mark_device_as_untrusted, "is_trusted", False),
        (service.mark_device_as_blocked, "is_blocked", True),
        (service.mark_device_as_unblocked, "is_blocked", False),
    ],
)
def test_trust_and_block_helpers_only_mutate_managed_device(
    helper,
    attribute,
    expected,
):
    db = MagicMock()
    device = make_device()

    result = helper(db, device)

    assert result is device
    assert getattr(device, attribute) is expected
    assert not db.commit.called
    assert not db.refresh.called


def test_user_device_helpers_keep_user_scope():
    db = MagicMock()
    device = make_device()
    db.query.return_value.filter.return_value.first.return_value = device

    result = service.get_current_device(
        db,
        user_id=20,
        device_hash="fingerprint-hash",
    )

    assert result is device
    filters = db.query.return_value.filter.call_args.args
    assert len(filters) == 2
    assert {condition.left.key for condition in filters} == {
        "user_id",
        "device_hash",
    }
    assert not db.commit.called
