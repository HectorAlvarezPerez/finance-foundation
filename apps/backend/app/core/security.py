import uuid

from itsdangerous import BadSignature, SignatureExpired, URLSafeSerializer, URLSafeTimedSerializer
from pwdlib import PasswordHash

from app.core.config import settings

SESSION_KEY = "user_id"
password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def _get_session_serializer() -> URLSafeSerializer:
    return URLSafeSerializer(settings.session_secret_key, salt="session")


def _get_auth_state_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.session_secret_key, salt="auth-state")


def create_session_token(user_id: uuid.UUID) -> str:
    serializer = _get_session_serializer()
    return serializer.dumps({SESSION_KEY: str(user_id)})


def read_session_token(token: str) -> uuid.UUID | None:
    serializer = _get_session_serializer()
    try:
        payload = serializer.loads(token)
    except BadSignature:
        return None

    user_id = payload.get(SESSION_KEY)
    if not isinstance(user_id, str):
        return None

    try:
        return uuid.UUID(user_id)
    except ValueError:
        return None


def create_auth_state_token(payload: dict[str, str]) -> str:
    serializer = _get_auth_state_serializer()
    return serializer.dumps(payload)


def read_auth_state_token(token: str) -> dict[str, str] | None:
    serializer = _get_auth_state_serializer()
    try:
        payload = serializer.loads(token, max_age=settings.auth_state_max_age)
    except (BadSignature, SignatureExpired):
        return None

    if not isinstance(payload, dict):
        return None

    if not all(isinstance(key, str) and isinstance(value, str) for key, value in payload.items()):
        return None

    return payload
