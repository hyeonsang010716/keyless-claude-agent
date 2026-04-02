"""
2편: ClaudeAgentOptions 활용 예시 — 다양한 옵션 조합

실행:
    uv run examples/2_options_showcase.py

3가지 시나리오를 순서대로 실행합니다:
    1. 읽기 전용 모드 (plan) — 코드 분석만
    2. thinking 활성화 — 깊은 사고 과정 확인
    3. 구조화된 출력 — JSON 스키마로 결과 받기
"""

import asyncio
import json

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
)


async def scenario_readonly():
    """시나리오 1: 읽기 전용 모드 — 코드를 분석만 하고 수정하지 않음"""
    print("\n" + "=" * 60)
    print("시나리오 1: 읽기 전용 모드 (읽기 도구만 허용)")
    print("=" * 60)

    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        allowed_tools=["Read", "Glob", "Grep"],  # 읽기 도구만 허용 → 사실상 읽기 전용
        max_turns=3,
    )

    async for message in query(
        prompt="이 프로젝트의 pyproject.toml을 분석해서 사용 중인 의존성을 설명해줘.",
        options=options,
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"Claude: {block.text}")
                elif isinstance(block, ToolUseBlock):
                    print(f"[도구] {block.name}")

        elif isinstance(message, ResultMessage):
            print(f"\n완료: {message.num_turns}턴")


async def scenario_thinking():
    """시나리오 2: thinking 활성화 — Claude의 사고 과정 엿보기"""
    print("\n" + "=" * 60)
    print("시나리오 2: Extended Thinking 활성화")
    print("=" * 60)

    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        thinking={"type": "enabled", "budget_tokens": 5000},
        max_turns=3,
    )

    async for message in query(
        prompt="파이썬에서 GIL이 뭔지 한 문장으로 설명해줘.",
        options=options,
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ThinkingBlock):
                    # 사고 과정은 길 수 있으므로 앞부분만 출력
                    preview = block.thinking[:300]
                    print(f"[사고 과정] {preview}...")
                elif isinstance(block, TextBlock):
                    print(f"Claude: {block.text}")

        elif isinstance(message, ResultMessage):
            print(f"\n완료: {message.num_turns}턴")


async def scenario_structured_output():
    """시나리오 3: 구조화된 출력 — JSON 스키마로 결과 받기"""
    print("\n" + "=" * 60)
    print("시나리오 3: 구조화된 출력 (output_format)")
    print("=" * 60)

    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        max_turns=3,
        output_format={
            "type": "json_schema",
            "schema": {
                "type": "object",
                "properties": {
                    "language": {"type": "string"},
                    "pros": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "cons": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "rating": {"type": "integer"},
                },
                "required": ["language", "pros", "cons", "rating"],
            },
        },
    )

    async for message in query(
        prompt="Python 언어를 평가해줘.",
        options=options,
    ):
        if isinstance(message, ResultMessage):
            if message.structured_output:
                print("구조화된 출력:")
                print(json.dumps(message.structured_output, indent=2, ensure_ascii=False))
            elif message.result:
                print(f"결과: {message.result}")

            print(f"\n완료: {message.num_turns}턴")


async def main():
    await scenario_readonly()
    await scenario_thinking()
    await scenario_structured_output()


if __name__ == "__main__":
    asyncio.run(main())
