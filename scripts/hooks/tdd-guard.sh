#!/usr/bin/env bash
# TDD 가드: 테스트 파일이 하나도 없는 구현 파일을 새로 작성/수정하려 하면 막는다.
# 근거: CLAUDE.md 개발 프로세스 규칙 — "새 기능 구현 시 반드시 테스트를 먼저 작성"
#
# 이 프로젝트는 src/app/lib 같은 계층 디렉토리 없이 루트에 .py 파일을 두는 구조라,
# 원본(my-harness) 버전의 디렉토리 기반 판별 대신 "루트의 .py 구현 파일"을 대상으로 한다.
#
# 한계: 완벽한 TDD 강제(테스트를 실제로 먼저 실행해봤는지)는 훅만으로 검증할 수
# 없다. 여기서는 "같은 이름의 테스트 파일이 저장소 어딘가에 존재하는가"만 확인하는
# 가벼운 휴리스틱이다. 테스트 파일 자체, 문서, 설정 파일, scripts/는 대상에서 제외한다.

FILE_PATH=$(echo "$CLAUDE_TOOL_INPUT" | grep -oE '"file_path"[[:space:]]*:[[:space:]]*"[^"]+"' | head -1 | sed -E 's/.*:[[:space:]]*"(.*)"/\1/')

[ -z "$FILE_PATH" ] && exit 0

# 대상 확장자가 아니면 통과
case "$FILE_PATH" in
  *.py) ;;
  *) exit 0 ;;
esac

# 테스트 파일 자체는 통과
case "$FILE_PATH" in
  *test_*|*_test.py|*/tests/*) exit 0 ;;
esac

# scripts/(하네스 엔진 자체)는 TDD 대상 아님 — scripts/test_execute.py가 이미 커버
case "$FILE_PATH" in
  */scripts/*|scripts/*) exit 0 ;;
esac

BASE=$(basename "$FILE_PATH")
NAME="${BASE%.*}"

if ! find . -type f \( -iname "test_${NAME}.py" -o -iname "${NAME}_test.py" \) 2>/dev/null | grep -q .; then
  echo "BLOCKED: '${BASE}'에 대한 테스트 파일을 찾지 못했습니다. TDD 규칙(CLAUDE.md)에 따라 테스트를 먼저 작성하세요." >&2
  exit 1
fi
