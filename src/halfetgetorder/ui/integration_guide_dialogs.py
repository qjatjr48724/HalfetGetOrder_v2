"""고도몰·쿠팡 API 확인 가이드 팝업."""

from __future__ import annotations

import tkinter as tk
import webbrowser
from pathlib import Path
from typing import Literal

import customtkinter as ctk

from .. import config
from .layout import fix_window_size

Platform = Literal["godo", "coupang"]

_GODO_PORTAL_URL = "https://devcenter.godo.co.kr/mypage"
_COUPANG_WING_LOGIN_URL = (
    "https://xauth.coupang.com/auth/realms/seller/protocol/openid-connect/auth?"
    "response_type=code&client_id=wing&redirect_uri=https%3A%2F%2Fwing.coupang.com%2Fsso%2Flogin"
    "?returnUrl%3Dhttp%253A%252F%252Fwing.coupang.com%252F&state=fbc11a0c-2f38-47b1-8612-0430540e7481"
    "&login=true&ui_locales=ko-KR&scope=openid"
)
_COUPANG_DOC_URL = (
    "https://developers.coupangcorp.com/hc/ko/articles/"
    "20288952179993-OpenAPI-Key-%EB%B0%9C%EA%B8%89%EB%B0%9B%EA%B8%B0"
)
_GODO_PARTNER_KEY_IMG = "guide/godo_partner_key.png"
_GODO_USER_KEY_IMG = "guide/godo_user_key.png"
# 설명 wraplength와 스크린샷 표시 너비를 동일하게
_GODO_GUIDE_CONTENT_WIDTH = 620


def _guide_asset_path(rel: str) -> Path:
    return Path(config.resource_path(rel))


