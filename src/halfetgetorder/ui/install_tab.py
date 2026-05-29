"""설치 탭 — exe: 4단계 / 개발(소스): 5단계(환경 준비 포함)."""

from __future__ import annotations

import subprocess
import sys
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox

from .. import config
from ..security import AppStore, ApiKeys, PasswordValidationError, check_admin_password_pair
from .layout import form_scroll_body, form_section, pack_section

_KEY_SAVED_PLACEHOLDER = "이미 입력되었습니다"
_KEY_LABEL_WIDTH = 160


class InstallTab(ctk.CTkFrame):
    def __init__(self, master, store: AppStore, on_install_done=None, **kwargs):
        super().__init__(master, **kwargs)
        self.store = store
        self.on_install_done = on_install_done
        self._dev_mode = not config.is_frozen()
        self.btn_venv = None
        self.btn_deps = None
        self.lbl_env = None
        self._build_ui()
        self.refresh_state()

    def _num(self, index: int) -> str:
        """1-based 단계 번호 → ①②③…"""
        circled = "①②③④⑤"
        return circled[index - 1] if 1 <= index <= len(circled) else str(index)

    def _build_ui(self):
        scroll = ctk.CTkScrollableFrame(self)
        scroll.pack(fill="both", expand=True, padx=8, pady=8)
        body = form_scroll_body(scroll)

        if self._dev_mode:
            sec_env = form_section(
                body,
                f"{self._num(1)} 환경 준비",
                desc="개발용: 가상환경(.venv)과 requirements.txt 의존성을 설치합니다.",
                pady=(4, 12),
            )
            self.lbl_env = ctk.CTkLabel(sec_env, text="", anchor="w")
            pack_section(self.lbl_env, fill="x")
            row1 = ctk.CTkFrame(sec_env, fg_color="transparent")
            pack_section(row1, fill="x", pady=4)
            self.btn_venv = ctk.CTkButton(
                row1, text="가상환경 만들기 (.venv)", command=self._create_venv
            )
            self.btn_venv.pack(side="left", padx=(0, 8))
            self.btn_deps = ctk.CTkButton(
                row1, text="의존성 설치 (requirements.txt)", command=self._install_deps
            )
            self.btn_deps.pack(side="left")

        # 관리자 비밀번호
        sec_pw = form_section(
            body,
            f"{self._num(2 if self._dev_mode else 1)} 관리자 비밀번호",
            desc="규칙: 8자 이상 / 영문, 숫자, 특수문자 포함",
            pady=(4, 12) if not self._dev_mode else (0, 12),
        )
        self.pw1 = ctk.CTkEntry(sec_pw, placeholder_text="비밀번호", show="*", width=320)
        pack_section(self.pw1, pady=2)
        row_pw2 = ctk.CTkFrame(sec_pw, fg_color="transparent")
        pack_section(row_pw2, fill="x", pady=2)
        self.pw2 = ctk.CTkEntry(row_pw2, placeholder_text="비밀번호 확인", show="*", width=320)
        self.pw2.pack(side="left", padx=(0, 12))
        self.lbl_pw_error = ctk.CTkLabel(
            row_pw2,
            text="",
            text_color="#c1121f",
            anchor="w",
            justify="left",
            wraplength=280,
        )
        self.lbl_pw_error.pack(side="left", fill="x", expand=True)
        self.pw2.bind("<FocusOut>", lambda _e: self._validate_password_fields())
        self.pw1.bind("<KeyRelease>", lambda _e: self._validate_password_fields(quiet=True))
        self.pw2.bind("<KeyRelease>", lambda _e: self._validate_password_fields(quiet=True))
        self.btn_pw = ctk.CTkButton(sec_pw, text="비밀번호 저장", command=self._save_password)
        pack_section(self.btn_pw, pady=6)
        self.lbl_pw = ctk.CTkLabel(sec_pw, text="", text_color="gray", anchor="w")
        pack_section(self.lbl_pw)

        # 출력 폴더
        sec_output = form_section(
            body,
            f"{self._num(3 if self._dev_mode else 2)} 출력 폴더",
            desc="찾아보기로 상위 폴더를 고르면 아래에 실제 저장 경로가 표시됩니다.",
        )
        row3 = ctk.CTkFrame(sec_output, fg_color="transparent")
        pack_section(row3, fill="x", pady=4)
        self.output_var = ctk.StringVar()
        self.entry_output = ctk.CTkEntry(row3, textvariable=self.output_var, width=480)
        self.entry_output.pack(side="left", padx=(0, 8))
        self.btn_browse = ctk.CTkButton(row3, text="찾아보기", width=80, command=self._browse_output)
        self.btn_browse.pack(side="left")
        self.btn_output = ctk.CTkButton(sec_output, text="출력 경로 저장", command=self._save_output)
        pack_section(self.btn_output, pady=6)

        # API 키
        sec_keys = form_section(
            body,
            f"{self._num(4 if self._dev_mode else 3)} API 키",
            desc="쿠팡·고도몰 API 키 4개를 입력합니다.",
        )
        self.key_entries: dict[str, ctk.CTkEntry] = {}
        for label, key in [
            ("쿠팡 ACCESSKEY", "cp_access"),
            ("쿠팡 SECRETKEY", "cp_secret"),
            ("고도몰 PARTNER_KEY", "partner"),
            ("고도몰 GODO_KEY", "godo"),
        ]:
            row = ctk.CTkFrame(sec_keys, fg_color="transparent")
            pack_section(row, fill="x", pady=(0, 6))
            ctk.CTkLabel(row, text=label, width=_KEY_LABEL_WIDTH, anchor="w").pack(
                side="left", padx=(0, 10)
            )
            e = ctk.CTkEntry(row, width=360, show="*")
            e.pack(side="left")
            self.key_entries[key] = e
        self.btn_keys = ctk.CTkButton(sec_keys, text="API 키 저장", command=self._save_keys)
        pack_section(self.btn_keys, pady=6)
        self.lbl_keys = ctk.CTkLabel(sec_keys, text="", text_color="gray", anchor="w")
        pack_section(self.lbl_keys)

        # 설치 완료
        sec_finish = form_section(
            body,
            f"{self._num(5 if self._dev_mode else 4)} 설치 완료",
            desc="모든 단계가 끝나면 아래 버튼을 누르세요.",
            pady=(0, 4),
        )
        self.lbl_check = ctk.CTkLabel(sec_finish, text="", anchor="w", justify="left")
        pack_section(self.lbl_check, fill="x")
        self.btn_finish = ctk.CTkButton(
            sec_finish, text="설치 완료", fg_color="#2d6a4f", command=self._finish_install
        )
        pack_section(self.btn_finish, pady=(8, 0))

    def refresh_state(self):
        setup = self.store.load_setup()
        parent = setup.get("output_parent", str(config.default_desktop_parent()))
        self.output_var.set(self.store.format_output_path(parent))

        if self._dev_mode and self.lbl_env is not None:
            env_parts = []
            if setup.get("venv_done"):
                env_parts.append("가상환경 ✓")
            if setup.get("deps_done"):
                env_parts.append("의존성 ✓")
            self.lbl_env.configure(text=" / ".join(env_parts) if env_parts else "미완료")

        if self.store.is_password_configured():
            self.lbl_pw.configure(text="✓ 관리자 비밀번호 설정됨", text_color="#2d6a4f")
            self.btn_pw.configure(state="disabled")
            self.pw1.configure(state="disabled")
            self.pw2.configure(state="disabled")
        else:
            self.lbl_pw.configure(text="", text_color="gray")
            self.btn_pw.configure(state="normal")
            self.pw1.configure(state="normal")
            self.pw2.configure(state="normal")

        if self.store.is_keys_configured():
            self.lbl_keys.configure(text="✓ API 키 저장됨", text_color="#2d6a4f")
            self.btn_keys.configure(state="disabled")
        else:
            self.lbl_keys.configure(text="", text_color="gray")
            if not setup.get("install_done", False):
                self.btn_keys.configure(state="normal")

        checks = self._checklist()
        self.lbl_check.configure(text="\n".join(checks))

        done = setup.get("install_done", False)
        if done:
            self._set_install_locked(True)
        else:
            self._set_install_locked(False)
            all_ok = all("✓" in c for c in checks)
            self.btn_finish.configure(state="normal" if all_ok else "disabled")

        self._sync_key_entries()

    def _sync_key_entries(self) -> None:
        """저장된 API 키는 입력란에 안내 문구 표시 (disabled placeholder는 CTk에서 안 보임)."""
        saved = self.store.is_keys_configured()
        setup = self.store.load_setup()
        install_locked = setup.get("install_done", False)

        for e in self.key_entries.values():
            if saved:
                e.configure(state="normal")
                e.delete(0, "end")
                e.insert(0, _KEY_SAVED_PLACEHOLDER)
                e.configure(state="disabled", show="", text_color="#6b7280")
            elif not install_locked:
                if e.get() == _KEY_SAVED_PLACEHOLDER:
                    e.delete(0, "end")
                e.configure(state="normal", show="*", text_color=("gray10", "gray90"))
            else:
                e.configure(state="disabled")

    def _checklist(self) -> list[str]:
        setup = self.store.load_setup()
        items: list[str] = []
        if self._dev_mode:
            env_ok = setup.get("venv_done") and setup.get("deps_done")
            items.append(f"{'✓' if env_ok else '○'} 환경 준비")
        items.append(f"{'✓' if self.store.is_password_configured() else '○'} 관리자 비밀번호")
        items.append(f"{'✓' if setup.get('output_parent') else '○'} 출력 폴더")
        items.append(f"{'✓' if self.store.is_keys_configured() else '○'} API 키")
        return items

    def _install_widgets(self) -> list:
        widgets = [
            self.btn_pw,
            self.btn_browse,
            self.btn_output,
            self.btn_keys,
            self.btn_finish,
            self.pw1,
            self.pw2,
            self.entry_output,
        ]
        if self.btn_venv is not None:
            widgets.append(self.btn_venv)
        if self.btn_deps is not None:
            widgets.append(self.btn_deps)
        widgets.extend(self.key_entries.values())
        return widgets

    def _set_install_locked(self, locked: bool):
        state = "disabled" if locked else "normal"
        for w in self._install_widgets():
            w.configure(state=state)
        if locked:
            self.btn_finish.configure(text="설치 완료됨")
        self._sync_key_entries()

    def _create_venv(self):
        root = config.project_root()
        venv_path = root / ".venv"
        if venv_path.exists():
            messagebox.showinfo("안내", "이미 .venv 폴더가 있습니다.")
            setup = self.store.load_setup()
            setup["venv_done"] = True
            self.store.save_setup(setup)
            self.refresh_state()
            return

        def work():
            try:
                subprocess.run(
                    [sys.executable, "-m", "venv", str(venv_path)],
                    check=True,
                    cwd=str(root),
                )
                setup = self.store.load_setup()
                setup["venv_done"] = True
                self.store.save_setup(setup)
                self.after(0, lambda: messagebox.showinfo("완료", "가상환경이 생성되었습니다."))
            except Exception as e:
                self._show_async_error(self._format_cmd_error(e))
            finally:
                self.after(0, self.refresh_state)

        threading.Thread(target=work, daemon=True).start()

    def _format_cmd_error(self, exc: Exception) -> str:
        if isinstance(exc, subprocess.CalledProcessError):
            detail = (exc.stderr or exc.stdout or b"").decode("utf-8", errors="replace").strip()
            msg = f"명령 실행 실패 (코드 {exc.returncode})"
            if detail:
                return f"{msg}\n\n{detail}"
            return msg
        text = str(exc).strip()
        return text if text else repr(exc)

    def _show_async_error(self, message: str) -> None:
        self.after(0, lambda msg=message: messagebox.showerror("오류", msg))

    def _install_deps(self):
        root = config.project_root()
        req = root / "requirements.txt"
        venv_py = root / ".venv" / "Scripts" / "python.exe"
        py = str(venv_py) if venv_py.exists() else sys.executable

        def work():
            try:
                subprocess.run(
                    [py, "-m", "pip", "install", "--upgrade", "pip"],
                    check=True,
                    cwd=str(root),
                    capture_output=True,
                )
                subprocess.run(
                    [py, "-m", "pip", "install", "-r", str(req)],
                    check=True,
                    cwd=str(root),
                    capture_output=True,
                )
                setup = self.store.load_setup()
                setup["deps_done"] = True
                self.store.save_setup(setup)
                self.after(0, lambda: messagebox.showinfo("완료", "의존성 설치가 완료되었습니다."))
            except Exception as e:
                self._show_async_error(self._format_cmd_error(e))
            finally:
                self.after(0, self.refresh_state)

        threading.Thread(target=work, daemon=True).start()

    def _validate_password_fields(self, *, quiet: bool = False) -> bool:
        """입력값 검증. quiet=True면 통과 시 메시지를 지움."""
        p1, p2 = self.pw1.get(), self.pw2.get()
        if not p1 and not p2:
            if not quiet:
                self.lbl_pw_error.configure(text="")
            return False
        try:
            check_admin_password_pair(p1, p2)
            self.lbl_pw_error.configure(text="✓ 사용 가능한 비밀번호입니다.", text_color="#2d6a4f")
            return True
        except PasswordValidationError as e:
            self.lbl_pw_error.configure(text=str(e), text_color="#c1121f")
            return False

    def _save_password(self):
        p1, p2 = self.pw1.get(), self.pw2.get()
        if not self._validate_password_fields():
            messagebox.showerror("오류", self.lbl_pw_error.cget("text") or "비밀번호를 확인해 주세요.")
            return
        try:
            check_admin_password_pair(p1, p2)
            self.store.setup_admin_password(p1)
            messagebox.showinfo("완료", "관리자 비밀번호가 저장되었습니다.")
            self.pw1.delete(0, "end")
            self.pw2.delete(0, "end")
            self.lbl_pw_error.configure(text="")
        except PasswordValidationError as e:
            messagebox.showerror("오류", str(e))
        except Exception as e:
            messagebox.showerror("오류", str(e))
        self.refresh_state()

    def _browse_output(self):
        path = filedialog.askdirectory(
            title="저장 위치 선택 (하프전자 주문수집기 폴더는 자동으로 생성됩니다)",
        )
        if path:
            self.output_var.set(self.store.format_output_path(path))

    def _save_output(self):
        try:
            parent = self.store.parse_output_parent(self.output_var.get())
        except ValueError as e:
            messagebox.showerror("오류", str(e))
            return
        setup = self.store.load_setup()
        setup["output_parent"] = str(parent)
        self.store.save_setup(setup)
        try:
            out = self.store.get_output_dir()
            self.output_var.set(str(out))
            messagebox.showinfo("완료", f"저장되었습니다.\n{out}")
        except Exception as e:
            messagebox.showerror("오류", str(e))
        self.refresh_state()

    def _save_keys(self):
        if not self.store.is_password_configured():
            messagebox.showerror("오류", "먼저 관리자 비밀번호를 설정해 주세요.")
            return
        keys = ApiKeys(
            cp_accesskey=self.key_entries["cp_access"].get().strip(),
            cp_secretkey=self.key_entries["cp_secret"].get().strip(),
            partner_key=self.key_entries["partner"].get().strip(),
            godo_key=self.key_entries["godo"].get().strip(),
        )
        try:
            self.store.save_api_keys_at_install(keys)
            for e in self.key_entries.values():
                e.delete(0, "end")
            messagebox.showinfo("완료", "API 키가 암호화되어 저장되었습니다.")
        except Exception as e:
            messagebox.showerror("오류", str(e))
        self.refresh_state()

    def _finish_install(self):
        setup = self.store.load_setup()
        setup["install_done"] = True
        self.store.save_setup(setup)
        messagebox.showinfo("완료", "설치가 완료되었습니다. 빌드 탭에서 파일을 생성할 수 있습니다.")
        self.refresh_state()
        if self.on_install_done:
            self.on_install_done()
