이 프로젝트는 Harness 프레임워크를 사용한다. 아래 워크플로우에 따라 작업을 진행하라.

---

## 워크플로우

### A. 탐색

`/docs/` 하위 문서(PRD, TECH_STACK, ARCHITECTURE, ADR 등)를 읽고 프로젝트의 기획·아키텍처·설계 의도를 파악한다. 필요시 Explore 에이전트를 병렬로 사용한다.

### A-1. 기술 스택 결정 (신규 기술 결정이 필요한 경우)

`docs/TECH_STACK.md`가 없거나 아직 템플릿(`{...}`) 상태이거나, 이번 작업이 기존 스택으로 커버되지 않는 새 요구사항(예: 기존 CRUD 서비스에 AI 챗봇 추가)을 포함하면, 구현 계획보다 먼저 기술 스택을 결정한다.

**사용자에게 Spring/FastAPI/React 같은 선택지를 직접 고르게 하지 않는다.** 사용자는 "무엇을 만들고 싶은지"만 말하고, 기술 선택은 아래 절차로 Agent가 수행한다.

1. PRD의 핵심 기능·MVP 범위를 근거로 후보를 2~3개 비교한다 (임의로 "가장 좋은 것"을 고르지 않는다).
2. `docs/TECH_STACK.md`의 "선정 기준" 표에서 이 프로젝트에 실제로 해당하는 기준(개발 속도/확장성/보안/생태계 등)을 선택하고 근거를 채운다.
3. 결정한 스택과 이유, 검토했던 대안을 `docs/TECH_STACK.md`에 기록한다.
4. 대응하는 결정을 `docs/ADR.md`에도 ADR 항목으로 남긴다 (TECH_STACK.md는 "무엇을/왜", ADR은 "트레이드오프"까지 포함).
5. 사용자에게는 기술 용어 나열이 아니라 선택 결과 + 이유 한두 줄만 요약해 전달한다. 예: "로그인·데이터 저장이 필요해 React + Next.js + PostgreSQL로 구성했습니다."
6. 이미 스택이 정해진 프로젝트에서 새 요구사항이 기존 스택 밖의 기술을 필요로 하면, TECH_STACK.md의 "재검토 트리거" 절에 따라 갱신하고 ADR에 변경 사유를 남긴다.

### B. 논의

구현을 위해 구체화하거나 기술적으로 결정해야 할 사항이 있으면 사용자에게 제시하고 논의한다.

### C. Step 설계

사용자가 구현 계획 작성을 지시하면 여러 step으로 나뉜 초안을 작성해 피드백을 요청한다.

설계 원칙:

1. **Scope 최소화** — 하나의 step에서 하나의 레이어 또는 모듈만 다룬다. 여러 모듈을 동시에 수정해야 하면 step을 쪼갠다.
2. **자기완결성** — 각 step 파일은 독립된 Claude 세션에서 실행된다. "이전 대화에서 논의한 바와 같이" 같은 외부 참조는 금지한다. 필요한 정보는 전부 파일 안에 적는다.
3. **사전 준비 강제** — 관련 문서 경로와 이전 step에서 생성/수정된 파일 경로를 명시한다. 세션이 코드를 읽고 맥락을 파악한 뒤 작업하도록 유도한다.
4. **시그니처 수준 지시** — 함수/클래스의 인터페이스만 제시하고 내부 구현은 에이전트 재량에 맡긴다. 단, 설계 의도에서 벗어나면 안 되는 핵심 규칙(멱등성, 보안, 데이터 무결성 등)은 반드시 명시한다.
5. **AC는 실행 가능한 커맨드** — "~가 동작해야 한다" 같은 추상적 서술이 아닌 `npm run build && npm test` 같은 실제 실행 가능한 검증 커맨드를 포함한다.
6. **주의사항은 구체적으로** — "조심해라" 대신 "X를 하지 마라. 이유: Y" 형식으로 적는다.
7. **네이밍** — step name은 kebab-case slug로, 해당 step의 핵심 모듈/작업을 한두 단어로 표현한다 (예: `project-setup`, `api-layer`, `auth-flow`).

