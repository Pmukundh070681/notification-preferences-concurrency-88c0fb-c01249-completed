"""Data access. Every query is scoped by tenant_id, so isolation never depends on callers."""
from typing import Optional
from uuid import UUID

from app.database import get_db
from app.models.preferences import NotificationPreferences

_COLUMNS = "user_id, tenant_id, email_enabled, sms_enabled, push_enabled, frequency, version"
_UPDATABLE = frozenset({"email_enabled", "sms_enabled", "push_enabled", "frequency"})


def get_preferences_by_user(tenant_id: UUID, user_id: UUID) -> Optional[NotificationPreferences]:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_COLUMNS} FROM notification_preferences WHERE user_id = %s AND tenant_id = %s",
                (str(user_id), str(tenant_id)),
            )
            row = cur.fetchone()
            return NotificationPreferences(**row) if row else None


def update_preferences(tenant_id: UUID, user_id: UUID, expected_version: int,
                       updates: dict) -> Optional[NotificationPreferences]:
    """Compare-and-set in ONE statement. Returns None if no row matched
    (wrong tenant, no such user, or the version moved on).

    Two simultaneous writers holding the same version: PostgreSQL serialises the row update;
    the second re-evaluates `version = N` against the new row, matches nothing, and gets None.
    """
    unknown = set(updates) - _UPDATABLE
    if unknown:
        raise ValueError(f"Non-updatable fields: {sorted(unknown)}")

    set_clauses = ", ".join(f"{key} = %s" for key in updates)
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE notification_preferences "
                f"SET {set_clauses}, version = version + 1, updated_at = NOW() "
                f"WHERE user_id = %s AND tenant_id = %s AND version = %s "
                f"RETURNING {_COLUMNS}",
                list(updates.values()) + [str(user_id), str(tenant_id), expected_version],
            )
            row = cur.fetchone()
            return NotificationPreferences(**row) if row else None
