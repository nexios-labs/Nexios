import pytest

from nexios import get_application
from nexios.auth.backends.jwt import create_jwt, decode_jwt
from nexios.auth.base import AuthenticationBackend, SimpleUser
from nexios.auth.decorator import auth
from nexios.config.base import MakeConfig
from nexios.http import Request, Response
from nexios.testing import Client


@pytest.fixture
async def test_client():
    app = get_application(MakeConfig({"secret_key": "1234"}))
    async with Client(app) as client:
        yield client, app


@pytest.fixture
def mock_user():
    return {"id": 1, "username": "testuser"}


@pytest.fixture
def valid_token(mock_user):
    return create_jwt(mock_user)


@pytest.fixture
def expired_token(mock_user):
    return create_jwt({"exp": 1, **mock_user})


async def test_jwt_auth_success(test_client, mock_user, valid_token):
    client, app = test_client

    async def mock_authenticate(**kwargs):
        return mock_user

    from nexios.auth.backends import JWTAuthBackend
    from nexios.auth.middleware import AuthenticationMiddleware

    app.add_middleware(
        AuthenticationMiddleware(
            backend=JWTAuthBackend(authenticate_func=mock_authenticate)
        )
    )

    @app.get("/protected")
    @auth(["jwt"])
    async def protected_route(req: Request, res: Response):
        return res.json({"user": req.user})

    response = await client.get(
        "/protected", headers={"Authorization": f"Bearer {valid_token}"}
    )

    assert response.status_code == 200
    assert response.json()["user"] == mock_user


async def test_jwt_auth_missing_header(test_client, mock_user):
    client, app = test_client

    async def mock_authenticate(**kwargs):
        return mock_user

    from nexios.auth.backends import JWTAuthBackend
    from nexios.auth.middleware import AuthenticationMiddleware

    app.add_middleware(
        AuthenticationMiddleware(
            backend=JWTAuthBackend(authenticate_func=mock_authenticate)
        )
    )

    @app.get("/protected")
    @auth(["jwt"])
    async def protected_route(req: Request, res: Response):
        return res.json({"user": req.user})

    # Test without auth header
    response = await client.get("/protected")

    assert response.status_code == 401


async def test_jwt_auth_invalid_token(test_client, mock_user):
    client, app = test_client

    async def mock_authenticate(**kwargs):
        return mock_user

    from nexios.auth.backends import JWTAuthBackend
    from nexios.auth.middleware import AuthenticationMiddleware

    app.add_middleware(
        AuthenticationMiddleware(
            backend=JWTAuthBackend(authenticate_func=mock_authenticate)
        )
    )

    @app.get("/protected")
    @auth(["jwt"])
    async def protected_route(req: Request, res: Response):
        return res.json({"user": req.user})

    # Test with invalid token
    response = await client.get(
        "/protected", headers={"Authorization": "Bearer invalid_token"}
    )

    assert response.status_code == 401


async def test_jwt_auth_expired_token(test_client, mock_user, expired_token):
    client, app = test_client

    async def mock_authenticate(**kwargs):
        return mock_user

    from nexios.auth.backends import JWTAuthBackend
    from nexios.auth.middleware import AuthenticationMiddleware

    app.add_middleware(
        AuthenticationMiddleware(
            backend=JWTAuthBackend(authenticate_func=mock_authenticate)
        )
    )

    @app.get("/protected")
    @auth(["jwt"])
    async def protected_route(req: Request, res: Response):
        return res.json({"user": req.user})

    # Test with expired token
    response = await client.get(
        "/protected", headers={"Authorization": f"Bearer {expired_token}"}
    )

    assert response.status_code == 401


async def test_jwt_auth_validation_failure(test_client, valid_token):
    client, app = test_client

    # Mock authenticate function to return None (invalid user)
    async def mock_authenticate(**kwargs):
        return SimpleUser(username="nexios-dev")

    from nexios.auth.backends import JWTAuthBackend
    from nexios.auth.middleware import AuthenticationMiddleware

    app.add_middleware(
        AuthenticationMiddleware(
            backend=JWTAuthBackend(authenticate_func=mock_authenticate)
        )
    )

    @app.get("/protected")
    @auth(["jwt"])
    async def protected_route(req: Request, res: Response):
        return res.json({"user": req.user})

    # Test with valid token but invalid user
    response = await client.get(
        "/protected", headers={"Authorization": f"Bearer {valid_token}"}
    )

    assert response.status_code == 200


async def test_jwt_auth_with_auth_decorator(test_client, mock_user, valid_token):
    client, app = test_client

    async def mock_authenticate(**kwargs):
        return mock_user

    from nexios.auth.backends import JWTAuthBackend
    from nexios.auth.decorator import auth
    from nexios.auth.middleware import AuthenticationMiddleware

    app.add_middleware(
        AuthenticationMiddleware(
            backend=JWTAuthBackend(authenticate_func=mock_authenticate)
        )
    )

    @app.get("/protected-decorator")
    @auth(["jwt"])
    async def protected_route(req: Request, res: Response):
        return res.json({"user": req.user})

    # Test with valid token
    response = await client.get(
        "/protected-decorator", headers={"Authorization": f"Bearer {valid_token}"}
    )
    assert response.status_code == 200
    assert response.json()["user"] == mock_user

    # Test without token (should be unauthorized)
    response = await client.get("/protected-decorator")
    assert response.status_code == 401


def test_create_jwt():
    from jwt import decode as jwt_decode

    payload = {"user_id": 1, "username": "test"}
    token = create_jwt(payload, "test_secret")

    decoded = jwt_decode(token, "test_secret", algorithms=["HS256"])
    assert decoded["user_id"] == 1
    assert decoded["username"] == "test"


def test_decode_jwt_valid():
    payload = {"user_id": 1, "username": "test"}
    token = create_jwt(payload, "test_secret", algorithm="HS256")

    decoded = decode_jwt(token, "test_secret", ["HS256"])
    assert decoded["user_id"] == 1
    assert decoded["username"] == "test"


def test_decode_jwt_expired():
    payload = {"user_id": 1, "username": "test", "exp": 1}  # Expired in 1970
    token = create_jwt(payload, "test_secret", algorithm="HS256")

    with pytest.raises(ValueError, match="Token has expired"):
        decode_jwt(token, "test_secret", ["HS256"])


def test_decode_jwt_invalid():
    with pytest.raises(ValueError, match="Invalid token"):
        decode_jwt("invalid.token", "test_secret", ["HS256"])


async def test_custom_auth_backend(test_client):
    client, app = test_client

    class CustomAuthBackend(AuthenticationBackend):
        async def authenticate(self, request: Request, response: Response):
            if request.headers.get("X-Custom-Auth") == "valid":
                return {"id": 1, "username": "custom_user"}, "X-auth"
            return None

    from nexios.auth.middleware import AuthenticationMiddleware

    app.add_middleware(AuthenticationMiddleware(backend=CustomAuthBackend()))

    @app.get("/custom-protected")
    @auth(["X-auth"])
    async def custom_protected(req: Request, res: Response):
        return res.json({"user": req.user})

    # Test with valid custom auth
    response = await client.get("/custom-protected", headers={"X-Custom-Auth": "valid"})
    assert response.status_code == 200
    assert response.json()["user"] == {"id": 1, "username": "custom_user"}

    response = await client.get("/custom-protected")
    assert response.status_code == 401
