"""%APPDATA% 설정·관리자·API 키 저장."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from . import crypto

APP_DIR_NAME = "HalfetGetOrder"
OUTPUT_FOLDER_NAME = "하프전자 주문수집기"


@dataclass
class ApiKeys:
    cp_accesskey: str
    cp_secretkey: str
    partner_key: str
    godo_key: str

    def to_dict(self) -> dict[str, str]:
        return {
            "cp_accesskey": self.cp_accesskey,
            "cp_secretkey": self.cp_secretkey,
            "partner_key": self.partner_key,
            "godo_key": self.godo_key,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ApiKeys:
        return cls(
            cp_accesskey=(data.get("cp_accesskey") or "").strip(),
            cp_secretkey=(data.get("cp_secretkey") or "").strip(),
            partner_key=(data.get("partner_key") or "").strip(),
            godo_key=(data.get("godo_key") or "").strip(),
        )

    def is_complete(self) -> bool:
        return all(
            [
                self.cp_accesskey,
                self.cp_secretkey,
                self.partner_key,
                self.godo_key,
            ]
        )


class AppStore:
    def __init__(self, base_dir: Path | None = None):
        if base_dir is None:
            base_dir = Path(os.environ.get("APPDATA", Path.home())) / APP_DIR_NAME
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._setup_path = self.base_dir / "setup.json"
        self._admin_path = self.base_dir / "admin.json"
        self._keys_path = self.base_dir / "keys.enc"
        self._last_run_path = self.base_dir / "godo_last_run.json"

    @property
    def last_run_path(self) -> Path:
        return self._last_run_path

    def load_setup(self) -> dict:
        if not self._setup_path.exists():
            return self._default_setup()
        try:
            data = json.loads(self._setup_path.read_text(encoding="utf-8"))
            merged = self._default_setup()
            merged.update(data)
            return merged
        except Exception:
            return self._default_setup()

    def save_setup(self, data: dict) -> None:
        merged = self._default_setup()
        merged.update(data)
        self._setup_path.write_text(
            json.dumps(merged, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _default_setup(self) -> dict:
        desktop = Path.home() / "Desktop"
        return {
            "install_done": False,
            "output_parent": str(desktop),
            "venv_done": False,
            "deps_done": False,
        }

    @staticmethod
    def format_output_path(parent: str | Path) -> str:
        """상위 경로 → 화면 표시용 전체 경로 (…/하프전자 주문수집기)."""
        p = Path(parent)
        if p.name == OUTPUT_FOLDER_NAME:
            return str(p)
        return str(p / OUTPUT_FOLDER_NAME)

    @staticmethod
    def parse_output_parent(display_or_parent: str) -> Path:
        """입력/표시 경로에서 상위 폴더만 추출."""
        p = Path((display_or_parent or "").strip())
        if not str(p):
            raise ValueError("폴더 경로를 입력하거나 선택해 주세요.")
        if p.name == OUTPUT_FOLDER_NAME:
            return p.parent
        return p

    def get_output_dir(self) -> Path:
        setup = self.load_setup()
        parent = self.parse_output_parent(
            setup.get("output_parent") or str(Path.home() / "Desktop")
        )
        out = parent / OUTPUT_FOLDER_NAME
        out.mkdir(parents=True, exist_ok=True)
        return out

    def is_password_configured(self) -> bool:
        return self._admin_path.exists()

    def is_keys_configured(self) -> bool:
        return self._keys_path.exists()

    def setup_admin_password(self, password: str) -> None:
        """최초 관리자 비밀번호 + 마스터 키 생성."""
        crypto.validate_password(password)
        master = crypto.generate_master_key()
        salt = crypto.new_wrap_salt()
        wrapped = crypto.wrap_master_key(master, password, salt)
        admin = {
            "password_hash": crypto.hash_password(password),
            "wrapped_key": wrapped,
            "wrap_salt": crypto.b64_encode(salt),
        }
        self._admin_path.write_text(
            json.dumps(admin, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def change_admin_password(self, old_password: str, new_password: str) -> None:
        master = self._unwrap_with_password(old_password)
        crypto.validate_password(new_password)
        salt = crypto.new_wrap_salt()
        wrapped = crypto.wrap_master_key(master, new_password, salt)
        admin = self._load_admin()
        admin["password_hash"] = crypto.hash_password(new_password)
        admin["wrapped_key"] = wrapped
        admin["wrap_salt"] = crypto.b64_encode(salt)
        self._admin_path.write_text(
            json.dumps(admin, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def reset_admin_and_keys(self) -> None:
        """비밀번호 분실 재설정: admin + keys 삭제."""
        for p in (self._admin_path, self._keys_path):
            if p.exists():
                p.unlink()

    def verify_admin_password(self, password: str) -> bool:
        if not self._admin_path.exists():
            return False
        admin = self._load_admin()
        return crypto.verify_password(password, admin.get("password_hash", ""))

    def save_api_keys(self, keys: ApiKeys, password: str) -> None:
        if not keys.is_complete():
            raise ValueError("API 키 4개를 모두 입력해 주세요.")
        master = self._unwrap_with_password(password)
        token = crypto.encrypt_with_master(
            master, json.dumps(keys.to_dict(), ensure_ascii=False)
        )
        self._keys_path.write_text(token, encoding="utf-8")

    def load_api_keys(self, password: str) -> ApiKeys:
        if not self._keys_path.exists():
            raise FileNotFoundError("저장된 API 키가 없습니다. 설치 탭에서 키를 입력해 주세요.")
        master = self._unwrap_with_password(password)
        raw = self._keys_path.read_text(encoding="utf-8")
        plain = crypto.decrypt_with_master(master, raw)
        return ApiKeys.from_dict(json.loads(plain))

    def _load_admin(self) -> dict:
        return json.loads(self._admin_path.read_text(encoding="utf-8"))

    def _unwrap_with_password(self, password: str) -> bytes:
        if not self._admin_path.exists():
            raise FileNotFoundError("관리자 비밀번호가 설정되지 않았습니다.")
        admin = self._load_admin()
        if not crypto.verify_password(password, admin.get("password_hash", "")):
            raise ValueError("비밀번호가 올바르지 않습니다.")
        salt = crypto.b64_decode(admin["wrap_salt"])
        return crypto.unwrap_master_key(admin["wrapped_key"], password, salt)