### D. 파일 생성

사용자가 승인하면 아래 파일들을 생성한다.

#### D-1. `phases/index.json` (전체 현황)

여러 task를 관리하는 top-level 인덱스. 이미 존재하면 `phases` 배열에 새 항목을 추가한다.

```json
{
  "phases": [
    {
      "dir": "0-mvp",
      "status": "pending"
    }
  ]
}
```

- `dir`: task 디렉토리명.
- `status`: `"pending"` | `"completed"` | `"error"` | `"blocked"`. execute.py가 실행 중 자동으로 업데이트한다.
- 타임스탬프(`completed_at`, `failed_at`, `blocked_at`)는 execute.py가 상태 변경 시 자동 기록한다. 생성 시 넣지 않는다.

#### D-2. `phases/{task-name}/index.json` (task 상세)

```json
{
  "project": "<프로젝트명>",
  "phase": "<task-name>",
  "steps": [
    { "step": 0, "name": "project-setup", "status": "pending" },
    { "step": 1, "name": "core-types", "status": "pending" },
    { "step": 2, "name": "api-layer", "status": "pending" }
  ]
}
```

필드 규칙:

- `project`: 프로젝트명 (CLAUDE.md 참조).
- `phase`: task 이름. 디렉토리명과 일치시킨다.
- `steps[].step`: 0부터 시작하는 순번.
- `steps[].name`: kebab-case slug.
- `steps[].status`: 초기값은 모두 `"pending"`.

상태 전이와 자동 기록 필드:

| 전이 | 기록되는 필드 | 기록 주체 |
|------|-------------|----------|
| → `completed` | `completed_at`, `summary`, `evaluation` | Claude 세션 (summary, evaluation), execute.py (timestamp) |
| → `error` | `failed_at`, `error_message` | Claude 세션 (message), execute.py (timestamp) |
| → `blocked` | `blocked_at`, `blocked_reason` | Claude 세션 (reason), execute.py (timestamp) |

`summary`는 step 완료 시 산출물을 한 줄로 요약한 것으로, execute.py가 다음 step 프롬프트에 컨텍스트로 누적 전달한다. 따라서 다음 step에 유용한 정보(생성된 파일, 핵심 결정 등)를 담아야 한다.

`evaluation`은 step 완료 시 아래 5개 기준으로 자가 점검한 결과다. `/diagnose`가 이 필드들을 근거로 "어느 단계가 부족했는지"를 역추적하므로, 통과했다고 대충 채우지 말고 실제로 부족한 부분을 정직하게 남긴다.

```json
"evaluation": {
  "requirements_met": true,
  "runs_without_error": true,
  "error_handling": "partial",
  "test_coverage": "none",
  "notes": "비밀번호 검증 로직이 충분하지 않음 — 8자 미만만 체크"
}
```

| 필드 | 값 | 의미 |
|------|-----|------|
| `requirements_met` | boolean | 이 step에 명시된 요구사항을 전부 반영했는가 |
| `runs_without_error` | boolean | AC 커맨드가 에러 없이 통과했는가 |
| `error_handling` | `"ok"` \| `"partial"` \| `"none"` | 예외 상황(잘못된 입력, 실패 응답 등) 처리 수준 |
| `test_coverage` | `"ok"` \| `"partial"` \| `"none"` | 이 step 산출물에 대한 테스트 존재 여부/충분성 |
| `notes` | string | 부족한 부분에 대한 구체적 설명. 문제 없으면 빈 문자열 |

`created_at`은 execute.py가 최초 실행 시 task 레벨에 한 번만 기록한다. step 레벨의 `started_at`도 execute.py가 각 step 시작 시 자동 기록한다. 생성 시 넣지 않는다.

#### D-3. `phases/{task-name}/step{N}.md` (각 step마다 1개)

