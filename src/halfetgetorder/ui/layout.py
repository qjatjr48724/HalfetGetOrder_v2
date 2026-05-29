"""폼 위젯 왼쪽 정렬."""

from __future__ import annotations

import customtkinter as ctk

FORM_PADX = 12


def form_scroll_body(parent: ctk.CTkScrollableFrame) -> ctk.CTkFrame:
    """스크롤 안 콘텐츠를 왼쪽에 붙이는 컨테이너."""
    body = ctk.CTkFrame(parent, fg_color="transparent")
    body.pack(fill="x", anchor="nw")
    return body


def pack_form(widget, /, **kwargs) -> None:
    kwargs.setdefault("anchor", "w")
    kwargs.setdefault("padx", FORM_PADX)
    widget.pack(**kwargs)
