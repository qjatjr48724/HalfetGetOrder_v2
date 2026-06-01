"""설정 탭."""

from __future__ import annotations

import customtkinter as ctk
from tkinter import filedialog, messagebox

from ..security import AppStore, PasswordValidationError, check_admin_password_pair
from .api_key_dialogs import open_api_key_manager
from .dialogs import ask_password
from .integration_guide_dialogs import show_integration_guide
from .layout import fix_window_size, form_scroll_body, form_section, pack_section


class SettingsTab(ctk.CTkFrame):
    def __init__(self, master, store: AppStore, on_reset_install=None, **kwargs):
        super().__init__(master, **kwargs)
        self.store = store
        self.on_reset_install = on_reset_install
        self._build_ui()

    def _build_ui(self):
        scroll = ctk.CTkScrollableFrame(self)
        scroll.pack(fill="both", expand=True, padx=8, pady=8)
        body = form_scroll_body(scroll)

        # API 키
        sec_keys = form_section(body, "API 키 변경", pady=(4, 12))
        pack_section(
            ctk.CTkButton(sec_keys, text="API 키 관리", width=140, command=self._open_api_key_manager),
            pady=(0, 8),
        )
        pack_section(
            ctk.CTkButton(
                sec_keys,
                text="API 키 연결 복구 (비밀번호만 입력)",
                command=self._repair_keys,
            ),
            pady=(0, 8),
        )
        pack_section(
            ctk.CTkLabel(
                sec_keys,
                text="빌드 시 키를 불러오지 못할 때: 위 「연결 복구」를 실행하세요.",
                text_color="gray",
                font=ctk.CTkFont(size=12),
                anchor="w",
            ),
        )

        # 출력 폴더
        sec_output = form_section(body, "출력 폴더 변경")
        row = ctk.CTkFrame(sec_output, fg_color="transparent")
        pack_section(row, fill="x")
        setup = self.store.load_setup()
        self.output_var = ctk.StringVar(
            value=self.store.format_output_path(setup.get("output_parent", "")),
        )
        ctk.CTkEntry(row, textvariable=self.output_var, width=480).pack(side="left", padx=(0, 8))
        ctk.CTkButton(row, text="찾아보기", width=80, command=self._browse).pack(side="left")
        pack_section(ctk.CTkButton(sec_output, text="출력 경로 저장", command=self._save_output), pady=(8, 0))

        # 비밀번호
        sec_pw = form_section(body, "관리자 비밀번호")
        pack_section(ctk.CTkButton(sec_pw, text="비밀번호 변경", command=self._change_password), pady=(0, 8))
        pack_section(
            ctk.CTkButton(
                sec_pw,
                text="비밀번호 재설정 (분실 시 — API 키 재입력 필요)",
                fg_color="#9b2226",
                command=self._reset_password,
            ),
        )

        sec_guide = form_section(
            body,
            "API 확인 가이드",
            desc="IP 등록·API 키 발급·프로그램에 키 반영 방법을 안내합니다.",
            pady=(0, 4),
        )
        row_g = ctk.CTkFrame(sec_guide, fg_color="transparent")
        pack_section(row_g)
        ctk.CTkButton(
            row_g,
            text="고도몰 API 확인 가이드",
            width=180,
            command=lambda: show_integration_guide(
                self.winfo_toplevel(), "godo"
            ),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            row_g,
            text="쿠팡 Wing API 확인 가이드",
            width=180,
            command=lambda: show_integration_guide(
                self.winfo_toplevel(), "coupang"
            ),
        ).pack(side="left")

    def _open_api_key_manager(self):
        if not self.store.is_keys_configured():
            messagebox.showwarning(
                "안내",
                "저장된 API 키가 없습니다.\n설치 탭에서 API 키를 먼저 등록해 주세요.",
            )
            return
        open_api_key_manager(self.winfo_toplevel(), self.store)

    def _repair_keys(self):
        if not self.store.needs_local_key_repair() and self.store._keys_local_path.exists():
            messagebox.showinfo("안내", "API 키 연결이 정상입니다. 복구가 필요하지 않습니다.")
            return
        password = ask_password(self.winfo_toplevel(), title="API 키 연결 복구")
        if not password:
            return
        try:
            self.store.repair_local_keys(password)
            messagebox.showinfo(
                "완료",
                "이 PC에서 API 키를 사용할 수 있도록 복구했습니다.\n빌드 탭에서 파일 생성을 다시 시도해 주세요.",
            )
        except Exception as e:
            messagebox.showerror("오류", str(e))

    def _browse(self):
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
        out = self.store.get_output_dir()
        self.output_var.set(str(out))
        messagebox.showinfo("완료", f"출력 폴더:\n{out}")

    def _change_password(self):
        old = ask_password(self.winfo_toplevel(), title="현재 비밀번호")
        if not old:
            return

        dlg = ctk.CTkToplevel(self.winfo_toplevel())
        dlg.title("새 비밀번호")
        fix_window_size(dlg, 640, 240)
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()

        body = ctk.CTkFrame(dlg, fg_color="transparent")
        body.pack(fill="x", padx=20, anchor="w")
        ctk.CTkLabel(
            body,
            text="규칙: 8자 이상 / 영문, 숫자, 특수문자 포함",
            text_color="gray",
            font=ctk.CTkFont(size=12),
            anchor="w",
        ).pack(anchor="w", pady=(12, 6))
        ctk.CTkLabel(body, text="새 비밀번호", anchor="w").pack(anchor="w", pady=(0, 4))
        e1 = ctk.CTkEntry(body, width=300, show="*")
        e1.pack(anchor="w")
        ctk.CTkLabel(body, text="새 비밀번호 확인", anchor="w").pack(anchor="w", pady=(8, 4))
        row_pw2 = ctk.CTkFrame(body, fg_color="transparent")
        row_pw2.pack(anchor="w", fill="x")
        e2 = ctk.CTkEntry(row_pw2, width=300, show="*")
        e2.pack(side="left", padx=(0, 12))
        lbl_err = ctk.CTkLabel(
            row_pw2,
            text="",
            text_color="gray",
            font=ctk.CTkFont(size=12),
            anchor="w",
            justify="left",
            wraplength=240,
        )
        lbl_err.pack(side="left", fill="x", expand=True)

        def validate_fields() -> bool:
            try:
                check_admin_password_pair(e1.get(), e2.get())
                lbl_err.configure(text="✓ 사용 가능한 비밀번호입니다.", text_color="#2d6a4f")
                return True
            except PasswordValidationError as ex:
                lbl_err.configure(text=str(ex), text_color="#c1121f")
                return False

        e2.bind("<FocusOut>", lambda _e: validate_fields())

        def ok():
            if not validate_fields():
                messagebox.showerror("오류", lbl_err.cget("text"), parent=dlg)
                return
            try:
                check_admin_password_pair(e1.get(), e2.get())
                self.store.change_admin_password(old, e1.get())
                messagebox.showinfo("완료", "비밀번호가 변경되었습니다.", parent=dlg)
                dlg.destroy()
            except PasswordValidationError as ex:
                messagebox.showerror("오류", str(ex), parent=dlg)
            except Exception as ex:
                messagebox.showerror("오류", str(ex), parent=dlg)

        ctk.CTkButton(dlg, text="저장", command=ok).pack(pady=12, padx=20, anchor="w")

    def _reset_password(self):
        if not messagebox.askyesno(
            "확인",
            "관리자 비밀번호와 저장된 API 키가 삭제됩니다.\n"
            "설치 탭에서 비밀번호·API 키를 다시 설정해야 합니다.\n\n계속하시겠습니까?",
        ):
            return
        self.store.reset_admin_and_keys()
        setup = self.store.load_setup()
        setup["install_done"] = False
        self.store.save_setup(setup)
        messagebox.showinfo("완료", "재설정되었습니다. 설치 탭에서 다시 설정해 주세요.")
        if self.on_reset_install:
            self.on_reset_install()
