# 하프전자 주문수집기 v2

고도몰·쿠팡 주문을 API로 수집해 **엑셀 3종**을 자동 생성하는 Windows 전용 프로그램입니다.

| 생성 파일 | 설명 |
|-----------|------|
| `주문수집_YYYYMMDD.xlsx` | 쿠팡 + 고도몰 주문 내역 |
| `대한통운 송장등록_YYYYMMDD.xlsx` | 쿠팡 주문이 있을 때만 생성 |
| `라벨출력_YYYYMMDD.xlsx` | 라벨 출력용 (생성에 10~30초 소요될 수 있음) |

출력 위치: 사용자가 지정한 **상위 폴더** 아래 `하프전자 주문수집기` 폴더 (기본: 바탕화면)

---

## v2 주요 변경

- **CustomTkinter GUI** — 설치 / 빌드 / 설정 3탭
- **API 키를 exe에 포함하지 않음** — `%APPDATA%\HalfetGetOrder`에 암호화 저장
- **관리자 비밀번호** — API 키 변경 시 확인, 빌드(파일 생성)는 비밀번호 불필요
- **설치 1회 후** 설치 탭 잠금, 빌드 탭에서 반복 실행

---

## 화면 구성

| 탭 | 역할 |
|----|------|
| **설치** | 최초 1회: 관리자 비밀번호 → 출력 폴더 → API 키 4종 → 설치 완료 |
| **빌드** | 「파일 생성」— 주문 조회 후 엑셀 3종 저장 (로그·진행률 표시) |
| **설정** | API 키 관리(개별 변경), 연결 복구, 출력 경로·비밀번호 변경 |

개발 환경(소스 실행)에서는 설치 탭에 **환경 준비**(venv·pip) 단계가 추가로 표시됩니다.

---

## 보안

- API 키 4종: 쿠팡 ACCESS/SECRET, 고도몰 PARTNER/GODO
- 저장 위치: `%APPDATA%\HalfetGetOrder\`
  - `admin.json` — 관리자 비밀번호(bcrypt) + 마스터 키 wrap
  - `keys.enc` — Fernet 암호화 API 키
  - `keys.local` / `runtime.key` — 이 PC 전용(DPAPI, 빌드용)
  - `setup.json` — 출력 경로, 설치 완료 여부
- 비밀번호 분실 시: 설정 탭 **비밀번호 재설정** → API 키 재입력 필요

---

## 실무자 (exe 배포)

1. 배포받은 **exe 1개** 실행
2. **설치** 탭에서 비밀번호·출력 폴더·API 키 설정 후 「설치 완료」
3. **빌드** 탭 → 「파일 생성」
4. `하프전자 주문수집기` 폴더에서 엑셀 확인

> exe 빌드는 개발자가 `build.bat` 또는 PyInstaller로 생성합니다. (아래 참고)

---

## 개발자 (소스 실행)

### 요구 사항

- Windows 10 이상
- Python 3.10+ 권장

### 설치

```powershell
cd HalfetGetOrder_v2
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 실행

```powershell
.\.venv\Scripts\activate
python entry.py
```

GUI **설치** 탭에서 환경 준비(venv·의존성)를 진행하거나, 위 명령으로 직접 설치해도 됩니다.

### 개발용 API 키 (선택)

실무 배포에는 사용하지 않습니다. 로컬 개발 시에만:

- `.env` — `.env.example`을 복사해 `CP_ACCESSKEY`, `CP_SECRETKEY`, `PARTNER_KEY`, `GODO_KEY` 입력
- 또는 `src/halfetgetorder/keys.py` (Git에 올리지 말 것)

설치·설정 탭에서 키를 저장하면 APPDATA 방식이 우선합니다.

### exe 빌드

```powershell
.\build.bat
```

메뉴에서 **1. 프로그램 빌드** 선택. 또는:

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --onefile --name HalfetGetOrder --icon=icon/app.ico entry.py
```

빌드 결과는 `dist\HalfetGetOrder.exe` (또는 `build.bat` 안내 경로)입니다.

---

## 프로젝트 구조

```
HalfetGetOrder_v2/
├── entry.py                 # GUI 진입점
├── requirements.txt
├── build.bat                # 개발자용: exe 빌드·키 변경 메뉴
├── godo_goods_all.json      # 고도몰 상품 캐시(레거시, 당분간 유지)
├── icon/app.ico
└── src/halfetgetorder/
    ├── app.py               # CLI fallback
    ├── runner.py            # 엑셀 3종 생성 로직
    ├── config.py
    ├── coupang.py / godo.py / io_excel.py
    ├── security/            # 암호화·APPDATA 저장
    │   ├── crypto.py
    │   ├── dpapi.py
    │   └── store.py
    └── ui/                  # CustomTkinter
        ├── app_window.py
        ├── install_tab.py
        ├── build_tab.py
        ├── settings_tab.py
        └── ...
```

---

## 자주 묻는 문제

| 증상 | 조치 |
|------|------|
| 쿠팡 주문이 안 나옴 / 401 | Wing에서 키·IP 확인. 설정 탭에서 API 키 재저장 |
| 빌드 시 키 로드 실패 | 설정 → **API 키 연결 복구** (비밀번호만 입력) |
| `Permission denied` 저장 오류 | 해당 날짜 엑셀 파일을 **Excel에서 닫고** 다시 「파일 생성」 |
| 고도몰 2분 제한 | 마지막 실행 후 2분 대기 후 재시도 |
| 고도몰 API 호출 후 | `godo_last_run.json`으로 간격 제한 |

---

## 비즈니스 규칙

- 쿠팡: 상품명에 `렌탈` / `대여` / `임대` 포함 주문 제외
- 고도몰: API 호출 후 **2분 이내** 재실행 차단

---

## 라이선스 / 저장소

내부 업무용 프로젝트입니다. 상세 스펙은 Notion 「하프전자 주문수집기 v2 — 개발 스펙」을 참고하세요.
