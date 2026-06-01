"""빌드 탭 — 엑셀 생성 + 로그 + 프로그레스."""

from __future__ import annotations

import threading

import customtkinter as ctk
from tkinter import messagebox

from ..runner import run_order_job
from ..security.store import AppStore


class BuildTab(ctk.CTkFrame):
    def __init__(self, master, store: AppStore, **kwargs):
        super().__init__(master, **kwargs)
        self.store = store
        self._running = False
        self._build_ui()

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

    def _on_run(self):
        if self._running:
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
                    self.after(
                        0,
                        lambda: messagebox.showinfo(
                            "완료",
                            f"{len(files)}개 파일이 생성되었습니다.\n\n" + "\n".join(files),
                        ),
                    )
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("오류", str(e)))
                self.after(0, lambda: self._append_log(f"❌ 오류: {e}"))
            finally:
                def done():
                    self._running = False
                    self.btn_run.configure(state="normal")

                self.after(0, done)

        threading.Thread(target=work, daemon=True).start()
