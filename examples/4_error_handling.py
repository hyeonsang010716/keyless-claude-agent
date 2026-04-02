"""
4편: 에러 처리 — 모든 에러 경로를 빠짐없이 잡기

실행:
    uv run examples/4_error_handling.py

3가지 시나리오를 실행합니다:
    1. 정상 쿼리 — 에러 없이 성공하는 케이스
    2. 존재하지 않는 작업 디렉토리 — CLIConnectionError 발생
    3. 의도적 에러 유발 — 메시지 내 에러 필드 확인

두 가지 에러 경로를 모두 보여줍니다:
    - 경로 1: try/except로 잡는 예외 (SDK 레벨)
    - 경로 2: 메시지 내 에러 필드 (응답 레벨)
"""

import asyncio
import os

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    # 예외 타입
    ClaudeSDKError,
    CLIConnectionError,
    CLINotFoundError,
    ProcessError,
    CLIJSONDecodeError,
    # 메시지 타입
    AssistantMessage,
    ResultMessage,
    RateLimitEvent,
    TextBlock,
    ToolResultBlock,
)


async def safe_query(prompt: str, options: ClaudeAgentOptions) -> str:
    """두 가지 에러 경로를 모두 처리하는 쿼리 함수"""

    result_text = ""

    try:
        async for message in query(prompt=prompt, options=options):

            # ── 경로 2a: AssistantMessage.error ──
            if isinstance(message, AssistantMessage):
                if message.error:
                    return f"[응답 에러] {message.error}"

                for block in message.content:
                    if isinstance(block, TextBlock):
                        result_text += block.text
                    # ── 경로 2b: ToolResultBlock.is_error ──
                    elif isinstance(block, ToolResultBlock) and block.is_error:
                        print(f"  [도구 실패] {block.content}")

            # ── 경로 2c: RateLimitEvent ──
            elif isinstance(message, RateLimitEvent):
                info = message.rate_limit_info
                if info.status == "rejected":
                    return f"[레이트 리밋] 한도 초과. 초기화: {info.resets_at}"
                elif info.status == "allowed_warning":
                    print(f"  [경고] 사용량 {(info.utilization or 0) * 100:.0f}%")

            # ── 경로 2d: ResultMessage.is_error ──
            elif isinstance(message, ResultMessage):
                if message.is_error:
                    return f"[실행 에러] {message.errors}"
                if message.result:
                    result_text = message.result

    # ── 경로 1: 예외 (구체적인 것부터 잡기) ──
    except CLINotFoundError:
        return "[CLINotFoundError] Claude Code CLI가 설치되지 않았습니다."

    except ProcessError as e:
        diag = {
            "exit_code": e.exit_code,
            "token": "SET" if os.getenv("CLAUDE_CODE_OAUTH_TOKEN") else "NOT SET",
            "node": os.popen("node --version 2>&1").read().strip(),
        }
        return f"[ProcessError] {e}\n  진단: {diag}"

    except CLIConnectionError as e:
        return f"[CLIConnectionError] {e}"

    except CLIJSONDecodeError as e:
        return f"[CLIJSONDecodeError] 파싱 실패: {e.line[:80]}"

    except ClaudeSDKError as e:
        return f"[ClaudeSDKError] {type(e).__name__}: {e}"

    return result_text or "[결과 없음]"


async def scenario_success():
    """시나리오 1: 정상 쿼리"""
    print("\n" + "=" * 60)
    print("시나리오 1: 정상 쿼리")
    print("=" * 60)

    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        max_turns=3,
    )

    result = await safe_query("1 + 1 = ?  한 줄로 답해줘.", options)
    print(f"결과: {result}")


async def scenario_bad_cwd():
    """시나리오 2: 존재하지 않는 작업 디렉토리 → CLIConnectionError"""
    print("\n" + "=" * 60)
    print("시나리오 2: 존재하지 않는 작업 디렉토리")
    print("=" * 60)

    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        cwd="/this/path/does/not/exist",  # 존재하지 않는 경로
        max_turns=1,
    )

    result = await safe_query("안녕", options)
    print(f"결과: {result}")


async def scenario_tool_error():
    """시나리오 3: 도구 실행 에러 — 없는 파일 읽기"""
    print("\n" + "=" * 60)
    print("시나리오 3: 도구 실행 에러 (없는 파일 읽기)")
    print("=" * 60)

    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        allowed_tools=["Read", "Bash"],
        max_turns=3,
    )

    result = await safe_query(
        "/tmp/this_file_definitely_does_not_exist_12345.txt 파일을 읽어줘. "
        "파일이 없으면 '파일 없음'이라고 답해줘.",
        options,
    )
    print(f"결과: {result}")


async def main():
    await scenario_success()
    await scenario_bad_cwd()
    await scenario_tool_error()

    print("\n" + "=" * 60)
    print("모든 시나리오 완료")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
