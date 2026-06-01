"""빌드 탭 — 엑셀 생성 + 로그 + 프로그레스."""

from __future__ import annotations

import threading

import customtkinter as ctk
from tkinter import messagebox

from ..job_cooldown import (
    MIN_INTERVAL_MINUTES,
    format_block_message,
    format_remaining_hms,
    get_last_run_datetime,
    get_remaining_seconds,
    record_last_run,
)
from ..runner import run_order_job
from ..security.store import AppStore


class BuildTab(ctk.CTkFrame):
    def __init__(self, master, store: AppStore, **kwargs):
        super().__init__(master, **kwargs)
        self.store = store
        self._running = False
        self._cooldown_tick_id: str | None = None
        self._build_ui()
        self._schedule_cooldown_tick()
        self.bind("<Destroy>", self._on_destroy, add="+")

    def _build_ui(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=12)

        self.btn_run = ctk.CTkButton(
            top,
            text="파일 생성",
            width=160,
            height=40,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._on_run,
        )
        self.btn_run.pack(side="left")

        self.lbl_out = ctk.CTkLabel(top, text="", anchor="w")
        self.lbl_out.pack(side="left", padx=16)

        cooldown_row = ctk.CTkFrame(self, fg_color="transparent")
        cooldown_row.pack(fill="x", padx=12, pady=(0, 4))
        self.lbl_cooldown = ctk.CTkLabel(
            cooldown_row,
            text="",
            anchor="w",
            font=ctk.CTkFont(size=13),
        )
        self.lbl_cooldown.pack(anchor="w")

        self.log = ctk.CTkTextbox(self, height=320)
        self.log.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        self.log.configure(state="disabled")

        self.progress = ctk.CTkProgressBar(self)
        self.progress.pack(fill="x", padx=12, pady=(0, 12))
        self.progress.set(0)

        self._append_log("빌드 탭: 「파일 생성」을 누르면 엑셀 3종을 만듭니다.")
        self._update_output_label()

    def _update_output_label(self):
        try:
            out = self.store.get_output_dir()
            self.lbl_out.configure(text=f"저장 위치: {out}")
        except Exception:
            self.lbl_out.configure(text="")

    def _append_log(self, msg: str):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _set_progress(self, value: float):
        self.progress.set(value / 100.0)

    def _on_destroy(self, _event=None) -> None:
        if self._cooldown_tick_id is not None:
            try:
                self.after_cancel(self._cooldown_tick_id)
            except Exception:
                pass
            self._cooldown_tick_id = None

    def _get_cooldown_remaining(self) -> int:
        return get_remaining_seconds(self.store.last_run_path)

    def _update_cooldown_ui(self) -> None:
        remain = self._get_cooldown_remaining()
        if remain > 0:
            self.lbl_cooldown.configure(
                text=(
                    f"고도몰·쿠팡 API 재실행 대기 ({MIN_INTERVAL_MINUTES}분 제한) — "
                    f"남은 시간 {format_remaining_hms(remain)}"
                ),
                text_color="#E67E22",
            )
            if not self._running:
                self.btn_run.configure(state="disabled")
        else:
            self.lbl_cooldown.configure(text="", text_color="gray")
            if not self._running:
                self.btn_run.configure(state="normal")

    def _schedule_cooldown_tick(self) -> None:
        self._update_cooldown_ui()
        self._cooldown_tick_id = self.after(1000, self._schedule_cooldown_tick)

    def _on_job_success(self, files: list[str]) -> None:
        """완료 팝업이 뜨는 시점부터 2분 재실행 대기를 시작합니다."""
        record_last_run(self.store.last_run_path)
        self._update_cooldown_ui()
        messagebox.showinfo(
            "완료",
            f"{len(files)}개 파일이 생성되었습니다.\n\n" + "\n".join(files),
        )

    def _on_run(self):
        if self._running:
            return
        remain = self._get_cooldown_remaining()
        if remain > 0:
            last_dt = get_last_run_datetime(self.store.last_run_path)
            messagebox.showwarning("대기 필요", format_block_message(remain, last_dt=last_dt))
            return
        setup = self.store.load_setup()
        if not setup.get("install_done"):
            messagebox.showwarning("안내", "설치 탭에서 설치를 먼저 완료해 주세요.")
            return
        if not self.store.is_keys_configured():
            messagebox.showwarning("안내", "API 키를 먼저 설정해 주세요.")
            return

        try:
            keys = self.store.load_api_keys()
        except Exception as e:
            messagebox.showerror("오류", str(e))
            return

        self._running = True
        self.btn_run.configure(state="disabled")
        self.progress.set(0)
        self._append_log("——— 작업 시작 ———")
        self._update_output_label()

        def work():
            try:
                result = run_order_job(
                    self.store,
                    keys,
                    log=lambda m: self.after(0, lambda msg=m: self._append_log(msg)),
                    progress=lambda v: self.after(0, lambda val=v: self._set_progress(val)),
                )
                if result.get("error"):
                    files = result.get("files", [])
                    if files:
                        body = (
                            f"{len(files)}개 파일은 저장되었습니다.\n\n"
                            + "\n".join(files)
                            + "\n\n"
                            + result["error"]
                        )
                        self.after(0, lambda b=body: messagebox.showwarning("일부 실패", b))
                    else:
                        self.after(
                            0,
                            lambda: messagebox.showerror("오류", result["error"]),
                        )
                elif result.get("success"):
                    files = result.get("files", [])
                    self.after(0, lambda f=files: self._on_job_success(f))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("오류", str(e)))
                self.after(0, lambda: self._append_log(f"❌ 오류: {e}"))
            finally:
                def done():
                    self._running = False
                    self._update_cooldown_ui()

                self.after(0, done)

        threading.Thread(target=work, daemon=True).start()
