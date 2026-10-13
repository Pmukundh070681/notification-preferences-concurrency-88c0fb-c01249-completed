"""Pure unit tests for the rules: no DB, no HTTP."""
import uuid

import pytest

from app.errors import Forbidden
from app.services.authorization import Action, Principal, Role, authorize, ensure_same_tenant

T1, T2, ME, OTHER = (uuid.uuid4() for _ in range(4))


def p(role):
    return Principal(ME, T1, role)


def test_user_can_access_self():
    authorize(p(Role.USER), Action.READ, target_user_id=ME)
    authorize(p(Role.USER), Action.UPDATE, target_user_id=ME)


@pytest.mark.parametrize("action", list(Action))
def test_user_cannot_access_others(action):
    with pytest.raises(Forbidden) as e:
        authorize(p(Role.USER), action, target_user_id=OTHER)
    assert e.value.code == "SELF_ONLY"


def test_admin_can_act_on_others():
    for a in Action:
        authorize(p(Role.ADMIN), a, target_user_id=OTHER)


@pytest.mark.parametrize("role", list(Role))
def test_no_role_crosses_tenants(role):
    with pytest.raises(Forbidden) as e:
        ensure_same_tenant(p(role), T2)
    assert e.value.code == "CROSS_TENANT_ACCESS"
    ensure_same_tenant(p(role), T1)
