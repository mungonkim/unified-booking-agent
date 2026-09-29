# 아키텍처

## 디렉토리 구조
```
./
├── main.py            # 메인 애플리케이션 (자연어 질의 + 레거시 CLI 메뉴)
├── booking_engine.py  # 예약 셀렉터/캘린더 핵심 로직 (.gitignore 처리, 로컬 전용)
├── .env               # ANTHROPIC_API_KEY 등 시크릿 (커밋 금지)
├── user_data/         # Playwright persistent context 프로필 (네이버 로그인 세션 유지)
├── debug/             # 마크업 인식 실패 시 자동 저장되는 진단용 HTML/스크린샷 (.gitignore 처리)
├── recommend_cache.json  # 장소 추천 후보 캐시, (지역,업종) 키 + 24시간 TTL (.gitignore 처리, ADR-010)
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
                     반환은 (times, status) — status="unknown_markup"이면 "마감"이 아니라 마크업을
                     인식 못한 것 → _save_debug_artifacts()가 debug/ 에 HTML/스크린샷 자동 저장 (ADR-005)

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

## 장소 추천 (설계 확정, 구현 전 — 상세 원칙은 docs/PRD.md, 결정 배경은 ADR-006·ADR-009 참고)
```
후보 수집 로직은 "네이버 지도 검색 결과를 어떻게 파싱하는지"에 대한 노하우이므로
booking_engine.py와 동일하게 로컬 전용(.gitignore) 코드로 둔다 — 별도 파일(예: recommend_engine.py)로
분리하되 공개 저장소에는 올리지 않는다. 랭킹/판단은 수식이 아니라 parse_natural_query()와
동일한 패턴(Claude tool-use)으로 처리한다(ADR-009) — 코드는 사실 수집까지만 담당.

사실 수집 (코드, recommend_engine.py)
  캐시 조회        (지역, 업종) 키로 recommend_cache.json 확인 → 24시간 이내면 그대로 재사용 (ADR-010)
  후보 수집        캐시 미스일 때만: 지역+업종 키워드로 네이버 지도 검색 → 이름/카테고리/평점/리뷰수/좌표·주소
  리뷰 샘플 수집    상위 후보(예: 8개)만 개별 페이지에서 최신 리뷰 10~20개의 작성일 조회
                   (전체 후보를 다 깊게 스크래핑하지 않도록 저렴한 필터 → 정밀 조회 2단계)
                   수집한 결과는 캐시에 기록

판단 (Claude tool-use, main.py 자연어 레이어에서 호출)
  입력             위 사실 데이터 + PRD.md에 문서화된 판단 원칙(리뷰 적음 투명하게 알리기,
                   업종별 상대적 판단, 리뷰 이벤트성 몰림 의심, 거리는 언급된 지역 기준,
                   검증됨/신상 구분, 이유 명시)
  출력             구조화된 추천 목록 (검증됨 3~5개 + 신상, 각 항목에 이유 포함)
```
