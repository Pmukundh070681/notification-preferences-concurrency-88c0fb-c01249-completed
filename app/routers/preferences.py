import re
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response

from app.errors import BadRequest, VersionRequired
from app.middleware.auth import get_principal
from app.models.preferences import PreferencesResponse, PreferencesUpdateRequest
from app.services.authorization import Principal
from app.services.preferences_service import apply_preference_updates, fetch_user_preferences

router = APIRouter()

_ETAG = re.compile(r'^(?:W/)?"?(\d+)"?$')


def _parse_if_match(value: Optional[str]) -> int:
    if value is None:
        raise VersionRequired(
            "If-Match header is required for updates.",
            hint="GET the preferences first, then send the returned ETag as If-Match.",
        )
    m = _ETAG.match(value.strip())
    if not m:
        raise BadRequest('If-Match must be the ETag returned by GET, e.g. "3".', code="INVALID_IF_MATCH")
    return int(m.group(1))


@router.get("/users/{user_id}/preferences", response_model=PreferencesResponse)
def get_preferences(user_id: UUID, response: Response, principal: Principal = Depends(get_principal)):
    prefs = fetch_user_preferences(principal, user_id)
    response.headers["ETag"] = f'"{prefs.version}"'
    return PreferencesResponse(**prefs.model_dump())


@router.put("/users/{user_id}/preferences", response_model=PreferencesResponse)
def update_preferences(user_id: UUID, body: PreferencesUpdateRequest, response: Response,
                       if_match: Optional[str] = Header(default=None),
                       principal: Principal = Depends(get_principal)):
    expected = _parse_if_match(if_match)
    updated = apply_preference_updates(principal, user_id, body, expected)
    response.headers["ETag"] = f'"{updated.version}"'
    return PreferencesResponse(**updated.model_dump())
