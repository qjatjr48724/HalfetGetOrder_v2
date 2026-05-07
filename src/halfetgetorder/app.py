import os, json, sys
from datetime import date, datetime
from .config import DATA_DIR
from . import godo, coupang
from .io_excel import (
    create_orders_workbook,   # ✅ 주문수집 엑셀 한 번에 만드는 헬퍼
    create_waybill_workbook,
    create_label_workbook,
)

today = date.today().strftime("%Y%m%d")

def _pause_before_exit():
    """
    PyInstaller로 빌드된 exe(콘솔)로 실행했을 때,
    작업이 끝난 뒤 바로 창이 닫히지 않도록 Enter 입력을 대기한다.
    개발 환경(파이썬 실행)에서는 불필요한 대기를 하지 않는다.
    """
    if getattr(sys, "frozen", False):
        try:
            input("\n[완료] 작업이 끝났습니다. 창을 닫으려면 Enter를 누르세요.")
        except Exception:
            pass


def _is_rental_order(od):
    """
    쿠팡 주문(od)이 '렌탈/대여/임대' 관련 주문인지 판단하는 함수.

    기준:
    - orderItems 안의 상품명들 중에
      '렌탈', '대여', '임대' 중 하나라도 포함되면 렌탈 주문으로 간주한다.
    - 상품명 후보:
      sellerProductName, sellerProductItemName, vendorItemName
    """
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


def main():
    try:
        # ─────────────────────────────────────────────
        # 1. 실행 간격 제한 (예: 2분)
        # ─────────────────────────────────────────────
        MIN_INTERVAL_MINUTES = 2  # 여기 숫자만 바꿔서 1분, 5분 등으로 조정 가능
        last_run_path = os.path.join(DATA_DIR, "godo_last_run.json")
        now = datetime.now()

        try:
            if os.path.exists(last_run_path):
                with open(last_run_path, "r", encoding="utf-8") as f:
                    info = json.load(f)
                last_ts = info.get("ts")
                if last_ts:
                    last_dt = datetime.fromisoformat(last_ts)
                    elapsed = (now - last_dt).total_seconds()

                    if elapsed < MIN_INTERVAL_MINUTES * 60:
                        remain = int(MIN_INTERVAL_MINUTES * 60 - elapsed)
                        print("⚠️ 고도몰 API 보호를 위해 너무 짧은 간격으로 실행하는 것을 막았습니다.")
                        print(f"   마지막 실행 시각 : {last_dt.strftime('%Y-%m-%d %H:%M:%S')}")
                        print(f"   최소 {MIN_INTERVAL_MINUTES}분 간격으로 실행해 주세요.")
                        print(f"   (약 {remain}초 후에 다시 실행 가능)")
                        return
        except Exception as e:
            # 방어용: 여기서 문제가 나도 프로그램 전체는 계속 돌도록
            print("⚠️ 실행 간격 확인 중 오류가 발생했지만, 프로그램은 계속 진행합니다:", e)

        # 2) 주문 데이터 조회 (API 직접 호출)
        cp_body = coupang.fetch_orders()
        godo_json = godo.fetch_orders()
        grouped = godo.group_sets(godo_json)

        # 고도몰 API까지 정상 호출되었다고 보고, 마지막 실행 시각 저장
        try:
            with open(last_run_path, "w", encoding="utf-8") as f:
                json.dump({"ts": now.isoformat()}, f)
        except Exception as e:
            print("⚠️ 마지막 실행 시각 저장 실패:", e)

        # 3) 쿠팡 주문 파싱 및 렌탈 주문 제외
        resp_json = {}
        filtered_orders = []
        filtered_cp_body = ""

        try:
            resp_json = json.loads(cp_body) if cp_body else {}
            orders = resp_json.get("data") or resp_json.get("content", []) or []

            # 🔽 렌탈/대여/임대 주문 제외
            filtered_orders = [od for od in orders if not _is_rental_order(od)]
            # 🔼 필터링된 주문만 엑셀/송장/라벨에 사용

            # 필터링된 주문만 포함하는 JSON 문자열을 만들어서
            # 대한통운 송장용 normalize_coupang_orders 에도 동일하게 적용
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
            print("⚠️ 쿠팡 JSON 파싱 또는 필터링 오류:", e)
            # 오류가 나도 이후 로직이 돌아가도록, cp_body 그대로 사용
            filtered_cp_body = cp_body or ""

        # 3-1) 주문수집 엑셀 생성 (쿠팡 + 고도몰)
        try:
            wb_orders, _ = create_orders_workbook(
                coupang_orders=filtered_orders,
                godo_grouped_orders=grouped,
            )
            order_xlsx = os.path.join(DATA_DIR, f"주문수집_{today}.xlsx")
            wb_orders.save(order_xlsx)
            print(f"✅ 엑셀 저장 완료: {order_xlsx}")
        except Exception as e:
            print("⚠️ 주문수집 엑셀 생성 중 오류:", e)

        # 4) 대한통운 송장등록 엑셀 생성 (쿠팡 주문만, 렌탈 제외된 상태)
        try:
            norm_cp_orders = (
                coupang.normalize_coupang_orders(filtered_cp_body)
                if filtered_cp_body
                else []
            )
        except Exception as e:
            print("⚠️ 쿠팡 송장용 정규화 오류:", e)
            norm_cp_orders = []

        if norm_cp_orders:
            wb1, _ = create_waybill_workbook(norm_cp_orders)
            waybill_xlsx = os.path.join(DATA_DIR, f"대한통운 송장등록_{today}.xlsx")
            wb1.save(waybill_xlsx)
            print(f"✅ 엑셀 저장 완료: {waybill_xlsx}")
        else:
            print("ℹ️ 쿠팡 주문이 없어 대한통운 송장등록 파일은 생성하지 않습니다.")

        print("=================================================================")
        print("[INFO] 라벨출력 엑셀파일을 생성하는 중입니다...")
        print("[INFO] 약 10~30초 정도 소요되니, 반응이 없다면 Enter키를 한번 눌러주세요.")

        # 5) 라벨 워크북 생성
        label_wb, _ = create_label_workbook(
            coupang_orders=filtered_orders,      # 쿠팡 주문 리스트(렌탈 제외)
            godo_grouped_orders=grouped,         # 고도몰 grouped_orders 리스트
            godo_add_goods_map_path=os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),  # 프로젝트 루트
                "godo_add_goods_all.json",
            ),
        )

        os.makedirs(DATA_DIR, exist_ok=True)
        label_path = os.path.join(DATA_DIR, f"라벨출력_{today}.xlsx")
        label_wb.save(label_path)

        print(f"✅ 라벨 엑셀 저장 완료: {label_path}")
    finally:
        _pause_before_exit()


if __name__ == "__main__":
    main()
