# reports/

`phases/{task-name}`를 실행/진단한 결과가 task별로 이 아래 쌓인다: `reports/{task-name}/`.

| 파일 | 생성 주체 | 내용 |
|------|-----------|------|
| `execution.json` | `scripts/execute.py` (기계적 집계) | 각 step의 상태·시각을 판단 없이 그대로 기록 |
| `evaluation.json` | `/diagnose` (별도 세션의 판단) | step별 🟢/🟡/🔴 판정, 근본 원인, 권장 조치 (구조화) |
| `final-report.md` | `/diagnose` | 위 내용을 비개발자가 읽을 수 있는 형태로 요약 |

`execution.json`은 "무슨 일이 있었는지"만 담고, `evaluation.json`/`final-report.md`는 "그게 괜찮은지, 어디가 문제인지"를 담는다 — 이 둘을 분리하는 이유는 구현자가 자기 결과물을 스스로 채점하지 않도록 하기 위함이다. 자세한 절차는 `.claude/commands/diagnose.md` 참고.

이 디렉토리의 내용물(`{task-name}/` 하위)은 실행 결과물이므로 버전 관리 대상이 아니다.
