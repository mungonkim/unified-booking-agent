# 아키텍처

## 디렉토리 구조
```
./
├── main.py            # 메인 애플리케이션 (자연어 질의 + 레거시 CLI 메뉴)
├── booking_engine.py  # 예약 셀렉터/캘린더 핵심 로직 (.gitignore 처리, 로컬 전용)
├── .env               # ANTHROPIC_API_KEY 등 시크릿 (커밋 금지)
├── user_data/         # Playwright persistent context 프로필 (네이버 로그인 세션 유지)
├── docs/              # PRD/TECH_STACK/ARCHITECTURE/ADR
├── .claude/           # harness 커맨드/훅 설정
├── scripts/           # harness 실행 엔진 (execute.py) — 이 프로젝트 자체 기능과는 별개
├── phases/            # (harness가 생성) 기능 단위 step 계획
└── reports/           # (harness가 생성) 실행/진단 결과
```

## 계층 분리 (main.py ↔ booking_engine.py)
```
main.py (공개 저장소에 올라가는 부분)
  자연어 레이어      parse_natural_query() → Claude tool-use로 {place, target, people, mode, day} 추출
                     run_natural_query() → 세션(session_key/entry_iframe) 유지, 후속 질문 재사용
  CLI 레이어         run_checker() (레거시 메뉴), _format_query_result()
  → booking_engine의 query_place()/enter_booking_calendar() 등을 import해서 호출만 한다.

booking_engine.py (.gitignore 처리, 로컬 전용 — 실제 셀렉터/마크업 대응 노하우)
  오케스트레이션      enter_booking_calendar() → 검색~예약 진입까지 네비게이션
                     query_place() → 진입 후 날짜/시간 조회, entry_iframe 재사용 지원

  선택 로직          select_search_result() / select_booking_target()
                     → 신형/구형/디자이너/서비스카드/li-fallback 등 마크업별 분기

  캘린더 로직        select_date_on_calendar() → _select_date_grid_v2 / _select_date_legacy 분기
                     find_earliest_available() / check_specific_day()

  시간 슬롯 로직      get_available_times_from_page() → 신형(button.btn_time)/구형(span[_label_]) 분기, 재시도 포함

  공용 유틸          _safe_inner_text() (타임아웃 가드), _mark() (타이밍 로그), _place_url_cache (URL 캐시)
```

## 데이터 흐름
```
사용자 자연어 입력
  → parse_natural_query() (Claude API, 이전 맥락 고려)
  → query_place()/enter_booking_calendar() (Playwright, 캐시된 URL/entry_iframe 있으면 재사용)
  → 검색결과 소거 → 예약 상세 진입 → (필요시 인원/담당자 선택) → 날짜 선택 → 시간 슬롯 읽기
  → _format_query_result() (자연어 한 줄 답변)
  → 터미널 출력, session_key/entry_iframe는 다음 턴을 위해 유지
```

## 상태 관리
- 프로세스 내 인메모리 상태만 사용 (DB 없음): `_place_url_cache` (place→URL), `run_natural_query()`의 `session_key`/`session_entry_iframe` (같은 장소·항목 후속 질문 재사용), `previous_context` (자연어 후속 질문 맥락)
- 브라우저 로그인 세션은 `user_data/` 디렉토리(Playwright persistent context)에 영속화됨
