이 프로젝트에서 실행된 phase/task를 진단하고, 비개발자도 이해할 수 있는 원인 추적 리포트를 생성하라.

사용법: `/diagnose {task-name}` (예: `/diagnose 0-mvp`)

**중요**: 이 커맨드는 해당 task를 구현한 세션과 다른 세션에서 실행되어야 한다. 구현자가 자기 결과물을 스스로 평가하지 않는다는 원칙 때문이다 — 이미 구현에 몰입한 컨텍스트에서는 자기 코드의 문제를 발견하기 어렵다. 새 세션에서 아래 절차만으로 판단하라.

## 1. 원본 데이터 수집

다음 파일을 읽는다. 요약이나 기억에 의존하지 말고 실제 파일을 읽는다.

- `phases/{task-name}/index.json` — 각 step의 `status`, `summary`, `evaluation`, `error_message`, `blocked_reason`
- `reports/{task-name}/execution.json` — execute.py가 기계적으로 집계한 시각/상태 (있으면)
- `docs/PRD.md`, `docs/TECH_STACK.md`, `docs/ARCHITECTURE.md`, `docs/ADR.md` — 이 step이 원래 무엇을 요구했는지 대조하기 위함
- 필요시 `phases/{task-name}/step{N}.md`(원래 지시 내용)와 실제 산출 코드를 비교

## 2. 각 step을 3단계 신호등으로 판정

점수(82점 등)를 매기지 않는다. 비개발자는 "82점이면 좋은 건가?"에서 다시 막힌다. 대신 행동으로 연결되는 신호등을 쓴다.

- 🟢 **정상**: `status: completed`이고 `evaluation`의 모든 항목이 통과 수준
- 🟡 **확인 필요**: `completed`이지만 `evaluation`에 `"partial"`이나 `notes`가 있음
- 🔴 **수정 필요**: `status: error` 또는 `blocked`, 또는 `evaluation`에 `"none"`이 있음

## 3. 원인을 발생 지점이 아니라 근본 원인까지 역추적

문제가 드러난 step(예: 테스트/검증 단계)과 문제가 실제로 생겨난 step(예: 요구사항이 불명확했던 기획 단계)은 다를 수 있다. 아래처럼 역방향으로 추적한다.

1. 어느 step에서 문제가 "발견"됐는가? (`error`/`blocked`/`evaluation` 부족이 기록된 step)
2. 그 문제가 이전 step의 산출물(`summary`) 또는 문서(PRD/TECH_STACK/ARCHITECTURE)의 누락·모호함 때문인가, 아니면 해당 step 자체의 구현 실수인가?
3. 근본 원인이 더 이전 문서/step에 있다면 거기까지 거슬러 올라가 명시한다.

예: "로그인 테스트 실패" → 원인 분석 → "비밀번호 규칙이 PRD/step 지시에 구체적으로 정의되지 않았음" → 근본 원인은 기획 단계.

## 4. `reports/{task-name}/evaluation.json` 작성

```json
{
  "task": "{task-name}",
  "generated_at": "<ISO8601 KST>",
  "overall_status": "green | yellow | red",
  "steps": [
    {
      "step": 0,
      "name": "...",
      "status": "green | yellow | red",
      "issue": "무엇이 문제인가 (문제 없으면 생략)",
      "root_cause_step": "문제가 실제로 시작된 step 번호/이름 (해당 step 자체가 원인이면 자기 자신)",
      "root_cause": "근본 원인 한두 문장",
      "recommendation": "무엇을 수정해야 하는가"
    }
  ],
  "top_priority": "가장 먼저 확인해야 할 step 이름과 이유"
}
```

## 5. `reports/{task-name}/final-report.md` 작성 (비개발자용)

기술 용어를 최소화하고, "무엇을 확인해야 하는가"로 끝나도록 쓴다. 아래 형식을 따른다.

```markdown
# 실행 결과 진단 — {task-name}

전체 상태: 🟢 정상 | 🟡 확인 필요 | 🔴 수정 필요

## 단계별 결과

① {step 이름}
{🟢/🟡/🔴}

{한두 줄 설명. 통과했으면 "정상 반영됨" 정도로 짧게, 문제 있으면 구체적으로}

② {다음 step}
...

## 가장 먼저 확인할 부분

🔴 {step 이름}

이유: {구체적 사유}

## 원인 분석

{step A}에서 발견된 문제는 사실 {step B}의 {구체적 누락/모호함} 때문입니다.

## 권장 조치

{어느 step을 다시 실행해야 하는지, 어느 문서를 먼저 보완해야 하는지}
```

## 6. 재실행 안내

`recommendation`이 특정 step의 재구현이면, 사용자에게 다음을 안내한다:

```
phases/{task-name}/index.json 에서 step {N}의 status를 "pending"으로 되돌리고
{보완이 필요한 부분}을 step{N}.md에 반영한 뒤 재실행하세요:

python3 scripts/execute.py {task-name}
```

문서(PRD/TECH_STACK/ARCHITECTURE) 자체의 누락이 근본 원인이면, 코드 재실행보다 해당 문서를 먼저 보완하라고 안내한다.
