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


def pack_section(widget, /, **kwargs) -> None:
    """form_section 안쪽 위젯용 (좌측 여백 없음)."""
    kwargs.setdefault("anchor", "w")
    kwargs.setdefault("padx", 0)
    widget.pack(**kwargs)


def form_section(
    parent: ctk.CTkFrame,
    title: str,
    *,
    desc: str | None = None,
    pady: tuple[int, int] = (0, 12),
) -> ctk.CTkFrame:
    """항목별 구분 카드 — 제목·설명과 콘텐츠용 inner frame 반환."""
    card = ctk.CTkFrame(
        parent,
        corner_radius=8,
        border_width=1,
        border_color=("#d1d5db", "#404040"),
    )
    card.pack(fill="x", anchor="w", padx=FORM_PADX, pady=pady)

    inner = ctk.CTkFrame(card, fg_color="transparent")
    inner.pack(fill="x", padx=14, pady=12, anchor="w")

    ctk.CTkLabel(
        inner,
        text=title,
        font=ctk.CTkFont(size=15, weight="bold"),
        anchor="w",
    ).pack(anchor="w", pady=(0, 2))
    if desc:
        ctk.CTkLabel(
            inner,
            text=desc,
            text_color="gray",
            font=ctk.CTkFont(size=12),
            anchor="w",
        ).pack(anchor="w", pady=(0, 8))

    content = ctk.CTkFrame(inner, fg_color="transparent")
    content.pack(fill="x", anchor="w")
    return content


def fix_window_size(window, width: int, height: int) -> None:
    """창 크기를 고정하고 사용자 조절을 막는다."""
    window.geometry(f"{width}x{height}")
    window.resizable(False, False)
    window.minsize(width, height)
    window.maxsize(width, height)
