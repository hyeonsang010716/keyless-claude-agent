"""
1편: API Key 없이 Claude Agent 사용하기 — 기본 query() 호출

실행:
    uv run examples/1_basic_query.py

사전 준비:
    1. claude setup-token 으로 OAuth 토큰 생성
    2. 환경변수 설정: export CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-...
    (또는 Claude Code에 이미 로그인되어 있으면 바로 실행 가능)
"""

import asyncio

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)


async def main():
    # ── 가장 기본적인 사용법 ──
    # permission_mode="bypassPermissions"는 도구 사용 시 확인 없이 자동 승인
    # 서버/자동화 환경에서는 필수
    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        allowed_tools=["Read", "Write", "Edit", "Bash", "Glob"],
        max_turns=5,
    )

    prompt = "현재 디렉토리에 hello.py를 만들어줘. 내용은 'Hello from Claude Agent SDK!' 를 출력하는 간단한 스크립트로."

    print(f"프롬프트: {prompt}")
    print("=" * 60)

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"Claude: {block.text}")
                elif isinstance(block, ToolUseBlock):
                    print(f"[도구 호출] {block.name}: {list(block.input.keys())}")

        elif isinstance(message, ResultMessage):
            print("=" * 60)
            print(f"완료: {message.num_turns}턴, {message.duration_ms}ms")
            if message.total_cost_usd:
                print(f"비용: ${message.total_cost_usd:.4f}")


if __name__ == "__main__":
    asyncio.run(main())
