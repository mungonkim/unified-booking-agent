#!/usr/bin/env bash
# 위험한 명령어(강제 삭제, force push, DB 전체 삭제 등)를 차단하는 PreToolUse 훅.
# settings.json에서 Bash 툴 호출 시마다 실행된다.

if echo "$CLAUDE_TOOL_INPUT" | grep -qE 'rm\s+-rf|git\s+push\s+--force|git\s+reset\s+--hard|DROP\s+TABLE'; then
  echo "BLOCKED: 위험한 명령어가 감지되었습니다." >&2
  exit 1
fi