def _load_photo(path: Path, *, width: int = _GODO_GUIDE_CONTENT_WIDTH) -> tk.PhotoImage:
    """스크린샷 너비를 설명 텍스트 wraplength와 맞춤."""
    try:
        from PIL import Image, ImageTk

        pil = Image.open(path)
        if pil.width != width:
            height = max(1, round(pil.height * width / pil.width))
            pil = pil.resize((width, height), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(pil)
    except ImportError:
        img = tk.PhotoImage(file=str(path))
        w = img.width()
        if w > width:
            factor = max(1, (w + width - 1) // width)
            img = img.subsample(factor, factor)
        return img


def _pack_label(parent, text: str, *, bold: bool = False, pady: tuple[int, int] = (0, 4)) -> None:
    font = ctk.CTkFont(size=13 if not bold else 14, weight="bold" if bold else "normal")
    ctk.CTkLabel(
        parent,
        text=text,
        anchor="w",
        justify="left",
        wraplength=_GODO_GUIDE_CONTENT_WIDTH,
        font=font,
    ).pack(anchor="w", pady=pady)


def _pack_photo(parent, path: Path) -> tk.PhotoImage:
    photo = _load_photo(path, width=_GODO_GUIDE_CONTENT_WIDTH)
    lbl = tk.Label(parent, image=photo, borderwidth=1, relief="solid")
    lbl.image = photo
    lbl.pack(anchor="w", pady=(0, 12))
    return photo


def _open_url(url: str) -> None:
    webbrowser.open(url)


def _show_godo_guide(parent) -> None:
    dlg = ctk.CTkToplevel(parent)
    dlg.title("고도몰 API 확인 가이드")
    fix_window_size(dlg, 720, 720)
    dlg.transient(parent)
    dlg.grab_set()

    header = ctk.CTkFrame(dlg, fg_color="transparent")
    header.pack(fill="x", padx=20, pady=(16, 8), anchor="w")
    ctk.CTkLabel(
        header,
        text="고도몰 API 확인 가이드",
        font=ctk.CTkFont(size=16, weight="bold"),
        anchor="w",
    ).pack(anchor="w")
    ctk.CTkLabel(
        header,
        text="프로그램 입력: PARTNER_KEY ← 제휴사 키 · GODO_KEY ← 사용자키",
        text_color="gray",
        font=ctk.CTkFont(size=12),
        anchor="w",
    ).pack(anchor="w", pady=(4, 0))

    scroll = ctk.CTkScrollableFrame(dlg, height=520)
    scroll.pack(fill="both", expand=True, padx=20, pady=8)

    body = ctk.CTkFrame(scroll, fg_color="transparent")
    body.pack(fill="x", anchor="w")

    _pack_label(
        body,
        "「고도몰 개발자센터 열기」 → 로그인\n\n"
        "제휴사 키\n"
        "  왼쪽 「오픈 API키」 → partner_key 확인 → 프로그램 「PARTNER_KEY」\n\n"
        "사용자키\n"
        "  왼쪽 「사용자키 발급현황」 → 하프북 → 「사용자키 확인」 → 프로그램 「GODO_KEY」",
        pady=(0, 12),
    )

    _pack_label(body, "① 제휴사 키 — 오픈 API키", bold=True)
    partner_path = _guide_asset_path(_GODO_PARTNER_KEY_IMG)
    if partner_path.is_file():
        _pack_photo(body, partner_path)
    else:
        _pack_label(body, f"(이미지 없음: {partner_path.name})", pady=(0, 12))

    _pack_label(body, "② 사용자키 — 사용자키 발급현황 → 하프북 → 사용자키 확인", bold=True)
    user_path = _guide_asset_path(_GODO_USER_KEY_IMG)
    if user_path.is_file():
        _pack_photo(body, user_path)
    else:
        _pack_label(body, f"(이미지 없음: {user_path.name})", pady=(0, 12))

    btn_row = ctk.CTkFrame(dlg, fg_color="transparent")
    btn_row.pack(fill="x", padx=20, pady=(4, 16), anchor="w")
    ctk.CTkButton(
        btn_row,
        text="고도몰 개발자센터 열기",
        width=200,
        command=lambda: _open_url(_GODO_PORTAL_URL),
    ).pack(side="left", padx=(0, 8))
    ctk.CTkButton(
        btn_row,
        text="닫기",
        width=80,
        fg_color="#555555",
        command=dlg.destroy,
    ).pack(side="left")

    dlg.bind("<Escape>", lambda _e: dlg.destroy())
    parent.wait_window(dlg)


def _show_coupang_guide(parent) -> None:
    dlg = ctk.CTkToplevel(parent)
    dlg.title("쿠팡 Wing API 확인 가이드")
    fix_window_size(dlg, 680, 360)
    dlg.transient(parent)
    dlg.grab_set()

    header = ctk.CTkFrame(dlg, fg_color="transparent")
    header.pack(fill="x", padx=20, pady=(16, 8), anchor="w")
    ctk.CTkLabel(
        header,
        text="쿠팡 Wing API 확인 가이드",
        font=ctk.CTkFont(size=16, weight="bold"),
        anchor="w",
    ).pack(anchor="w")
    ctk.CTkLabel(
        header,
        text="프로그램 입력: 「쿠팡 ACCESSKEY」 ← Access Key · 「쿠팡 SECRETKEY」 ← Secret Key",
        text_color="gray",
        font=ctk.CTkFont(size=12),
        anchor="w",
    ).pack(anchor="w", pady=(4, 0))

    body = ctk.CTkFrame(dlg, fg_color="transparent")
    body.pack(fill="x", padx=20, pady=8, anchor="w")

    _pack_label(
        body,
        "「쿠팡 Wing 로그인」 → 로그인 → 오른쪽 프로필 → 「추가판매정보」 "
        "→ Access Key · Secret Key 확인\n\n"
        "Access Key → 프로그램 「쿠팡 ACCESSKEY」\n"
        "Secret Key → 프로그램 「쿠팡 SECRETKEY」",
        pady=(0, 8),
    )

    btn_row = ctk.CTkFrame(dlg, fg_color="transparent")
    btn_row.pack(fill="x", padx=20, pady=(4, 16), anchor="w")
    ctk.CTkButton(
        btn_row,
        text="쿠팡 Wing 로그인",
        width=160,
        command=lambda: _open_url(_COUPANG_WING_LOGIN_URL),
    ).pack(side="left", padx=(0, 8))
    ctk.CTkButton(
        btn_row,
        text="Open API 키 발급 안내 (공식)",
        width=220,
        fg_color="#336699",
        hover_color="#264d73",
        command=lambda: _open_url(_COUPANG_DOC_URL),
    ).pack(side="left", padx=(0, 8))
    ctk.CTkButton(
        btn_row,
        text="닫기",
        width=80,
        fg_color="#555555",
        command=dlg.destroy,
    ).pack(side="left")

    dlg.bind("<Escape>", lambda _e: dlg.destroy())
    parent.wait_window(dlg)


def show_integration_guide(parent, platform: Platform) -> None:
    """API 확인 가이드 팝업."""
    if platform == "godo":
        _show_godo_guide(parent)
    else:
        _show_coupang_guide(parent)
