import jwt
from jwt import PyJWKClient


def token_to_user_generic(token, token_issuers, token_decoded_to_user_fun):
    # Get JWKs URL from token
    jwks_url, decoded = get_jwks_url_from_token(token)

    # Verify token using the JWKs URL
    jwks_client = PyJWKClient(jwks_url)
    signing_key = jwks_client.get_signing_key_from_jwt(token)
    audience = decoded["aud"]

    jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=audience,
        issuer=token_issuers,
        options={"verify_signature": True},
    )

    return token_decoded_to_user_fun(decoded)


def get_jwks_url_from_token(token):
    # Decode without verification to get the issuer
    decoded = jwt.decode(token, options={"verify_signature": False})

    issuer = decoded.get("iss")
    if not issuer:
        raise ValueError("Token does not contain 'iss' claim")

    # Remove trailing slash if present
    issuer = issuer.rstrip("/")
    return f"{issuer}/.well-known/jwks.json", decoded
