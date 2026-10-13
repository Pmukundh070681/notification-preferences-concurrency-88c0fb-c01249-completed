from typing import Optional

from fastapi import Depends, Header
from jose import JWTError, jwt

from app.config import settings
from app.errors import AuthenticationRequired
from app.models.auth import TokenClaims
from app.services.authorization import Principal, Role


def decode_token(authorization: Optional[str] = Header(default=None)) -> TokenClaims:
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationRequired("Missing or invalid Authorization header.",
                                     hint="Send 'Authorization: Bearer <jwt>'.")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return TokenClaims(user_id=payload["user_id"], tenant_id=payload["tenant_id"], role=payload["role"])
    except (JWTError, KeyError, ValueError):
        raise AuthenticationRequired("Invalid or expired token.")


def get_principal(claims: TokenClaims = Depends(decode_token)) -> Principal:
    """Verified identity. Tenant and role come from the signed token only."""
    try:
        role = Role(claims.role)
    except ValueError:
        raise AuthenticationRequired("Token carries an unknown role.")
    return Principal(user_id=claims.user_id, tenant_id=claims.tenant_id, role=role)
