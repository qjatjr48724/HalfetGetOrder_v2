"""엑셀 생성 작업 (GUI·CLI 공용)."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from datetime import date, datetime
from typing import Any

from . import config, coupang, godo
from .io_excel import (
    create_label_workbook,
    create_orders_workbook,
    create_waybill_workbook,
)
from .security.store import ApiKeys, AppStore

LogFn = Callable[[str], None]
ProgressFn = Callable[[float], None]

MIN_INTERVAL_MINUTES = 2


def _is_rental_order(od: dict) -> bool:
    rental_keywords = ["렌탈", "대여", "임대"]
    for item in od.get("orderItems", []) or []:
        name_candidates = [
            item.get("sellerProductName", "") or "",
            item.get("sellerProductItemName", "") or "",
            item.get("vendorItemName", "") or "",
        ]
        for name in name_candidates:
            for kw in rental_keywords:
                if kw in name:
                    return True
    return False


def run_order_job(
    store: AppStore,
    keys: ApiKeys,
    *,
    log: LogFn | None = None,
    progress: ProgressFn | None = None,
) -> dict[str, Any]:
    """
    주문 수집 + 엑셀 3종 생성.
    반환: {"success": bool, "files": [...], "error": str|None}
    """
    result: dict[str, Any] = {"success": False, "files": [], "error": None}

    def _log(msg: str) -> None:
        if log:
            log(msg)

    def _prog(value: float) -> None:
        if progress:
            progress(max(0.0, min(100.0, value)))

    today = date.today().strftime("%Y%m%d")
    data_dir = config.init_data_dir_from_store(store)
    _log(f"출력 폴더: {data_dir}")

    config.apply_runtime_keys(
        cp_access=keys.cp_accesskey,
        cp_secret=keys.cp_secretkey,
        partner_key=keys.partner_key,
        godo_key=keys.godo_key,
    )

    _prog(5)
    last_run_path = str(store.last_run_path)
    now = datetime.now()

    try:
        if os.path.exists(last_run_path):
            with open(last_run_path, encoding="utf-8") as f:
                info = json.load(f)
            last_ts = info.get("ts")
            if last_ts:
                last_dt = datetime.fromisoformat(last_ts)
                elapsed = (now - last_dt).total_seconds()
                if elapsed < MIN_INTERVAL_MINUTES * 60:
                    remain = int(MIN_INTERVAL_MINUTES * 60 - elapsed)
                    msg = (
                        f"⚠️ 고도몰 API 보호: 최소 {MIN_INTERVAL_MINUTES}분 간격이 필요합니다.\n"
                        f"   마지막 실행: {last_dt.strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"   약 {remain}초 후 다시 시도해 주세요."
                    )
                    _log(msg)
                    result["error"] = msg
                    return result
    except Exception as e:
        _log(f"⚠️ 실행 간격 확인 중 오류 (계속 진행): {e}")

    _prog(15)
    _log("쿠팡 주문 조회 중...")
    cp_body = coupang.fetch_orders()

    _prog(30)
    _log("고도몰 주문 조회 중...")
    godo_json = godo.fetch_orders()
    grouped = godo.group_sets(godo_json)

    try:
        with open(last_run_path, "w", encoding="utf-8") as f:
            json.dump({"ts": now.isoformat()}, f)
    except Exception as e:
        _log(f"⚠️ 마지막 실행 시각 저장 실패: {e}")

    _prog(40)
    filtered_orders: list = []
    filtered_cp_body = ""

    try:
        resp_json = json.loads(cp_body) if cp_body else {}
        orders = resp_json.get("data") or resp_json.get("content", []) or []
        filtered_orders = [od for od in orders if not _is_rental_order(od)]

        if "data" in resp_json:
            resp_json_filtered = dict(resp_json)
            resp_json_filtered["data"] = filtered_orders
        elif "content" in resp_json:
            resp_json_filtered = dict(resp_json)
            resp_json_filtered["content"] = filtered_orders
        else:
            resp_json_filtered = resp_json

        filtered_cp_body = json.dumps(resp_json_filtered, ensure_ascii=False)
    except Exception as e:
        _log(f"⚠️ 쿠팡 JSON 파싱/필터링 오류: {e}")
        filtered_cp_body = cp_body or ""

    _prog(50)
    _log("주문수집 엑셀 생성 중...")
    try:
        wb_orders, _ = create_orders_workbook(
            coupang_orders=filtered_orders,
            godo_grouped_orders=grouped,
        )
        order_xlsx = os.path.join(data_dir, f"주문수집_{today}.xlsx")
        wb_orders.save(order_xlsx)
        result["files"].append(order_xlsx)
        _log(f"✅ 저장: {order_xlsx}")
    except Exception as e:
        _log(f"⚠️ 주문수집 엑셀 오류: {e}")

    _prog(65)
    _log("대한통운 송장등록 엑셀 생성 중...")
    try:
        norm_cp_orders = (
            coupang.normalize_coupang_orders(filtered_cp_body)
            if filtered_cp_body
            else []
        )
    except Exception as e:
        _log(f"⚠️ 쿠팡 송장 정규화 오류: {e}")
        norm_cp_orders = []

    if norm_cp_orders:
        wb1, _ = create_waybill_workbook(norm_cp_orders)
        waybill_xlsx = os.path.join(data_dir, f"대한통운 송장등록_{today}.xlsx")
        wb1.save(waybill_xlsx)
        result["files"].append(waybill_xlsx)
        _log(f"✅ 저장: {waybill_xlsx}")
    else:
        _log("ℹ️ 쿠팡 주문 없음 — 대한통운 송장등록 파일 생략")

    _prog(75)
    _log("라벨출력 엑셀 생성 중... (10~30초 소요될 수 있습니다)")

    label_wb, _ = create_label_workbook(
        coupang_orders=filtered_orders,
        godo_grouped_orders=grouped,
        godo_add_goods_map_path=os.path.join(
            config.project_root(),
            "godo_add_goods_all.json",
        ),
    )
    label_path = os.path.join(data_dir, f"라벨출력_{today}.xlsx")
    label_wb.save(label_path)
    result["files"].append(label_path)
    _log(f"✅ 저장: {label_path}")

    _prog(100)
    _log("모든 작업이 완료되었습니다.")
    result["success"] = True
    return result
