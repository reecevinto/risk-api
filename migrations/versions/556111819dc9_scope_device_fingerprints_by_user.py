"""scope device fingerprints by user

Revision ID: 556111819dc9
Revises: 903267aa7fb0

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "556111819dc9"
down_revision: Union[str, Sequence[str], None] = "903267aa7fb0"
branch_labels = None
depends_on = None


HASH_INDEX = "ix_device_fingerprints_device_hash"
USER_HASH_CONSTRAINT = "uq_device_fingerprints_user_id_device_hash"
USER_ID_CONSTRAINT = "uq_device_fingerprints_user_id_id"
OLD_DEVICE_FK = "request_logs_device_id_fkey"
NEW_DEVICE_FK = "fk_request_logs_user_device"


def _count(statement: str) -> int:
    bind = op.get_bind()
    return int(bind.execute(sa.text(statement)).scalar_one())


def _require_postgresql() -> None:
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError(
            "This migration requires PostgreSQL."
        )


def _lock_device_tables() -> None:
    """Prevent concurrent writes while device ownership is migrated."""
    op.execute(
        sa.text(
            """
            LOCK TABLE device_fingerprints, request_logs
            IN SHARE ROW EXCLUSIVE MODE
            """
        )
    )


def _validate_upgrade_schema() -> None:
    """Verify the expected pre-migration schema before changing anything."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    required_tables = {"device_fingerprints", "request_logs"}
    missing_tables = {
        table for table in required_tables
        if not inspector.has_table(table)
    }
    if missing_tables:
        raise RuntimeError(
            f"Required tables are missing: {sorted(missing_tables)}"
        )

    device_columns = {
        column["name"]
        for column in inspector.get_columns("device_fingerprints")
    }
    request_columns = {
        column["name"]
        for column in inspector.get_columns("request_logs")
    }

    required_device_columns = {
        "id",
        "user_id",
        "device_hash",
        "browser",
        "browser_version",
        "os",
        "os_version",
        "platform",
        "language",
        "timezone",
        "screen_resolution",
        "first_seen",
        "last_seen",
        "request_count",
        "is_trusted",
        "is_blocked",
        "created_at",
    }
    required_request_columns = {
        "id",
        "user_id",
        "device_id",
        "created_at",
    }

    if not required_device_columns.issubset(device_columns):
        raise RuntimeError(
            "device_fingerprints does not have the expected columns."
        )

    if not required_request_columns.issubset(request_columns):
        raise RuntimeError(
            "request_logs does not have the expected columns."
        )

    indexes = {
        index["name"]: index
        for index in inspector.get_indexes("device_fingerprints")
    }
    hash_index = indexes.get(HASH_INDEX)

    if (
        hash_index is None
        or hash_index.get("unique") is not True
        or hash_index.get("column_names") != ["device_hash"]
    ):
        raise RuntimeError(
            "The expected unique device_hash index was not found."
        )

    request_fks = inspector.get_foreign_keys("request_logs")
    old_device_fks = [
        fk for fk in request_fks
        if fk.get("name") == OLD_DEVICE_FK
    ]

    if len(old_device_fks) != 1:
        raise RuntimeError(
            f"Expected exactly one foreign key named {OLD_DEVICE_FK}."
        )

    old_fk = old_device_fks[0]

    if (
        old_fk.get("constrained_columns") != ["device_id"]
        or old_fk.get("referred_table") != "device_fingerprints"
        or old_fk.get("referred_columns") != ["id"]
    ):
        raise RuntimeError(
            "The existing request_logs device foreign key "
            "does not have the expected definition."
        )

    request_user_fks = [
        fk
        for fk in request_fks
        if (
            fk.get("constrained_columns") == ["user_id"]
            and fk.get("referred_table") == "users"
            and fk.get("referred_columns") == ["id"]
        )
    ]

    if len(request_user_fks) != 1:
        raise RuntimeError(
            "The request_logs user ownership foreign key "
            "is missing or ambiguous."
        )

    device_id_column = next(
        column
        for column in inspector.get_columns("request_logs")
        if column["name"] == "device_id"
    )

    if not device_id_column["nullable"]:
        raise RuntimeError(
            "request_logs.device_id must remain nullable."
        )

    device_fks = inspector.get_foreign_keys("device_fingerprints")
    user_fks = [
        fk for fk in device_fks
        if (
            fk.get("constrained_columns") == ["user_id"]
            and fk.get("referred_table") == "users"
            and fk.get("referred_columns") == ["id"]
        )
    ]
    if len(user_fks) != 1:
        raise RuntimeError(
            "The device_fingerprints user ownership foreign key "
            "is missing or ambiguous."
        )

    existing_unique_names = {
        constraint.get("name")
        for constraint in inspector.get_unique_constraints(
            "device_fingerprints"
        )
    }
    if (
        USER_HASH_CONSTRAINT in existing_unique_names
        or USER_ID_CONSTRAINT in existing_unique_names
    ):
        raise RuntimeError(
            "One or more target unique constraints already exist."
        )

    if _count(
        """
        SELECT COUNT(*)
        FROM (
            SELECT device_hash
            FROM device_fingerprints
            GROUP BY device_hash
            HAVING COUNT(*) > 1
        ) AS duplicate_hashes
        """
    ):
        raise RuntimeError(
            "Duplicate device hashes exist before migration."
        )

    if _count(
        """
        SELECT COUNT(*)
        FROM request_logs AS rl
        LEFT JOIN device_fingerprints AS df
            ON df.id = rl.device_id
        WHERE rl.device_id IS NOT NULL
          AND df.id IS NULL
        """
    ):
        raise RuntimeError(
            "Orphaned request_logs.device_id references exist."
        )

    if _count(
        """
        SELECT COUNT(*)
        FROM device_fingerprints AS df
        LEFT JOIN users AS u ON u.id = df.user_id
        WHERE u.id IS NULL
        """
    ):
        raise RuntimeError(
            "Orphaned device_fingerprints.user_id references exist."
        )


