import os
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2AuthorizationCodeBearer
from jwt import PyJWKClient

KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM")

oauth_2_scheme = OAuth2AuthorizationCodeBearer(
    tokenUrl=f"{KEYCLOAK_REALM}/protocol/openid-connect/token",
    authorizationUrl=f"{KEYCLOAK_REALM}/protocol/openid-connect/auth",
    refreshUrl=f"{KEYCLOAK_REALM}protocol/openid-connect/token",
)


def validate_token(token: str, return_encoded_token: bool = True):
    url = f"{KEYCLOAK_REALM}/protocol/openid-connect/certs"
    optional_custom_headers = {"User-agent": "custom-user-agent"}
    jwks_client = PyJWKClient(url, headers=optional_custom_headers)

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        data = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience="account",
            options={"verify_exp": True},
        )
        if return_encoded_token:
            return token
        return data
    except jwt.exceptions.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail="Not authenticated")


async def valid_access_token(access_token: Annotated[str, Depends(oauth_2_scheme)]):
    return validate_token(access_token, False)


async def valid_access_token_encoded(access_token: Annotated[str, Depends(oauth_2_scheme)]):
    return validate_token(access_token, True)


async def valid_admin_token(access_token: Annotated[str, Depends(oauth_2_scheme)]):
    """Validate the access token and ensure the user has the 'Platform.Admin' role."""
    data = validate_token(access_token, return_encoded_token=False)
    user_roles = data.get("userRoles", [])
    if "Platform.Admin" not in user_roles:
        raise HTTPException(status_code=403, detail="Admin access required")
    return data
