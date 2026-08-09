"""Clerk session verification.

Clerk issues short-lived RS256 session JWTs. We verify them statelessly
against Clerk's published JWKS — no server-side session store, and the same
verification path works no matter which Clerk-issued client called us.

When an organization is active in the session, Clerk embeds `org_id`,
`org_slug`, and `org_role` (org:admin / org:member) as default claims. Email
is deliberately NOT read from the JWT (it's not a default claim and adding
it requires a custom JWT template) — instead we fetch it once from Clerk's
Backend API when we first see a given user, via `fetch_clerk_user`.
"""
from typing import Optional

import httpx
import jwt
from fastapi import HTTPException, status
from jwt import PyJWKClient

from app.config import get_settings


class ClerkClaims:
    def __init__(self, user_id: str, org_id: Optional[str], org_slug: Optional[str], org_role: Optional[str]):
        self.user_id = user_id
        self.org_id = org_id
        self.org_slug = org_slug
        self.org_role = org_role


_jwk_client: Optional[PyJWKClient] = None


def _get_jwk_client() -> PyJWKClient:
    global _jwk_client
    if _jwk_client is None:
        _jwk_client = PyJWKClient(get_settings().clerk_jwks_url)
    return _jwk_client


def verify_session_token(token: str) -> ClerkClaims:
    settings = get_settings()
    try:
        signing_key = _get_jwk_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=settings.clerk_issuer or None,
            options={"verify_aud": False},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid session token: {exc}")

    return ClerkClaims(
        user_id=claims["sub"],
        org_id=claims.get("org_id"),
        org_slug=claims.get("org_slug"),
        org_role=claims.get("org_role"),
    )


def fetch_clerk_user(clerk_user_id: str) -> dict:
    """Called once, the first time we see a given clerk_user_id, to populate
    our local User mirror. Uses Clerk's Backend API with the secret key."""
    settings = get_settings()
    response = httpx.get(
        f"https://api.clerk.com/v1/users/{clerk_user_id}",
        headers={"Authorization": f"Bearer {settings.clerk_secret_key}"},
        timeout=5.0,
    )
    response.raise_for_status()
    data = response.json()
    primary_email = next(
        (
            e["email_address"]
            for e in data.get("email_addresses", [])
            if e["id"] == data.get("primary_email_address_id")
        ),
        None,
    )
    full_name = " ".join(filter(None, [data.get("first_name"), data.get("last_name")])) or None
    return {"email": primary_email or f"{clerk_user_id}@unknown.local", "full_name": full_name}
