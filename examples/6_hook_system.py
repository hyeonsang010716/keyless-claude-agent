"""
6편: 훅(Hook) 시스템 — 에이전트 동작에 이벤트 리스너 달기

실행:
    uv run examples/6_hook_system.py

3가지 시나리오를 실행합니다:
    1. 전체 로깅 — PreToolUse / PostToolUse / PostToolUseFailure 로그 기록
    2. Bash 명령 차단 — PreToolUse 훅에서 permissionDecision으로 거부
    3. 도구 입력값 수정 — PreToolUse 훅에서 updatedInput으로 경로 강제 변환

주의: 훅은 ClaudeSDKClient에서만 사용 가능합니다.
"""

import asyncio
import json
from datetime import datetime

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    HookMatcher,
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)


# ─────────────────────────────────────────────────
# 시나리오 1: 전체 로깅
# ─────────────────────────────────────────────────

audit_log: list[dict] = []


async def pre_logger(input, tool_use_id, context):
    """도구 실행 전 로깅"""
    entry = {
        "time": datetime.now().strftime("%H:%M:%S.%f")[:-3],
        "event": "PRE",
        "tool": input["tool_name"],
        "input_keys": list(input["tool_input"].keys()),
    }
    audit_log.append(entry)
    print(f"    [PRE]  {entry['time']} | {input['tool_name']} | keys={entry['input_keys']}")
    return {}


async def post_logger(input, tool_use_id, context):
    """도구 실행 후 로깅"""
    response = str(input.get("tool_response", ""))
    preview = response[:80] + "..." if len(response) > 80 else response
    entry = {
        "time": datetime.now().strftime("%H:%M:%S.%f")[:-3],
        "event": "POST",
        "tool": input["tool_name"],
        "response_preview": preview,
    }
    audit_log.append(entry)
    print(f"    [POST] {entry['time']} | {input['tool_name']} | {preview}")
    return {}


async def failure_logger(input, tool_use_id, context):
    """도구 실행 실패 로깅"""
    entry = {
        "time": datetime.now().strftime("%H:%M:%S.%f")[:-3],
        "event": "FAIL",
        "tool": input["tool_name"],
        "error": input["error"],
    }
    audit_log.append(entry)
    print(f"    [FAIL] {entry['time']} | {input['tool_name']} | {input['error'][:80]}")
    return {}


async def scenario_logging():
    print("\n" + "=" * 60)
    print("시나리오 1: 전체 로깅 — 도구 호출 전/후/실패를 기록")
    print("=" * 60)

    audit_log.clear()

    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        allowed_tools=["Read", "Glob", "Grep"],
        max_turns=5,
        hooks={
            "PreToolUse": [HookMatcher(matcher=None, hooks=[pre_logger])],
            "PostToolUse": [HookMatcher(matcher=None, hooks=[post_logger])],
            "PostToolUseFailure": [HookMatcher(matcher=None, hooks=[failure_logger])],
        },
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(
            "pyproject.toml을 읽고, 프로젝트에서 사용하는 의존성을 알려줘."
        )

        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        text = block.text[:150] + "..." if len(block.text) > 150 else block.text
                        print(f"  Claude: {text}")
            elif isinstance(message, ResultMessage):
                print(f"\n  완료: {message.num_turns}턴")

    print(f"\n  감사 로그: 총 {len(audit_log)}건")
    for entry in audit_log:
        print(f"    {entry['event']:4s} | {entry['time']} | {entry['tool']}")


# ─────────────────────────────────────────────────
# 시나리오 2: Bash 명령 차단
# ─────────────────────────────────────────────────

BLOCKED_PATTERNS = ["rm -rf", "rm -r /", "mkfs", "dd if=", "> /dev/"]


async def bash_guard(input, tool_use_id, context):
    """위험한 Bash 명령을 hookSpecificOutput으로 차단"""
    command = input["tool_input"].get("command", "")

    for pattern in BLOCKED_PATTERNS:
        if pattern in command:
            print(f"    [DENY] 위험 명령 감지: '{pattern}' in '{command}'")
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"보안 정책 위반: {pattern}",
                }
            }

    print(f"    [ALLOW] Bash: {command[:80]}")
    return {}


async def scenario_bash_guard():
    print("\n" + "=" * 60)
    print("시나리오 2: Bash 명령 차단 — permissionDecision으로 거부")
    print("=" * 60)

    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        allowed_tools=["Bash"],
        max_turns=5,
        hooks={
            "PreToolUse": [
                HookMatcher(matcher="Bash", hooks=[bash_guard]),
            ],
        },
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(
            "다음 두 가지를 해줘:\n"
            "1. echo 'hello from hook test' 실행\n"
            "2. rm -rf /tmp/test_dir 실행\n"
            "각각 결과를 알려줘."
        )

        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(f"  Claude: {block.text}")
            elif isinstance(message, ResultMessage):
                print(f"\n  완료: {message.num_turns}턴")


# ─────────────────────────────────────────────────
# 시나리오 3: 도구 입력값 수정 (경로 강제 변환)
# ─────────────────────────────────────────────────

WORKSPACE = "/tmp/claude-hook-example-workspace"


async def path_rewriter(input, tool_use_id, context):
    """파일 경로를 workspace 안으로 강제 변환"""
    tool_input = input["tool_input"]
    path_field = {"Read": "file_path", "Write": "file_path", "Edit": "file_path"}.get(
        input["tool_name"]
    )

    if path_field and path_field in tool_input:
        original = tool_input[path_field]
        if not original.startswith(WORKSPACE):
            safe_path = f"{WORKSPACE}/{original.lstrip('/')}"
            print(f"    [REWRITE] {original} → {safe_path}")
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "updatedInput": {**tool_input, path_field: safe_path},
                }
            }
        else:
            print(f"    [OK] {original}")

    return {}


async def scenario_path_rewrite():
    print("\n" + "=" * 60)
    print("시나리오 3: 경로 강제 변환 — updatedInput으로 입력 수정")
    print("=" * 60)

    import os
    os.makedirs(WORKSPACE, exist_ok=True)

    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        allowed_tools=["Write", "Read"],
        max_turns=5,
        hooks={
            "PreToolUse": [
                HookMatcher(matcher="Write|Read|Edit", hooks=[path_rewriter]),
            ],
        },
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(
            "hook_output.txt 파일을 만들어줘. 내용은 'Hello from hook system!' 으로."
        )

        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(f"  Claude: {block.text}")
                    elif isinstance(block, ToolUseBlock):
                        print(f"  [도구] {block.name}: {block.input}")
            elif isinstance(message, ResultMessage):
                print(f"\n  완료: {message.num_turns}턴")

    # 결과 확인
    expected = f"{WORKSPACE}/hook_output.txt"
    if os.path.exists(expected):
        with open(expected) as f:
            print(f"\n  파일 생성됨: {expected}")
            print(f"  내용: {f.read()}")
    else:
        print(f"\n  {expected} 에 파일이 없습니다.")
        # workspace 안에 다른 경로로 생성되었을 수 있음
        for root, dirs, files in os.walk(WORKSPACE):
            for fname in files:
                fpath = os.path.join(root, fname)
                print(f"  발견된 파일: {fpath}")


async def main():
    await scenario_logging()
    await scenario_bash_guard()
    await scenario_path_rewrite()

    print("\n" + "=" * 60)
    print("모든 시나리오 완료")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
