"""
5편: 권한 시스템 심화 — can_use_tool 콜백으로 도구 호출 제어하기

실행:
    uv run examples/5_permission_system.py

3가지 시나리오를 실행합니다:
    1. 감사 로그 — 모든 도구 호출을 로깅하면서 허용
    2. 위험 명령 차단 — rm -rf 같은 명령을 감지하고 거부
    3. 경로 격리 — 파일 경로를 workspace 안으로 강제 변환

주의: can_use_tool은 ClaudeSDKClient에서만 사용 가능합니다.
      query() 함수로는 사용할 수 없습니다.
"""

import asyncio
import json
from datetime import datetime

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext,
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)


# ─────────────────────────────────────────────────
# 시나리오 1: 감사 로그
# ─────────────────────────────────────────────────

audit_log: list[dict] = []


async def audit_guard(
    tool_name: str,
    tool_input: dict,
    context: ToolPermissionContext,
) -> PermissionResultAllow:
    """모든 도구 호출을 기록하고 허용"""
    entry = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "tool": tool_name,
        "input_keys": list(tool_input.keys()),
        "agent_id": context.agent_id,
    }
    audit_log.append(entry)
    print(f"  [감사 로그] {entry['time']} | {tool_name} | keys={entry['input_keys']}")
    return PermissionResultAllow()


async def scenario_audit():
    print("\n" + "=" * 60)
    print("시나리오 1: 감사 로그 — 모든 도구 호출을 기록")
    print("=" * 60)

    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        allowed_tools=["Read", "Glob", "Grep"],
        can_use_tool=audit_guard,
        max_turns=5,
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query("pyproject.toml 파일을 읽고 의존성 목록을 알려줘.")

        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        text = block.text[:200] + "..." if len(block.text) > 200 else block.text
                        print(f"Claude: {text}")
            elif isinstance(message, ResultMessage):
                print(f"\n완료: {message.num_turns}턴")

    print(f"\n기록된 도구 호출: {len(audit_log)}건")
    for entry in audit_log:
        print(f"  {entry['time']} | {entry['tool']}")


# ─────────────────────────────────────────────────
# 시나리오 2: 위험 명령 차단
# ─────────────────────────────────────────────────

BLOCKED_PATTERNS = ["rm -rf", "rm -r /", ":(){ :|:& };:", "mkfs", "dd if="]


async def security_guard(
    tool_name: str,
    tool_input: dict,
    context: ToolPermissionContext,
) -> PermissionResultAllow | PermissionResultDeny:
    """위험한 Bash 명령을 감지하고 차단"""
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        for pattern in BLOCKED_PATTERNS:
            if pattern in command:
                print(f"  [차단] 위험 명령 감지: '{pattern}' in '{command}'")
                return PermissionResultDeny(
                    message=f"보안 정책에 의해 차단됨: {pattern}",
                )
        print(f"  [허용] Bash: {command[:80]}")

    return PermissionResultAllow()


async def scenario_security():
    print("\n" + "=" * 60)
    print("시나리오 2: 위험 명령 차단")
    print("=" * 60)

    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        allowed_tools=["Bash"],
        can_use_tool=security_guard,
        max_turns=5,
    )

    async with ClaudeSDKClient(options=options) as client:
        # Claude는 이 요청을 받으면 Bash 도구를 시도하지만,
        # security_guard가 rm -rf 패턴을 감지하면 거부합니다.
        await client.query(
            "다음 두 가지를 해줘:\n"
            "1. echo 'hello' 를 실행해줘\n"
            "2. rm -rf /tmp/test 를 실행해줘\n"
            "각각의 결과를 알려줘."
        )

        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(f"Claude: {block.text}")
            elif isinstance(message, ResultMessage):
                print(f"\n완료: {message.num_turns}턴")
                if message.permission_denials:
                    print(f"거부된 요청: {len(message.permission_denials)}건")


# ─────────────────────────────────────────────────
# 시나리오 3: 경로 격리 (updated_input)
# ─────────────────────────────────────────────────

WORKSPACE = "/tmp/claude-sdk-example-workspace"


async def path_sandbox(
    tool_name: str,
    tool_input: dict,
    context: ToolPermissionContext,
) -> PermissionResultAllow:
    """파일 경로를 workspace 안으로 강제 변환"""
    path_field = {
        "Read": "file_path",
        "Write": "file_path",
        "Edit": "file_path",
    }.get(tool_name)

    if path_field and path_field in tool_input:
        original = tool_input[path_field]

        if not original.startswith(WORKSPACE):
            # 경로를 workspace 안으로 리다이렉트
            safe_path = f"{WORKSPACE}/{original.lstrip('/')}"
            print(f"  [경로 변환] {original} → {safe_path}")
            return PermissionResultAllow(
                updated_input={**tool_input, path_field: safe_path}
            )
        else:
            print(f"  [경로 OK] {original}")

    return PermissionResultAllow()


async def scenario_path_sandbox():
    print("\n" + "=" * 60)
    print("시나리오 3: 경로 격리 — workspace 밖 쓰기 방지")
    print("=" * 60)

    # workspace 디렉토리 생성
    import os
    os.makedirs(WORKSPACE, exist_ok=True)

    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        allowed_tools=["Write", "Read"],
        can_use_tool=path_sandbox,
        max_turns=5,
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(
            "sandbox_test.txt 파일을 만들어줘. 내용은 'Hello from sandbox!' 로."
        )

        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(f"Claude: {block.text}")
                    elif isinstance(block, ToolUseBlock):
                        print(f"[도구] {block.name}: {block.input}")
            elif isinstance(message, ResultMessage):
                print(f"\n완료: {message.num_turns}턴")

    # 결과 확인
    expected = f"{WORKSPACE}/sandbox_test.txt"
    if os.path.exists(expected):
        print(f"\n파일이 workspace 안에 생성됨: {expected}")
        with open(expected) as f:
            print(f"내용: {f.read()}")
    else:
        # Claude가 다른 경로를 사용했을 수 있음
        print(f"\n{expected} 에 파일이 없습니다. Claude가 다른 경로를 선택했을 수 있습니다.")


async def main():
    await scenario_audit()
    await scenario_security()
    await scenario_path_sandbox()

    print("\n" + "=" * 60)
    print("모든 시나리오 완료")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
