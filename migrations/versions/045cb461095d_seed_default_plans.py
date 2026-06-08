from alembic import op

# revision identifiers
revision = "045cb461095d"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO plans (name, request_limit)
        VALUES 
        ('free', 100),
        ('pro', 1000),
        ('enterprise', 10000)
        ON CONFLICT (name) DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM plans 
        WHERE name IN ('free', 'pro', 'enterprise');
    """)