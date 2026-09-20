"""Unit and integration tests for NETRA Authentication & Authorization (auth.py)."""

import json
import time
import pytest

from netra.auth import (
    AUTH_SECRET,
    ROLE_ADMIN,
    ROLE_OPERATOR,
    ROLE_VIEWER,
    PERM_ADMIN,
    PERM_APPROVE,
    PERM_MUTATE,
    PERM_VIEW,
    DEMO_ACCOUNTS,
    get_caller_identity,
    has_permission,
    hash_api_key,
    mint_session_token,
    verify_session_token,
)


def test_mint_and_verify_valid_token():
    token = mint_session_token("user@example.com", role=ROLE_OPERATOR, name="Test User")
    payload = verify_session_token(token)

    assert payload is not None
    assert payload["sub"] == "user@example.com"
    assert payload["role"] == ROLE_OPERATOR
    assert payload["name"] == "Test User"
    assert payload["iss"] == "netra-auth-v1"
    assert payload["exp"] > int(time.time())


def test_verify_expired_token():
    token = mint_session_token("user@example.com", role=ROLE_VIEWER, ttl_seconds=-10)
    payload = verify_session_token(token)
    assert payload is None


def test_verify_tampered_token():
    token = mint_session_token("user@example.com", role=ROLE_VIEWER)
    parts = token.split(".")
    # Tamper payload part
    tampered_token = f"{parts[0]}.{parts[1]}xyz.{parts[2]}"
    assert verify_session_token(tampered_token) is None

    # Tamper with different secret
    assert verify_session_token(token, secret=b"wrong-secret-key-000") is None


def test_role_permissions():
    assert has_permission(ROLE_VIEWER, PERM_VIEW) is True
    assert has_permission(ROLE_VIEWER, PERM_APPROVE) is False
    assert has_permission(ROLE_VIEWER, PERM_ADMIN) is False

    assert has_permission(ROLE_OPERATOR, PERM_VIEW) is True
    assert has_permission(ROLE_OPERATOR, PERM_APPROVE) is True
    assert has_permission(ROLE_OPERATOR, PERM_MUTATE) is True
    assert has_permission(ROLE_OPERATOR, PERM_ADMIN) is False

    assert has_permission(ROLE_ADMIN, PERM_VIEW) is True
    assert has_permission(ROLE_ADMIN, PERM_APPROVE) is True
    assert has_permission(ROLE_ADMIN, PERM_MUTATE) is True
    assert has_permission(ROLE_ADMIN, PERM_ADMIN) is True


def test_get_caller_identity_bearer_token():
    token = mint_session_token("operator@we-make-devs.org", role=ROLE_OPERATOR)
    event = {
        "headers": {
            "Authorization": f"Bearer {token}",
        }
    }
    is_auth, identity = get_caller_identity(event, allow_demo_fallback=False)
    assert is_auth is True
    assert identity["user_id"] == "operator@we-make-devs.org"
    assert identity["role"] == ROLE_OPERATOR
    assert identity["auth_type"] == "bearer"


def test_get_caller_identity_api_key():
    event = {
        "headers": {
            "x-api-key": "netra_live_admin_key_2026",
        }
    }
    is_auth, identity = get_caller_identity(event, allow_demo_fallback=False)
    assert is_auth is True
    assert identity["user_id"] == "admin@we-make-devs.org"
    assert identity["role"] == ROLE_ADMIN
    assert identity["auth_type"] == "api_key"


def test_get_caller_identity_anonymous():
    event = {"headers": {}}
    is_auth, identity = get_caller_identity(event, allow_demo_fallback=False)
    assert is_auth is False
    assert identity["role"] == ROLE_VIEWER
    assert identity["auth_type"] == "none"


def test_hash_api_key():
    digest1 = hash_api_key("secret-key-1")
    digest2 = hash_api_key("secret-key-1")
    digest3 = hash_api_key("secret-key-2")

    assert digest1 == digest2
    assert digest1 != digest3
    assert len(digest1) == 64


def test_api_auth_login_and_me_flow():
    from netra.api import lambda_handler

    # 1. Login as Operator
    login_event = {
        "rawPath": "/api/auth/login",
        "requestContext": {"http": {"method": "POST"}},
        "body": json.dumps({"email": "operator@we-make-devs.org"}),
    }
    resp = lambda_handler(login_event, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["ok"] is True
    assert "token" in body
    token = body["token"]
    assert body["user"]["role"] == ROLE_OPERATOR

    # 2. Call /api/auth/me with Bearer token
    me_event = {
        "rawPath": "/api/auth/me",
        "requestContext": {"http": {"method": "GET"}},
        "headers": {"Authorization": f"Bearer {token}"},
    }
    resp_me = lambda_handler(me_event, None)
    assert resp_me["statusCode"] == 200
    body_me = json.loads(resp_me["body"])
    assert body_me["authenticated"] is True
    assert body_me["user"]["role"] == ROLE_OPERATOR


def test_api_auth_keys_admin_only():
    from netra.api import lambda_handler

    # 1. Viewer trying to generate API key -> 403
    viewer_token = mint_session_token("viewer@test.com", role=ROLE_VIEWER)
    fail_event = {
        "rawPath": "/api/auth/keys",
        "requestContext": {"http": {"method": "POST"}},
        "headers": {"Authorization": f"Bearer {viewer_token}"},
    }
    resp_fail = lambda_handler(fail_event, None)
    assert resp_fail["statusCode"] == 403

    # 2. Admin generating API key -> 200
    admin_token = mint_session_token("admin@we-make-devs.org", role=ROLE_ADMIN)
    succ_event = {
        "rawPath": "/api/auth/keys",
        "requestContext": {"http": {"method": "POST"}},
        "headers": {"Authorization": f"Bearer {admin_token}"},
    }
    resp_succ = lambda_handler(succ_event, None)
    assert resp_succ["statusCode"] == 200
    body = json.loads(resp_succ["body"])
    assert body["ok"] is True
    assert body["api_key"].startswith("netra_live_")
    assert "key_hash" in body

