from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from jose import ExpiredSignatureError, JWTError, jwt
from jose.exceptions import JWTClaimsError

from src.config import api_settings, auth_settings
from src.schemas.auth import TokenPayload, TokenType

ACCESS_TTL = timedelta(minutes=auth_settings.access_token_ttl_minutes)
REFRESH_TTL = timedelta(days=auth_settings.refresh_token_ttl_days)


def _now_utc_ts() -> int:
    return int(datetime.now(UTC).timestamp())


def _exp_ts(ttl: timedelta) -> int:
    return int((datetime.now(UTC) + ttl).timestamp())


def _encode_jwt(claims: dict) -> str:
    return jwt.encode(
        claims,
        api_settings.secret_key.get_secret_value(),
        algorithm=auth_settings.encryption_algorithm,
    )


def create_access_token(
    subject: str,
    scope: str | None = None,
    extra_claims: dict | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    iat = _now_utc_ts()
    exp = _exp_ts(expires_delta or ACCESS_TTL)
    claims = {
        "sub": subject,
        "type": "access",
        "iat": iat,
        "exp": exp,
    }
    if scope:
        claims["scope"] = scope  # space-delimited
    if extra_claims:
        claims.update(extra_claims)
    return _encode_jwt(claims)


def create_refresh_token(
    subject: str,
    extra_claims: dict | None = None,
) -> str:
    iat = _now_utc_ts()
    exp = _exp_ts(REFRESH_TTL)
    claims = {
        "sub": subject,
        "type": "refresh",
        "iat": iat,
        "exp": exp,
    }
    if extra_claims:
        claims.update(extra_claims)
    return _encode_jwt(claims)


def decode_token(token: str, expected_type: TokenType = "access") -> TokenPayload:
    try:
        payload = jwt.decode(
            token,
            api_settings.secret_key.get_secret_value(),
            algorithms=[auth_settings.encryption_algorithm],
            options={"require_exp": True, "require_iat": True, "leeway": auth_settings.leeway},
        )
        if payload.get("type") != expected_type:
            raise JWTClaimsError(f"Invalid token type. Expected {expected_type}.")
        return TokenPayload(**payload)
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (JWTClaimsError, JWTError, ValueError, TypeError) as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
