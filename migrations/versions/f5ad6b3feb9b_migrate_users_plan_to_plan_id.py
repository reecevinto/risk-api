from alembic import op
import sqlalchemy as sa

import sqlalchemy as sa
from sqlalchemy import text

revision = "f5ad6b3feb9b"
down_revision = "045cb461095d"
branch_labels = None
depends_on = None


def upgrade():

    conn = op.get_bind()

    # 1. Add column safely (no duplicates)
    conn.execute(text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='users' AND column_name='plan_id'
            ) THEN
                ALTER TABLE users ADD COLUMN plan_id INTEGER;
            END IF;
        END $$;
    """))

    # 2. CHECK if old column exists BEFORE using it
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='users' AND column_name='plan'
        );
    """))

    has_old_plan = result.scalar()

    # 3. ONLY run backfill if column exists
    if has_old_plan:
        conn.execute(text("""
            UPDATE users
            SET plan_id = (
                SELECT id FROM plans WHERE plans.name = users.plan
            );
        """))

        conn.execute(text("""
            ALTER TABLE users DROP COLUMN plan;
        """))

    # 4. Add FK safely
    conn.execute(text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name='fk_users_plan_id'
            ) THEN
                ALTER TABLE users
                ADD CONSTRAINT fk_users_plan_id
                FOREIGN KEY (plan_id) REFERENCES plans(id);
            END IF;
        END $$;
    """))


def downgrade():

    conn = op.get_bind()

    conn.execute(text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='users' AND column_name='plan'
            ) THEN
                ALTER TABLE users ADD COLUMN plan TEXT;
            END IF;
        END $$;
    """))

    conn.execute(text("""
        UPDATE users
        SET plan = (
            SELECT name FROM plans WHERE plans.id = users.plan_id
        );
    """))

    conn.execute(text("""
        ALTER TABLE users DROP CONSTRAINT IF EXISTS fk_users_plan_id;
    """))

    conn.execute(text("""
        ALTER TABLE users DROP COLUMN IF EXISTS plan_id;
    """))