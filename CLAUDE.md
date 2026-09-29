# 프로젝트: 통합 예약 에이전트

네이버 예약/캐치테이블 등 여러 플랫폼의 예약 가능 시간을 통합 조회하고, 결제 없는 예약은 자동 진행, 결제 필요 시 사용자 직접 결제로 안내, 조건 기반 장소 추천까지 제공하는 개인용 에이전트. 현재는 네이버 예약 조회 기능만 구현되어 있다 (README 체크리스트 참고).

## 기술 스택
- Python 3 (asyncio)
- Playwright (async_playwright, Chromium, `launch_persistent_context`로 세션 유지)
- Anthropic Python SDK (`anthropic.AsyncAnthropic`) — 자연어 질의 파싱 (`claude-haiku-4-5-20251001`)
- python-dotenv (.env에서 `ANTHROPIC_API_KEY` 로드)
- 패키지 관리: `uv` (venv는 `.venv`, pip 없이 `uv pip install --python .venv/Scripts/python.exe <pkg>`로 설치)

## 아키텍처 규칙
- CRITICAL: 브라우저 자동화 로직(Playwright 셀렉터/클릭/대기)은 `input()` 등 CLI 입력에 의존하지 않는다. `interactive` 플래그로 분리해 자연어 질의 흐름에서도 그대로 재사용 가능해야 한다.
- CRITICAL: 업종(식당/미용실/병원/스튜디오 등)마다 페이지 마크업이 다르다는 전제를 유지한다 — 특정 업종에만 맞는 셀렉터를 하드코딩하지 말고, 신형/구형 마크업을 감지해 분기하는 패턴(`_select_date_grid_v2` vs `_select_date_legacy` 등)을 따른다.
- CRITICAL: 실제 페이지 구조가 불확실하면 추측으로 셀렉터를 만들지 말고, 사용자에게 개발자 도구 HTML을 요청한다.
- `.inner_text()`/`.click()` 등 Playwright 액션 호출 시 기본 30000ms 타임아웃을 그대로 두지 말고 항상 짧은 `timeout=`을 명시한다 (`_safe_inner_text` 패턴 참고).
- `asyncio.wait(..., return_when=FIRST_COMPLETED)` + `task.cancel()`로 Playwright 작업을 레이싱하지 않는다 — 취소 처리가 불안정해 오히려 긴 hang을 유발한 전례가 있다. 폴링 루프(`while` + 짧은 sleep)를 사용한다.
- API 키(`ANTHROPIC_API_KEY`) 등 민감 정보는 `.env`에만 두고 코드/커밋에 노출하지 않는다.
- CRITICAL: 예약 플랫폼별 실제 셀렉터/마크업 대응 로직(현재 `booking_engine.py`, 향후 캐치테이블 등 추가 시 그 어댑터 코드도 동일)은 원격 저장소에 올리지 않는다. `.gitignore`에 등록하고, `main.py`(공개되는 자연어/CLI 레이어)는 그 모듈을 import해서 호출만 한다.

## 개발 프로세스
- 이 프로젝트는 개인용 단일 사용자 도구다. 멀티 유저/동시성 확장은 지금 단계에서 설계하지 않는다 (탭당 캐싱 등 미리 최적화하지 않음).
- 성능 이슈는 추측하지 말고 `_mark()`류 타이밍 로그로 실측한 뒤 병목만 고친다.
- 새 업종/페이지 레이아웃 대응이 필요하면 실제 HTML을 받아서 셀렉터를 작성한다.

## 명령어

```
.\.venv\Scripts\python.exe main.py           # 자연어 질의 모드 (기본)
.\.venv\Scripts\python.exe main.py --menu    # 기존 CLI 메뉴 모드
python -m py_compile main.py                 # 문법 체크
```
