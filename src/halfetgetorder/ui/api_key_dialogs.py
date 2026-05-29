"""API 키 관리·변경 팝업."""

from __future__ import annotations

import customtkinter as ctk
from tkinter import messagebox

from ..security.store import ApiKeys, AppStore
from .dialogs import ask_password
from .layout import fix_window_size

# (ApiKeys 필드명, 표시 이름)
API_KEY_ROWS: list[tuple[str, str]] = [
    ("cp_accesskey", "쿠팡 ACCESSKEY"),
    ("cp_secretkey", "쿠팡 SECRETKEY"),
    ("partner_key", "고도몰 PARTNER_KEY"),
    ("godo_key", "고도몰 GODO_KEY"),
]


def mask_api_key(value: str) -> str:
    """앞 4자 + **** + 뒤 4자 미리보기."""
    v = (value or "").strip()
    if not v:
        return "(미설정)"
    if len(v) <= 8:
        return "****"
    return f"{v[:4]}****{v[-4:]}"


def _load_current_keys(store: AppStore) -> ApiKeys | None:
    if not store.is_keys_configured():
        return None
    try:
        return store.load_api_keys()
    except Exception:
        return None


def _empty_keys() -> ApiKeys:
    return ApiKeys("", "", "", "")


def _keys_with_field(field: str, value: str) -> ApiKeys:
    base = _empty_keys()
    data = base.to_dict()
    data[field] = value
    return ApiKeys.from_dict(data)


def _ask_new_key_value(parent, title: str, label: str) -> str | None:
    result: list[str | None] = [None]

    dlg = ctk.CTkToplevel(parent)
    dlg.title(title)
    fix_window_size(dlg, 440, 180)
    dlg.transient(parent)
    dlg.grab_set()

    body = ctk.CTkFrame(dlg, fg_color="transparent")
    body.pack(fill="x", padx=20, pady=(16, 8), anchor="w")
    ctk.CTkLabel(body, text=label, anchor="w").pack(anchor="w", pady=(0, 6))
    entry = ctk.CTkEntry(body, width=360, show="*")
    entry.pack(anchor="w")
    entry.focus_set()

    def save():
        val = entry.get().strip()
        if not val:
            messagebox.showerror("오류", "새 API 키 값을 입력해 주세요.", parent=dlg)
            return
        result[0] = val
        dlg.destroy()

    def cancel():
        result[0] = None
        dlg.destroy()

    row = ctk.CTkFrame(dlg, fg_color="transparent")
    row.pack(pady=12, padx=20, anchor="w")
    ctk.CTkButton(row, text="저장", width=100, command=save).pack(side="left", padx=(0, 8))
    ctk.CTkButton(row, text="취소", width=100, fg_color="gray", command=cancel).pack(side="left")

    dlg.bind("<Return>", lambda _e: save())
    dlg.bind("<Escape>", lambda _e: cancel())
    parent.wait_window(dlg)
    return result[0]


def open_api_key_manager(parent, store: AppStore) -> None:
    """API 키 목록 팝업 — 미리보기 + 개별 변경."""
    dlg = ctk.CTkToplevel(parent)
    dlg.title("API 키 관리")
    fix_window_size(dlg, 520, 320)
    dlg.transient(parent)
    dlg.grab_set()

    body = ctk.CTkFrame(dlg, fg_color="transparent")
    body.pack(fill="both", expand=True, padx=16, pady=16)

    ctk.CTkLabel(
        body,
        text="변경할 항목의 「변경」을 누르세요.",
        text_color="gray",
        font=ctk.CTkFont(size=12),
        anchor="w",
    ).pack(anchor="w", pady=(0, 12))

    preview_labels: dict[str, ctk.CTkLabel] = {}

    def refresh_previews() -> None:
        current = _load_current_keys(store)
        for field, _title in API_KEY_ROWS:
            val = getattr(current, field, "") if current else ""
            preview_labels[field].configure(text=mask_api_key(val))

    def on_change(field: str, title: str):
        new_val = _ask_new_key_value(dlg, f"{title} 변경", title)
        if not new_val:
            return

        password = ask_password(dlg, title="관리자 비밀번호 확인", confirm_text="완료")
        if not password:
            return

        try:
            partial = _keys_with_field(field, new_val)
            store.save_api_keys(partial, password, allow_partial=True)
            refresh_previews()
            messagebox.showinfo("완료", f"{title}이(가) 저장되었습니다.", parent=dlg)
        except Exception as e:
            messagebox.showerror("오류", str(e), parent=dlg)

    for field, title in API_KEY_ROWS:
        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="x", pady=6)

        ctk.CTkLabel(row, text=title, width=150, anchor="w").pack(side="left", padx=(0, 8))
        lbl = ctk.CTkLabel(row, text="...", width=180, anchor="w", text_color="#374151")
        lbl.pack(side="left", padx=(0, 12))
        preview_labels[field] = lbl

        ctk.CTkButton(
            row,
            text="변경",
            width=72,
            command=lambda f=field, t=title: on_change(f, t),
        ).pack(side="left")

    refresh_previews()

    ctk.CTkButton(body, text="닫기", fg_color="gray", command=dlg.destroy).pack(anchor="e", pady=(16, 0))

    parent.wait_window(dlg)
