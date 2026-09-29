#!/usr/bin/env bash
# 서킷 브레이커: 동일한 Bash 명령어를 반복 실행하는 패턴을 감지해 차단한다.
# 목적: 같은 실패를 자가 교정 없이 계속 재시도하는 루프를 끊는 것.
#
# 한계: PreToolUse 시점에는 이전 실행의 성공/실패 여부를 알 수 없으므로,
# "정확히 같은 명령어가 짧은 시간 안에 N회 이상 반복됐는가"만 본다. 정상적으로
# 반복 실행되는 명령(npm test 등)까지 막지 않도록 임계값을 넉넉히(5회) 잡고,
# 마지막 실행으로부터 일정 시간이 지나면 카운트를 리셋한다.

THRESHOLD=5
RESET_AFTER_SECONDS=600
STATE_DIR="${CLAUDE_PROJECT_DIR:-.}/.claude/.circuit-breaker"
mkdir -p "$STATE_DIR" 2>/dev/null

CMD=$(echo "$CLAUDE_TOOL_INPUT" | grep -oE '"command"[[:space:]]*:[[:space:]]*"[^"]+"' | head -1 | sed -E 's/.*:[[:space:]]*"(.*)"/\1/')
[ -z "$CMD" ] && exit 0

HASH=$(echo -n "$CMD" | md5sum | cut -d' ' -f1)
STATE_FILE="$STATE_DIR/$HASH"

NOW=$(date +%s)
COUNT=0
if [ -f "$STATE_FILE" ]; then
  LAST_TS=$(cut -d' ' -f1 "$STATE_FILE" 2>/dev/null)
  LAST_COUNT=$(cut -d' ' -f2 "$STATE_FILE" 2>/dev/null)
  if [ -n "$LAST_TS" ] && [ $((NOW - LAST_TS)) -le "$RESET_AFTER_SECONDS" ]; then
    COUNT="${LAST_COUNT:-0}"
  fi
fi
COUNT=$((COUNT + 1))
echo "$NOW $COUNT" > "$STATE_FILE"

if [ "$COUNT" -ge "$THRESHOLD" ]; then
  echo "BLOCKED: 동일한 명령어를 ${COUNT}회 반복 실행했습니다. 같은 방식으로 계속 재시도하지 말고, 원인을 다시 분석하거나 해당 step을 'blocked'/'error'로 표시하세요." >&2
  exit 1
fi
