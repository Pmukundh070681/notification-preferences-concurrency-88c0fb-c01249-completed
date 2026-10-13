"""Authorization rules. Pure Python: no FastAPI, no database.

  user   read/update ONLY their own preferences
  admin  read/update any user's preferences inside their OWN tenant
  nobody ever touches another tenant's data, whatever the role
"""
from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from app.errors import Forbidden


class Role(str, Enum):
    USER = "user"
    ADMIN = "admin"


class Action(str, Enum):
    READ = "read"
    UPDATE = "update"


@dataclass(frozen=True)
class Principal:
    """Who is calling. Built ONLY from a verified token, never from request input."""
    user_id: UUID
    tenant_id: UUID
    role: Role


def authorize(principal: Principal, action: Action, *, target_user_id: UUID) -> None:
    """Role/ownership check using only the token and the requested user id."""
    if principal.role is Role.ADMIN:
        return  # admins may act on anyone; tenant scoping is enforced separately
    if target_user_id != principal.user_id:
        raise Forbidden(
            "You can only access your own notification preferences.",
            code="SELF_ONLY",
            hint="Use your own user id, or ask a tenant administrator.",
            details={"your_user_id": str(principal.user_id), "action": action.value},
        )


def tenant_denied() -> Forbidden:
    """Used when the record is not inside the caller's tenant. Identical for 'other tenant'
    and 'does not exist', so callers can't probe which ids exist elsewhere."""
    return Forbidden(
        "That user's preferences are not accessible within your tenant.",
        code="CROSS_TENANT_ACCESS",
        hint="Tenant boundaries apply to every role, including administrators.",
    )


def ensure_same_tenant(principal: Principal, resource_tenant_id: UUID) -> None:
    """Defense in depth: even if a query forgot its tenant filter, the row is rejected here."""
    if resource_tenant_id != principal.tenant_id:
        raise tenant_denied()
