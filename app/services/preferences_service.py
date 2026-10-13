"""Orchestration: authorize -> tenant-scoped data access -> concurrency outcome."""
from uuid import UUID

from app.errors import BadRequest, VersionConflict
from app.models.preferences import NotificationPreferences, PreferencesUpdateRequest
from app.repositories import preferences_repository as repo
from app.services.authorization import Action, Principal, authorize, ensure_same_tenant, tenant_denied


def fetch_user_preferences(principal: Principal, user_id: UUID) -> NotificationPreferences:
    authorize(principal, Action.READ, target_user_id=user_id)
    prefs = repo.get_preferences_by_user(principal.tenant_id, user_id)
    if prefs is None:
        raise tenant_denied()
    ensure_same_tenant(principal, prefs.tenant_id)
    return prefs


def apply_preference_updates(principal: Principal, user_id: UUID, request: PreferencesUpdateRequest,
                             expected_version: int) -> NotificationPreferences:
    authorize(principal, Action.UPDATE, target_user_id=user_id)
    updates = request.model_dump(exclude_none=True)
    if not updates:
        raise BadRequest("Provide at least one field to update.", code="EMPTY_UPDATE")

    updated = repo.update_preferences(principal.tenant_id, user_id, expected_version, updates)
    if updated is not None:
        ensure_same_tenant(principal, updated.tenant_id)
        return updated

    # 0 rows matched: not in this tenant at all, or someone else changed it first.
    current = repo.get_preferences_by_user(principal.tenant_id, user_id)
    if current is None:
        raise tenant_denied()
    raise VersionConflict(
        "These preferences were changed by someone else after you read them. Nothing was changed.",
        hint="GET the latest preferences, reapply your change, and retry with the new ETag.",
        details={"your_version": expected_version, "current_version": current.version},
    )