```markdown
# Step {N}: {이름}

## 읽어야 할 파일

먼저 아래 파일들을 읽고 프로젝트의 아키텍처와 설계 의도를 파악하라:

- `/docs/ARCHITECTURE.md`
- `/docs/ADR.md`
- {이전 step에서 생성/수정된 파일 경로}

이전 step에서 만들어진 코드를 꼼꼼히 읽고, 설계 의도를 이해한 뒤 작업하라.

## 작업

{구체적인 구현 지시. 파일 경로, 클래스/함수 시그니처, 로직 설명을 포함.
코드 스니펫은 인터페이스/시그니처 수준만 제시하고, 구현체는 에이전트에게 맡겨라.
단, 설계 의도에서 벗어나면 안 되는 핵심 규칙은 명확히 박아넣어라.}

## Acceptance Criteria

```bash
npm run build   # 컴파일 에러 없음
npm test        # 테스트 통과
```

## 검증 절차

1. 위 AC 커맨드를 실행한다.
2. 아키텍처 체크리스트를 확인한다:
   - ARCHITECTURE.md 디렉토리 구조를 따르는가?
   - ADR 기술 스택을 벗어나지 않았는가?
   - CLAUDE.md CRITICAL 규칙을 위반하지 않았는가?
3. 결과에 따라 `phases/{task-name}/index.json`의 해당 step을 업데이트한다:
   - 성공 → `"status": "completed"`, `"summary": "산출물 한 줄 요약"`, `"evaluation": {...}` (5개 기준 자가 점검, 하네스.md D-2 참고)
   - 수정 3회 시도 후에도 실패 → `"status": "error"`, `"error_message": "구체적 에러 내용"`
   - 사용자 개입 필요 (API 키, 외부 인증, 수동 설정 등) → `"status": "blocked"`, `"blocked_reason": "구체적 사유"` 후 즉시 중단

## 금지사항

- {이 step에서 하지 말아야 할 것. "X를 하지 마라. 이유: Y" 형식}
- 기존 테스트를 깨뜨리지 마라
```

### E. 실행

```bash
python3 scripts/execute.py {task-name}        # 순차 실행
python3 scripts/execute.py {task-name} --push  # 실행 후 push
```

execute.py가 자동으로 처리하는 것:

- `feat-{task-name}` 브랜치 생성/checkout
- 가드레일 주입 — CLAUDE.md + docs/*.md 내용을 매 step 프롬프트에 포함
- 컨텍스트 누적 — 완료된 step의 summary를 다음 step 프롬프트에 전달
- 자가 교정 — 실패 시 최대 3회 재시도하며, 이전 에러 메시지를 프롬프트에 피드백
- 2단계 커밋 — 코드 변경(`feat`)과 메타데이터(`chore`)를 분리 커밋
- 타임스탬프 — started_at, completed_at, failed_at, blocked_at 자동 기록

에러 복구:

- **error 발생 시**: `phases/{task-name}/index.json`에서 해당 step의 `status`를 `"pending"`으로 바꾸고 `error_message`를 삭제한 뒤 재실행한다.
- **blocked 발생 시**: `blocked_reason`에 적힌 사유를 해결한 뒤, `status`를 `"pending"`으로 바꾸고 `blocked_reason`을 삭제한 뒤 재실행한다.

### F. 진단 (비개발자를 위한 원인 추적)

execute.py는 실행이 끝날 때마다 `reports/{task-name}/execution.json`에 각 step의 상태·시각을 기계적으로 집계한다 (판단 없이 사실만 기록).

phase 실행 중 하나라도 `error`/`blocked`가 발생했거나, `completed`된 step의 `evaluation`에 `"partial"`/`"none"`/비어있지 않은 `notes`가 있다면 `/diagnose {task-name}`을 실행한다.

`/diagnose`는 이 실행을 만든 세션과 **별도의 세션**에서 실행되어야 한다 — 구현자가 자기 결과물을 스스로 채점하지 않는다는 원칙 때문이다. `reports/{task-name}/evaluation.json`(구조화된 평가)과 `reports/{task-name}/final-report.md`(비개발자용 요약: 🟢/🟡/🔴 상태, 문제가 시작된 step, 원인, 권장 조치)를 생성한다. 자세한 절차는 `.claude/commands/diagnose.md` 참고.
