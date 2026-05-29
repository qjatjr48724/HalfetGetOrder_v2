"""설정 탭."""

from __future__ import annotations

import customtkinter as ctk
from tkinter import filedialog, messagebox

from ..security import AppStore, ApiKeys, PasswordValidationError, check_admin_password_pair
from .dialogs import ask_password
from .layout import form_scroll_body, pack_form


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

        # API 키 변경
        pack_form(
            ctk.CTkLabel(body, text="API 키 변경", font=ctk.CTkFont(size=15, weight="bold"), anchor="w"),
            padx=8,
            pady=(8, 4),
        )
        self.key_entries: dict[str, ctk.CTkEntry] = {}
        for label, key in [
            ("쿠팡 ACCESSKEY", "cp_access"),
            ("쿠팡 SECRETKEY", "cp_secret"),
            ("고도몰 PARTNER_KEY", "partner"),
            ("고도몰 GODO_KEY", "godo"),
        ]:
            pack_form(ctk.CTkLabel(body, text=label, anchor="w"))
            e = ctk.CTkEntry(body, width=400, show="*")
            pack_form(e, pady=(0, 4))
            self.key_entries[key] = e
        pack_form(ctk.CTkButton(body, text="API 키 저장", command=self._save_keys), pady=8)

        # 출력 폴더
        pack_form(
            ctk.CTkLabel(body, text="출력 폴더 변경", font=ctk.CTkFont(size=15, weight="bold"), anchor="w"),
            padx=8,
            pady=(16, 4),
        )
        row = ctk.CTkFrame(body, fg_color="transparent")
        pack_form(row, fill="x")
        setup = self.store.load_setup()
        self.output_var = ctk.StringVar(
            value=self.store.format_output_path(setup.get("output_parent", "")),
        )
        ctk.CTkEntry(row, textvariable=self.output_var, width=480).pack(side="left", padx=(0, 8))
        ctk.CTkButton(row, text="찾아보기", width=80, command=self._browse).pack(side="left")
        pack_form(ctk.CTkButton(body, text="출력 경로 저장", command=self._save_output), pady=8)

        # 비밀번호 변경
        pack_form(
            ctk.CTkLabel(body, text="관리자 비밀번호", font=ctk.CTkFont(size=15, weight="bold"), anchor="w"),
            padx=8,
            pady=(16, 4),
        )
        pack_form(ctk.CTkButton(body, text="비밀번호 변경", command=self._change_password), pady=4)
        pack_form(
            ctk.CTkButton(
                body,
                text="비밀번호 재설정 (분실 시 — API 키 재입력 필요)",
                fg_color="#9b2226",
                command=self._reset_password,
            ),
            pady=4,
        )

        # 가이드 (추후)
        pack_form(
            ctk.CTkLabel(body, text="연동 가이드", font=ctk.CTkFont(size=15, weight="bold"), anchor="w"),
            padx=8,
            pady=(16, 4),
        )
        pack_form(
            ctk.CTkLabel(
                body,
                text="고도몰·쿠팡 설정 가이드는 추후 업데이트 예정입니다.",
                text_color="gray",
                anchor="w",
            ),
        )
        row_g = ctk.CTkFrame(body, fg_color="transparent")
        pack_form(row_g, pady=8)
        ctk.CTkButton(
            row_g,
            text="고도몰 관리자 (준비 중)",
            state="disabled",
            width=160,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            row_g,
            text="쿠팡 Wing (준비 중)",
            state="disabled",
            width=160,
        ).pack(side="left")

    def _save_keys(self):
        password = ask_password(self.winfo_toplevel(), title="API 키 저장")
        if not password:
            return
        keys = ApiKeys(
            cp_accesskey=self.key_entries["cp_access"].get().strip(),
            cp_secretkey=self.key_entries["cp_secret"].get().strip(),
            partner_key=self.key_entries["partner"].get().strip(),
            godo_key=self.key_entries["godo"].get().strip(),
        )
        try:
            self.store.save_api_keys(keys, password)
            for e in self.key_entries.values():
                e.delete(0, "end")
            messagebox.showinfo("완료", "API 키가 저장되었습니다.")
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
        dlg.geometry("640x240")
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
