
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:

    def load_dotenv(*args, **kwargs):
        return False


OUTPUT_FOLDER_NAME = "하프전자 주문수집기"

PARTNER_KEY = ""
GODO_KEY = ""
CP_ACCESS = ""
CP_SECRET = ""
DATA_DIR = ""


def _project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parents[2]


def _load_env():
    root = _project_root()
    env = root / ".env"
    if env.exists():
        load_dotenv(env)
    else:
        load_dotenv()


_load_env()

# 개발용 폴백 (.env / keys.py) — GUI 설치 완료 후에는 apply_runtime_keys 사용
PARTNER_KEY = os.getenv("PARTNER_KEY", "")
GODO_KEY = os.getenv("GODO_KEY", "")
CP_ACCESS = os.getenv("CP_ACCESSKEY", "")
CP_SECRET = os.getenv("CP_SECRETKEY", "")

try:
    if not (PARTNER_KEY and GODO_KEY and CP_ACCESS and CP_SECRET):
        from .keys import partner_key as _pk, godo_key as _gk, cp_accesskey as _ak, cp_secretkey as _sk

        PARTNER_KEY = PARTNER_KEY or _pk
        GODO_KEY = GODO_KEY or _gk
        CP_ACCESS = CP_ACCESS or _ak
        CP_SECRET = CP_SECRET or _sk
except Exception:
    pass


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def resource_path(rel: str) -> str:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS) / "halfetgetorder" / "resources"
    else:
        base = Path(__file__).resolve().parent / "resources"
    return str(base / rel)


def project_root() -> Path:
    return _project_root()


def apply_runtime_keys(
    *,
    cp_access: str,
    cp_secret: str,
    partner_key: str,
    godo_key: str,
) -> None:
    """API 호출 직전에 config·godo·coupang 모듈에 키를 주입."""
    global PARTNER_KEY, GODO_KEY, CP_ACCESS, CP_SECRET
    PARTNER_KEY = partner_key
    GODO_KEY = godo_key
    CP_ACCESS = cp_access
    CP_SECRET = cp_secret


def set_data_dir(path: str | Path) -> None:
    global DATA_DIR
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    DATA_DIR = str(p)


def init_data_dir_from_store(store) -> str:
    """AppStore 기준 출력 폴더를 DATA_DIR에 반영."""
    out = store.get_output_dir()
    set_data_dir(out)
    return str(out)


def default_desktop_parent() -> Path:
    return Path.home() / "Desktop"
