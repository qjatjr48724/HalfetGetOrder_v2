"""PBKDF2 + Fernet 암호화, 관리자 비밀번호 검증."""

from __future__ import annotations

import base64
import re
import secrets

import bcrypt
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

PBKDF2_ITERATIONS = 600_000
_SALT_LEN = 16


class PasswordValidationError(ValueError):
    pass


def password_policy_errors(password: str) -> list[str]:
    """규칙 미충족 항목 목록 (비어 있으면 통과)."""
    errors: list[str] = []
    if len(password) < 8:
        errors.append("8자 이상")
    if not re.search(r"[A-Za-z]", password):
        errors.append("영문 포함")
    if not re.search(r"\d", password):
        errors.append("숫자 포함")
    if not re.search(r"[^A-Za-z0-9]", password):
        errors.append("특수문자 포함")
    return errors


def validate_password(password: str) -> None:
    """8자 이상, 영문+숫자+특수문자."""
    issues = password_policy_errors(password)
    if not issues:
        return
    if len(issues) == 1:
        msg = {
            "8자 이상": "비밀번호는 8자 이상이어야 합니다.",
            "영문 포함": "비밀번호에 영문이 포함되어야 합니다.",
            "숫자 포함": "비밀번호에 숫자가 포함되어야 합니다.",
            "특수문자 포함": "비밀번호에 특수문자가 포함되어야 합니다.",
        }.get(issues[0], issues[0])
        raise PasswordValidationError(msg)
    raise PasswordValidationError(
        "비밀번호는 8자 이상이며, 영문·숫자·특수문자를 모두 포함해야 합니다."
    )


def check_admin_password_pair(password: str, confirm: str) -> None:
    """
    관리자 비밀번호 설정용 검증.
    - 비밀번호 / 확인 입력 여부
    - 두 값 일치
    - 영문+숫자+특수문자+8자 이상
    """
    pwd = password or ""
    conf = confirm or ""

    if not pwd.strip():
        raise PasswordValidationError("비밀번호를 입력해 주세요.")
    if not conf.strip():
        raise PasswordValidationError("비밀번호 확인을 입력해 주세요.")
    if pwd != conf:
        raise PasswordValidationError("비밀번호와 비밀번호 확인이 일치하지 않습니다.")

    issues = password_policy_errors(pwd)
    if issues:
        detail = " · ".join(issues)
        raise PasswordValidationError(
            f"비밀번호 규칙을 만족하지 않습니다. ({detail})"
        )


def hash_password(password: str) -> str:
    validate_password(password)
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except Exception:
        return False


def generate_master_key() -> bytes:
    return secrets.token_bytes(32)


def _derive_fernet(password: str, salt: bytes) -> Fernet:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))
    return Fernet(key)


def wrap_master_key(master_key: bytes, password: str, salt: bytes) -> str:
    f = _derive_fernet(password, salt)
    return f.encrypt(master_key).decode("ascii")


def unwrap_master_key(wrapped: str, password: str, salt: bytes) -> bytes:
    f = _derive_fernet(password, salt)
    try:
        return f.decrypt(wrapped.encode("ascii"))
    except InvalidToken as e:
        raise ValueError("비밀번호가 올바르지 않습니다.") from e


def encrypt_with_master(master_key: bytes, plaintext: str) -> str:
    key = base64.urlsafe_b64encode(master_key)
    return Fernet(key).encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_with_master(master_key: bytes, token: str) -> str:
    key = base64.urlsafe_b64encode(master_key)
    try:
        return Fernet(key).decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as e:
        raise ValueError("키 파일을 복호화할 수 없습니다.") from e


def new_wrap_salt() -> bytes:
    return secrets.token_bytes(_SALT_LEN)


def b64_encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def b64_decode(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"))
