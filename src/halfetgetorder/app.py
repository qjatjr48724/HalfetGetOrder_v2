import sys

from .job_cooldown import record_last_run
from .runner import run_order_job
from .security.store import AppStore


def _pause_before_exit():
    if getattr(sys, "frozen", False):
        try:
            input("\n[완료] 작업이 끝났습니다. 창을 닫으려면 Enter를 누르세요.")
        except Exception:
            pass


def main():
    """CLI 호환 진입점 (개발·레거시). GUI에서는 runner를 직접 호출."""
    store = AppStore()

    def _print_log(msg: str) -> None:
        print(msg)

    try:
        if not store.is_keys_configured():
            print("⚠️ 설치가 완료되지 않았습니다. GUI 프로그램에서 설치 탭을 먼저 진행해 주세요.")
            return

        keys = store.load_api_keys()
        result = run_order_job(store, keys, log=_print_log, progress=lambda _: None)
        if result.get("success"):
            record_last_run(store.last_run_path)
    finally:
        _pause_before_exit()


if __name__ == "__main__":
    main()
