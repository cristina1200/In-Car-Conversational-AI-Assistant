import base64
import hashlib
import hmac
import re
import secrets
import sqlite3
import uuid
from datetime import datetime, timezone

from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserResponse


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class DuplicateEmailError(ValueError):
    pass


class UserNotFoundError(LookupError):
    pass


class InvalidCredentialsError(ValueError):
    pass


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    password_bytes = password.encode("utf-8")
    digest = hashlib.scrypt(
        password_bytes,
        salt=salt,
        n=2**14,
        r=8,
        p=1,
    )

    encoded_salt = base64.urlsafe_b64encode(salt).decode("ascii")
    encoded_digest = base64.urlsafe_b64encode(digest).decode("ascii")

    return f"scrypt$16384$8$1${encoded_salt}${encoded_digest}"


def verify_password(password: str, encoded_hash: str | None) -> bool:
    if not encoded_hash:
        return False

    try:
        algorithm, n, r, p, encoded_salt, encoded_digest = (
            encoded_hash.split("$", 5)
        )
        if algorithm != "scrypt":
            return False

        salt = base64.urlsafe_b64decode(encoded_salt.encode("ascii"))
        expected_digest = base64.urlsafe_b64decode(
            encoded_digest.encode("ascii")
        )
        actual_digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected_digest),
        )
    except (ValueError, TypeError, UnicodeDecodeError):
        return False

    return hmac.compare_digest(actual_digest, expected_digest)


class UserService:
    def __init__(self, repository: UserRepository | None = None):
        self.repository = repository or UserRepository()

    def create_user(self, user: UserCreate) -> UserResponse:
        name = user.name.strip()
        email = user.email.strip().lower()
        password = user.password

        if not name:
            raise ValueError("Name is required")
        if not EMAIL_PATTERN.fullmatch(email):
            raise ValueError("A valid email is required")
        if not password:
            raise ValueError("Password is required")
        if self.repository.email_exists(email):
            raise DuplicateEmailError("Email is already registered")

        try:
            row = self.repository.create(
                user_id=str(uuid.uuid4()),
                name=name,
                email=email,
                password_hash=hash_password(password),
                created_at=datetime.now(timezone.utc).isoformat(),
            )
        except sqlite3.IntegrityError as error:
            raise DuplicateEmailError("Email is already registered") from error

        return self._to_response(row)

    def get_user(self, user_id: str) -> UserResponse:
        row = self.repository.get_by_id(user_id)

        if row is None:
            raise UserNotFoundError("User not found")

        return self._to_response(row)

    def login(self, email: str, password: str) -> UserResponse:
        row = self.repository.get_by_email(email.strip().lower())

        if row is None or not verify_password(
            password,
            row["password_hash"],
        ):
            raise InvalidCredentialsError("Invalid email or password")

        return self._to_response(row)

    def delete_user(self, user_id: str) -> None:
        if not self.repository.delete(user_id):
            raise UserNotFoundError("User not found")

    @staticmethod
    def _to_response(row: sqlite3.Row) -> UserResponse:
        return UserResponse(
            user_id=row["user_id"],
            name=row["name"],
            email=row["email"],
            voice_enrolled=bool(row["voice_enrolled"]),
            created_at=row["created_at"],
        )
