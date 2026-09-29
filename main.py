import asyncio
import os
import sys
from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from playwright.async_api import async_playwright

from booking_engine import (
    query_place,
    enter_booking_calendar,
    find_earliest_available,
    check_specific_day,
)

load_dotenv()

_QUERY_EXTRACTION_TOOL = {
    "name": "extract_reservation_query",
    "description": "사용자의 자연어 예약 조회 질문에서 구조화된 조회 조건을 추출한다",
    "input_schema": {
        "type": "object",
        "properties": {
            "place_name": {"type": "string", "description": "조회할 매장/식당/미용실/병원 이름"},
            "target_name": {
                "type": ["string", "null"],
                "description": (
                    "예약 전에 여러 선택지(담당자, 룸, 서비스, 메뉴, 코스 등 업종 불문하고 무엇이든) 중 "
                    "사용자가 콕 집어 언급한 게 있으면 그 단어/이름을 그대로 적는다. "
                    "특별히 지목한 게 없으면 null."
                ),
            },
            "people": {
                "type": ["integer", "null"],
                "description": "방문 인원 수가 언급되었으면 그 숫자, 언급 없으면 null",
            },
            "mode": {
                "type": "string",
                "enum": ["earliest", "specific_day"],
                "description": "특정 날짜(예: '24일')를 콕 집어 물었으면 specific_day, '가장 빠른 날짜/시간'을 물었으면 earliest",
            },
            "specific_day": {
                "type": ["integer", "null"],
                "description": "mode가 specific_day일 때 그 '일(day)' 숫자, 아니면 null",
            },
        },
        "required": ["place_name", "mode"],
    },
}