def _validate_normalized_ownership() -> None:
    """Ensure every linked request log belongs to its device association."""
    if _count(
        """
        SELECT COUNT(*)
        FROM request_logs AS rl
        JOIN device_fingerprints AS df
            ON df.id = rl.device_id
        WHERE rl.user_id <> df.user_id
        """
    ):
        raise RuntimeError(
            "Device ownership mismatches remain after backfill."
        )

    if _count(
        """
        SELECT COUNT(*)
        FROM request_logs AS rl
        LEFT JOIN device_fingerprints AS df
            ON df.id = rl.device_id
        WHERE rl.device_id IS NOT NULL
          AND df.id IS NULL
        """
    ):
        raise RuntimeError(
            "Orphaned device references remain after backfill."
        )


def upgrade() -> None:
    """Scope device fingerprints to individual users."""
    _require_postgresql()
    _lock_device_tables()
    _validate_upgrade_schema()

    # The composite unique constraints are required as the target
    # of the composite request_logs foreign key.
    op.create_unique_constraint(
        USER_HASH_CONSTRAINT,
        "device_fingerprints",
        ["user_id", "device_hash"],
    )
    op.create_unique_constraint(
        USER_ID_CONSTRAINT,
        "device_fingerprints",
        ["user_id", "id"],
    )

    # The global unique hash index must be removed before creating
    # additional per-user associations for the same fingerprint.
    op.drop_index(
        HASH_INDEX,
        table_name="device_fingerprints",
    )

    # Create one additional association for each user who historically
    # referenced a fingerprint owned by another user.
    #
    # Existing owner rows are never updated. New associations begin
    # untrusted and unblocked, with counters and timestamps derived
    # from that user's own historical request logs.
    op.execute(
        sa.text(
            """
            INSERT INTO device_fingerprints (
                user_id,
                device_hash,
                browser,
                browser_version,
                os,
                os_version,
                platform,
                language,
                timezone,
                screen_resolution,
                first_seen,
                last_seen,
                request_count,
                is_trusted,
                is_blocked,
                created_at
            )
            SELECT
                rl.user_id,
                df.device_hash,
                df.browser,
                df.browser_version,
                df.os,
                df.os_version,
                df.platform,
                df.language,
                df.timezone,
                df.screen_resolution,
                COALESCE(MIN(rl.created_at), df.first_seen),
                COALESCE(MAX(rl.created_at), df.last_seen),
                COUNT(*)::integer,
                FALSE,
                FALSE,
                COALESCE(MIN(rl.created_at), df.created_at)
            FROM request_logs AS rl
            JOIN device_fingerprints AS df
                ON df.id = rl.device_id
            WHERE rl.user_id <> df.user_id
            GROUP BY
                rl.user_id,
                df.id,
                df.device_hash,
                df.browser,
                df.browser_version,
                df.os,
                df.os_version,
                df.platform,
                df.language,
                df.timezone,
                df.screen_resolution,
                df.first_seen,
                df.last_seen,
                df.created_at
            """
        )
    )

    # Redirect only cross-user historical links to the corresponding
    # new association. Null device_id values remain null.
    op.execute(
        sa.text(
            """
            UPDATE request_logs AS rl
            SET device_id = association.id
            FROM device_fingerprints AS original,
                 device_fingerprints AS association
            WHERE rl.device_id = original.id
              AND rl.user_id <> original.user_id
              AND association.user_id = rl.user_id
              AND association.device_hash = original.device_hash
            """
        )
    )

    _validate_normalized_ownership()

    # Replace the old single-column relationship with the composite
    # relationship that enforces tenant ownership at database level.
    op.drop_constraint(
        OLD_DEVICE_FK,
        "request_logs",
        type_="foreignkey",
    )
    op.create_foreign_key(
        NEW_DEVICE_FK,
        "request_logs",
        "device_fingerprints",
        ["user_id", "device_id"],
        ["user_id", "id"],
    )

    # Keep hash lookup efficient without requiring global uniqueness.
    op.create_index(
        HASH_INDEX,
        "device_fingerprints",
        ["device_hash"],
        unique=False,
    )


