from sqlalchemy.orm import declarative_base


Base = declarative_base()


# ---------------------------------------------------------
# Import ALL SQLAlchemy model modules.
#
# These imports register every model with SQLAlchemy's
# metadata so Alembic can detect them.
#
# IMPORTANT:
# Import MODULES only.
# Do NOT import model classes.
#
# Good:
#     import app.models.user
#
# Bad:
#     from app.models.user import User
#
# Importing classes can create circular imports because
# every model imports Base from this file.
#
# Keep this list synchronized with the actual SQLAlchemy
# model modules in app/models/.
# ---------------------------------------------------------

import app.models.user
import app.models.api_key
import app.models.request_log
import app.models.risk_score
import app.models.plan
import app.models.subscription
import app.models.device_fingerprint