async def parse_natural_query(user_text: str, previous_context: dict = None) -> dict:
    """자연어 질문을 Claude API로 파싱해 구조화된 조회 조건 dict로 변환

    previous_context가 주어지면(직전 조회의 place_name/target_name/people) "30일은?" 같이
    장소를 다시 언급하지 않는 후속 질문에서도 이전 맥락을 이어받아 채우도록 안내한다.
    반환 키: place_name, target_name, people, mode, specific_day (실패 시 "error" 키만 포함)
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {"error": "ANTHROPIC_API_KEY 환경변수가 설정되어 있지 않습니다."}

    client = AsyncAnthropic(api_key=api_key)

    user_content = user_text
    if previous_context:
        context_note = (
            f"[이전 조회 맥락] 장소: {previous_context.get('place_name')}, "
            f"담당자: {previous_context.get('target_name')}, 인원: {previous_context.get('people')}\n"
            f"새 질문: {user_text}"
        )
        user_content = context_note

    try:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=(
                "사용자의 예약 조회 질문에서 조회 조건을 추출한다. "
                "새 질문에 매장/식당/미용실/병원 등 장소로 해석될 만한 이름이 하나라도 등장하면, "
                "그것이 이전 맥락의 장소와 다르더라도 무조건 새로운 place_name으로 쓰고 "
                "target_name/people 등 나머지 값은 이전 맥락을 이어가지 않고 새로 판단한다. "
                "새 질문이 장소 언급 없이 날짜/항목 등 세부사항만 이야기할 때만 "
                "이전 맥락의 place_name(및 언급 안 된 다른 값)을 그대로 재사용한다."
            ),
            tools=[_QUERY_EXTRACTION_TOOL],
            tool_choice={"type": "tool", "name": "extract_reservation_query"},
            messages=[{"role": "user", "content": user_content}],
        )
    except Exception as e:
        return {"error": f"AI 파싱 중 오류: {e}"}

    for block in response.content:
        if block.type == "tool_use":
            return block.input

    return {"error": "질문에서 필요한 정보를 추출하지 못했습니다."}

async def run_checker():
    user_data_path = os.path.join(os.getcwd(), "user_data")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_path,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ignore_https_errors=True
        )
        page = context.pages[0] if context.pages else await context.new_page()

        print("\n🤖 [네이버 예약 가능 시간 조회 AI 에이전트 실행]")

        while True:
            restaurant_name = input("\n📍 탐색할 식당 이름을 입력하세요 (종료하려면 'q' 입력): ").strip()
            if restaurant_name.lower() in ['q', 'exit', 'quit']:
                print("에이전트를 종료합니다. 이용해 주셔서 감사합니다!")
                break

            people_input = input("👥 방문 인원 수가 있다면 입력하세요 (인원 선택이 없는 업종이면 Enter): ").strip()
            target_people = int(people_input) if people_input.isdigit() else None

            target_name_input = input("💇 담당자/디자이너 이름이 있다면 입력하세요 (없으면 Enter): ").strip()
            target_name = target_name_input or None

            print(f"\n🔍 '{restaurant_name}' 검색 및 예약 페이지 진입 중...")
            try:
                # 🔑 페이지가 닫혔거나 비정상 상태면 새 페이지 할당
                if page.is_closed():
                    page = await context.new_page()

                entry_iframe = await enter_booking_calendar(
                    page, restaurant_name, people=target_people, target_name=target_name, interactive=True
                )

                # 🔄 동일 식당 내 탐색 모드 무한 루프
                while True:
                    print(f"\n==================================================")
                    people_label = f"{target_people}명" if target_people is not None else "인원 미지정"
                    print(f"🏠 현재 식당: [ {restaurant_name} ] ({people_label})")
                    print("1. 가장 빠른 예약 가능 날짜 자동 탐색")
                    print("2. 특정 날짜 지정하여 예약 시간 조회")
                    print("3. 다른 식당 검색하기")
                    print("0. 프로그램 종료")
                    print("==================================================")
                    menu = input("👉 원하시는 메뉴 번호를 선택하세요: ").strip()

                    if menu == '1':
                        print(f"\n⚡ 오늘부터 순회하며 가장 빠른 예약 일시 탐색 중...")
                        target_date, available_times, status = await find_earliest_available(entry_iframe)

                        if status == "unknown_markup":
                            print("\n--------------------------------------------------")
                            print("⚠️ 페이지 마크업을 인식하지 못했습니다 (사이트 구조가 바뀌었을 수 있음).")
                            print("   debug/ 폴더에 저장된 HTML/스크린샷을 확인해 주세요.")
                            print("--------------------------------------------------")
                        elif target_date:
                            print("\n--------------------------------------------------")
                            print(f"🎉 가장 빠른 예약 가능 날짜 발견!")
                            print(f"📅 날짜: {target_date.strftime('%Y년 %m월 %d일 (%a)')}")
                            print(f"⏰ 가능 시간({len(available_times)}개): {', '.join(available_times)}")
                            print("--------------------------------------------------")
                        else:
                            print("😭 향후 30일 이내에 예약 가능한 날짜가 없습니다 (모두 휴무 또는 마감).")

                    elif menu == '2':
                        raw_day = input("\n📅 조회하고 싶은 '일(Day)'을 입력하세요 (ex: 25): ").strip()
                        if not raw_day.isdigit():
                            print("❌ 숫자 형식으로 입력해 주세요.")
                            continue

                        target_day = int(raw_day)
                        available_times, status = await check_specific_day(entry_iframe, target_day)

                        print("\n--------------------------------------------------")
                        if status == "success":
                            print(f"✅ {target_day}일 예약 가능 시간({len(available_times)}개):")
                            print(f"⏰ {', '.join(available_times)}")
                        elif status == "empty":
                            print(f"❌ {target_day}일은 정기 휴무일이거나 예약 가능한 시간대가 없습니다.")
                        elif status == "disabled":
                            print(f"❌ {target_day}일은 휴일/휴무일 또는 예약 불가능한 날짜입니다.")
                        elif status == "unknown_markup":
                            print(f"⚠️ {target_day}일의 시간 슬롯 마크업을 인식하지 못했습니다.")
                            print("   debug/ 폴더에 저장된 HTML/스크린샷을 확인해 주세요.")
                        else:
                            print(f"❌ 달력에서 {target_day}일을 찾을 수 없습니다.")
                        print("--------------------------------------------------")

                    elif menu == '3':
                        print("새로운 식당 검색으로 이동합니다.")
                        break

                    elif menu == '0':
                        print("에이전트를 종료합니다.")
                        await context.close()
                        return

                    else:
                        print("올바른 번호를 입력해 주세요.")

            except Exception as e:
                print(f"❌ 조회 중 오류 발생: {e}")

        await context.close()

def _format_query_result(parsed: dict, result: dict) -> str:
    """query_place() 결과를 한 줄 자연어 답변으로 변환"""
    place = result.get("place_name") or parsed.get("place_name", "")
    who = f" {result['target_name']}" if result.get("target_name") else ""

    if not result.get("success"):
        return f"❌ {place}{who} 조회 실패: {result.get('error', '알 수 없는 오류')}"

    times_str = ", ".join(result.get("available_times", []))

    if result.get("mode") == "specific_day":
        return f"✅ {place}{who} {result['day']}일 예약 가능 시간: {times_str}"

    date = result["date"]
    return f"✅ {place}{who} 가장 빠른 예약 가능 날짜: {date.strftime('%Y년 %m월 %d일 (%a)')} — {times_str}"

async def run_natural_query():
    """자연어 한 문장으로 물어보면 바로 답변하는 개인용 모드

    예: '한남 미래회관 가장 빠른 예약 날짜랑 시간 알려줘', '악티 합정 민재디자이너 가장 빠른 시간 언제야'
    """
    user_data_path = os.path.join(os.getcwd(), "user_data")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_path,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ignore_https_errors=True
        )
        page = context.pages[0] if context.pages else await context.new_page()

        print("\n🤖 [자연어 예약 조회 에이전트] 예: '한남 미래회관 가장 빠른 예약 날짜랑 시간 알려줘'")

        last_context = None
        # 직전 질문과 "같은 장소 + 같은 선택 항목"이면 처음부터 다시 찾지 않고
        # 이미 열려있는 화면(entry_iframe)에서 바로 날짜만 다시 확인한다.
        session_key = None
        session_entry_iframe = None

        while True:
            question = input("\n💬 질문을 입력하세요 (종료: q): ").strip()
            if question.lower() in ['q', 'exit', 'quit']:
                print("에이전트를 종료합니다.")
                break

            parsed = await parse_natural_query(question, previous_context=last_context)
            if parsed.get("error"):
                print(f"❌ {parsed['error']}")
                continue

            last_context = parsed

            if page.is_closed():
                page = await context.new_page()
                session_entry_iframe = None
                session_key = None

            place_name = parsed["place_name"]
            target_name = parsed.get("target_name")
            key = (place_name.strip().lower(), (target_name or "").strip().lower())
            reuse = session_entry_iframe is not None and key == session_key

            who_suffix = f" (담당: {target_name})" if target_name else ""
            reuse_note = " (열린 화면 이어서)" if reuse else ""
            print(f"🔍 '{place_name}'{who_suffix}{reuse_note} 조회 중...")

            result = await query_place(
                page,
                place_name,
                people=parsed.get("people"),
                target_name=target_name,
                mode=parsed.get("mode", "earliest"),
                specific_day=parsed.get("specific_day"),
                interactive=True,
                entry_iframe=session_entry_iframe if reuse else None,
            )

            if reuse and not result.get("entry_iframe"):
                # 재사용하려던 화면이 이미 달라졌을 수 있으니, 새로 진입해서 한 번 더 시도
                print("↻ 이전 화면을 재사용할 수 없어 새로 조회합니다...")
                result = await query_place(
                    page,
                    place_name,
                    people=parsed.get("people"),
                    target_name=target_name,
                    mode=parsed.get("mode", "earliest"),
                    specific_day=parsed.get("specific_day"),
                    interactive=True,
                )

            session_entry_iframe = result.pop("entry_iframe", None)
            session_key = key if session_entry_iframe else None

            print(_format_query_result(parsed, result))

        await context.close()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--menu":
        asyncio.run(run_checker())
    else:
        asyncio.run(run_natural_query())
