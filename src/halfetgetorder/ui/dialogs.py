"""공용 다이얼로그."""

from __future__ import annotations

import customtkinter as ctk


def ask_password(parent, *, title: str = "관리자 비밀번호") -> str | None:
    result: list[str | None] = [None]

    dlg = ctk.CTkToplevel(parent)
    dlg.title(title)
    dlg.geometry("400x160")
    dlg.transient(parent)
    dlg.grab_set()

    body = ctk.CTkFrame(dlg, fg_color="transparent")
    body.pack(fill="x", padx=20, pady=(16, 8), anchor="w")
    ctk.CTkLabel(body, text="관리자 비밀번호를 입력하세요.", anchor="w").pack(anchor="w")
    entry = ctk.CTkEntry(body, width=280, show="*")
    entry.pack(anchor="w", pady=4)
    entry.focus_set()

    def ok():
        result[0] = entry.get()
        dlg.destroy()

    def cancel():
        result[0] = None
        dlg.destroy()

    btn_row = ctk.CTkFrame(dlg, fg_color="transparent")
    btn_row.pack(pady=12, padx=20, anchor="w")
    ctk.CTkButton(btn_row, text="확인", width=100, command=ok).pack(side="left", padx=6)
    ctk.CTkButton(btn_row, text="취소", width=100, fg_color="gray", command=cancel).pack(
        side="left", padx=6
    )

    dlg.bind("<Return>", lambda _e: ok())
    dlg.bind("<Escape>", lambda _e: cancel())
    parent.wait_window(dlg)
    return result[0]
