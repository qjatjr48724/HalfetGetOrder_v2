"""메인 GUI."""

from __future__ import annotations

import customtkinter as ctk

from ..security.store import AppStore
from .build_tab import BuildTab
from .install_tab import InstallTab
from .settings_tab import SettingsTab


def run_gui():
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    store = AppStore()
    app = ctk.CTk()
    app.title("하프전자 주문수집기 v2")
    app.geometry("720x640")
    app.minsize(640, 520)

    header = ctk.CTkLabel(
        app,
        text="하프전자 주문수집기",
        font=ctk.CTkFont(size=20, weight="bold"),
    )
    header.pack(pady=(12, 4))

    tabview = ctk.CTkTabview(app, width=680, height=560)
    tabview.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    tab_install = tabview.add("설치")
    tab_build = tabview.add("빌드")
    tab_settings = tabview.add("설정")

    def on_install_done():
        build_tab._update_output_label()

    def on_reset():
        install_tab.refresh_state()
        tabview.set("설치")

    install_tab = InstallTab(tab_install, store, on_install_done=on_install_done)
    install_tab.pack(fill="both", expand=True)

    build_tab = BuildTab(tab_build, store)
    build_tab.pack(fill="both", expand=True)

    settings_tab = SettingsTab(tab_settings, store, on_reset_install=on_reset)
    settings_tab.pack(fill="both", expand=True)

    setup = store.load_setup()
    if setup.get("install_done"):
        tabview.set("빌드")
    else:
        tabview.set("설치")

    app.mainloop()
