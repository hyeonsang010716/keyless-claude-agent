"""
MCP 서버 — Claude에게 나만의 커스텀 도구 달아주기

실행:
    uv run examples/7_mcp_server.py

3가지 시나리오를 실행합니다:
    1. 계산기 서버 — @tool로 add, multiply, sqrt 도구를 만들어 Claude에 연결
    2. 앱 상태 노출 — Python 딕셔너리(가짜 DB)를 Claude가 조회하도록 연결
    3. 여러 서버 조합 — 계산기 + 앱 상태를 동시에 연결
"""

import asyncio
import json
import math
from typing import Annotated

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    create_sdk_mcp_server,
    tool,
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)


# ═════════════════════════════════════════════════
# 도구 정의
# ═════════════════════════════════════════════════

# ── 계산기 도구들 ──

@tool("add", "두 수를 더합니다", {"a": float, "b": float})
async def add(args):
    result = args["a"] + args["b"]
    return {"content": [{"type": "text", "text": str(result)}]}


@tool("multiply", "두 수를 곱합니다", {"a": float, "b": float})
async def multiply(args):
    result = args["a"] * args["b"]
    return {"content": [{"type": "text", "text": str(result)}]}


@tool("sqrt", "제곱근을 구합니다", {"n": float})
async def sqrt(args):
    if args["n"] < 0:
        return {
            "content": [{"type": "text", "text": "음수의 제곱근은 구할 수 없습니다."}],
            "is_error": True,
        }
    return {"content": [{"type": "text", "text": str(math.sqrt(args["n"]))}]}


# ── 앱 상태(가짜 DB) 도구들 ──

users_db = {
    1: {"name": "홍길동", "role": "admin", "orders": 5},
    2: {"name": "김철수", "role": "user", "orders": 12},
    3: {"name": "이영희", "role": "user", "orders": 3},
}


@tool("list_users", "전체 사용자 목록 조회", {})
async def list_users(args):
    lines = [f"ID {uid}: {u['name']} ({u['role']}, 주문 {u['orders']}건)"
             for uid, u in users_db.items()]
    return {"content": [{"type": "text", "text": "\n".join(lines)}]}


@tool("get_user", "사용자 정보 조회", {"user_id": Annotated[int, "조회할 사용자 ID"]})
async def get_user(args):
    user = users_db.get(args["user_id"])
    if not user:
        return {
            "content": [{"type": "text", "text": f"ID {args['user_id']}인 사용자를 찾을 수 없습니다."}],
            "is_error": True,
        }
    return {"content": [{"type": "text", "text": json.dumps(user, ensure_ascii=False)}]}


# ═════════════════════════════════════════════════
# 헬퍼
# ═════════════════════════════════════════════════

async def run_query(prompt: str, options: ClaudeAgentOptions):
    """query()를 실행하고 결과를 출력하는 공통 함수"""
    print(f"\n  프롬프트: {prompt}")
    print(f"  {'─' * 50}")

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    text = block.text[:300] + "..." if len(block.text) > 300 else block.text
                    print(f"  Claude: {text}")
                elif isinstance(block, ToolUseBlock):
                    input_str = json.dumps(block.input, ensure_ascii=False)
                    print(f"  [도구 호출] {block.name}({input_str})")

        elif isinstance(message, ResultMessage):
            print(f"\n  완료: {message.num_turns}턴, {message.duration_ms}ms")
            if message.total_cost_usd:
                print(f"  비용: ${message.total_cost_usd:.4f}")


# ═════════════════════════════════════════════════
# 시나리오
# ═════════════════════════════════════════════════

async def scenario_calculator():
    """시나리오 1: 계산기 서버"""
    print("\n" + "=" * 60)
    print("시나리오 1: 계산기 서버 — add, multiply, sqrt")
    print("=" * 60)

    calculator = create_sdk_mcp_server(
        name="calculator",
        tools=[add, multiply, sqrt],
    )

    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        mcp_servers={"calculator": calculator},
        allowed_tools=["add", "multiply", "sqrt"],
        max_turns=5,
    )

    await run_query(
        "(3 + 7) * 4 의 제곱근을 구해줘. 계산기 도구를 사용해서 단계별로.",
        options,
    )


async def scenario_app_state():
    """시나리오 2: 앱 상태(가짜 DB) 노출"""
    print("\n" + "=" * 60)
    print("시나리오 2: 앱 상태 노출 — list_users, get_user")
    print("=" * 60)

    user_server = create_sdk_mcp_server(
        name="user-db",
        tools=[list_users, get_user],
    )

    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        mcp_servers={"user-db": user_server},
        allowed_tools=["list_users", "get_user"],
        max_turns=5,
    )

    await run_query(
        "전체 사용자 목록을 조회한 다음, 주문이 가장 많은 사용자의 상세 정보를 알려줘.",
        options,
    )


async def scenario_combined():
    """시나리오 3: 계산기 + 앱 상태 동시 연결"""
    print("\n" + "=" * 60)
    print("시나리오 3: 여러 서버 조합 — 계산기 + 사용자 DB")
    print("=" * 60)

    calculator = create_sdk_mcp_server("calculator", tools=[add, multiply, sqrt])
    user_server = create_sdk_mcp_server("user-db", tools=[list_users, get_user])

    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        mcp_servers={
            "calculator": calculator,
            "user-db": user_server,
        },
        allowed_tools=["add", "multiply", "sqrt", "list_users", "get_user"],
        max_turns=8,
    )

    await run_query(
        "전체 사용자의 주문 수를 합산해줘. "
        "먼저 list_users로 목록을 조회하고, add 도구로 합산해.",
        options,
    )


async def main():
    await scenario_calculator()
    await scenario_app_state()
    await scenario_combined()

    print("\n" + "=" * 60)
    print("모든 시나리오 완료")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