def downgrade() -> None:
    """Restore global fingerprint uniqueness only when it is safe."""
    _require_postgresql()
    _lock_device_tables()

    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # This check must happen before any DDL. Never merge independent
    # user associations or discard their trust/block state.
    shared_hash_groups = _count(
        """
        SELECT COUNT(*)
        FROM (
            SELECT device_hash
            FROM device_fingerprints
            GROUP BY device_hash
            HAVING COUNT(DISTINCT user_id) > 1
        ) AS shared_hashes
        """
    )

    if shared_hash_groups:
        raise RuntimeError(
            "Downgrade refused: multiple users have associations "
            "for one or more device hashes. Resolve these associations "
            "explicitly before attempting downgrade."
        )

    if _count(
        """
        SELECT COUNT(*)
        FROM request_logs AS rl
        JOIN device_fingerprints AS df
            ON df.id = rl.device_id
        WHERE rl.user_id <> df.user_id
        """
    ):
        raise RuntimeError(
            "Downgrade refused: request log ownership mismatches exist."
        )

    if _count(
        """
        SELECT COUNT(*)
        FROM request_logs AS rl
        LEFT JOIN device_fingerprints AS df
            ON df.id = rl.device_id
        WHERE rl.device_id IS NOT NULL
          AND df.id IS NULL
        """
    ):
        raise RuntimeError(
            "Downgrade refused: orphaned device references exist."
        )

    request_fks = inspector.get_foreign_keys("request_logs")
    composite_fks = [
        fk for fk in request_fks
        if fk.get("name") == NEW_DEVICE_FK
    ]
    if len(composite_fks) != 1:
        raise RuntimeError(
            "The expected composite device ownership foreign key "
            "was not found."
        )

    composite_fk = composite_fks[0]
    if (
        composite_fk.get("constrained_columns") != ["user_id", "device_id"]
        or composite_fk.get("referred_table") != "device_fingerprints"
        or composite_fk.get("referred_columns") != ["user_id", "id"]
    ):
        raise RuntimeError(
            "The composite device ownership foreign key "
            "has an unexpected definition."
        )

    unique_names = {
        constraint.get("name")
        for constraint in inspector.get_unique_constraints(
            "device_fingerprints"
        )
    }
    if not {
        USER_HASH_CONSTRAINT,
        USER_ID_CONSTRAINT,
    }.issubset(unique_names):
        raise RuntimeError(
            "Expected per-user unique constraints are missing."
        )

    indexes = {
        index["name"]: index
        for index in inspector.get_indexes("device_fingerprints")
    }
    hash_index = indexes.get(HASH_INDEX)
    if (
        hash_index is None
        or hash_index.get("unique") is not False
        or hash_index.get("column_names") != ["device_hash"]
    ):
        raise RuntimeError(
            "The expected non-unique device hash index was not found."
        )

    # Restore the original single-column foreign key.
    op.drop_constraint(
        NEW_DEVICE_FK,
        "request_logs",
        type_="foreignkey",
    )
    op.create_foreign_key(
        OLD_DEVICE_FK,
        "request_logs",
        "device_fingerprints",
        ["device_id"],
        ["id"],
    )

    # Restore the original globally unique hash index.
    op.drop_index(
        HASH_INDEX,
        table_name="device_fingerprints",
    )
    op.create_index(
        HASH_INDEX,
        "device_fingerprints",
        ["device_hash"],
        unique=True,
    )

    op.drop_constraint(
        USER_ID_CONSTRAINT,
        "device_fingerprints",
        type_="unique",
    )
    op.drop_constraint(
        USER_HASH_CONSTRAINT,
        "device_fingerprints",
        type_="unique",
    )
