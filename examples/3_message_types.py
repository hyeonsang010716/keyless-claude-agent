"""
3편: 메시지 타입 완전 정복 — 모든 메시지 타입을 처리하는 핸들러

실행:
    uv run examples/3_message_types.py

Claude가 도구를 사용하는 과정에서 발생하는 모든 메시지 타입을 출력합니다.
각 메시지가 어떤 타입이고, 어떤 필드를 가지는지 실시간으로 확인할 수 있습니다.
"""

import asyncio
import json

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    # 메시지 타입
    AssistantMessage,
    ResultMessage,
    SystemMessage,
    RateLimitEvent,
    TaskStartedMessage,
    TaskProgressMessage,
    TaskNotificationMessage,
    # 콘텐츠 블록
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
    ToolResultBlock,
)


def print_header(label: str):
    print(f"\n{'─' * 50}")
    print(f"  {label}")
    print(f"{'─' * 50}")


async def main():
    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
        max_turns=10,
    )

    prompt = (
        "다음을 순서대로 해줘:\n"
        "1. 현재 디렉토리에서 *.py 파일을 검색해\n"
        "2. pyproject.toml 파일을 읽어\n"
        "3. 'SDK 테스트 완료'라는 내용의 test_output.txt를 만들어"
    )

    print(f"프롬프트: {prompt}")
    print("=" * 60)
    print("아래에서 각 메시지의 타입과 내용을 확인하세요.")
    print("=" * 60)

    message_count = {"assistant": 0, "system": 0, "result": 0, "rate_limit": 0}

    async for message in query(prompt=prompt, options=options):

        # ── AssistantMessage: Claude의 응답 ──
        if isinstance(message, AssistantMessage):
            message_count["assistant"] += 1
            print_header(
                f"AssistantMessage #{message_count['assistant']} "
                f"(model={message.model}, stop_reason={message.stop_reason})"
            )

            if message.error:
                print(f"  [에러] {message.error}")

            for i, block in enumerate(message.content):
                if isinstance(block, TextBlock):
                    # 긴 텍스트는 잘라서 표시
                    text = block.text if len(block.text) <= 200 else block.text[:200] + "..."
                    print(f"  [{i}] TextBlock: {text}")

                elif isinstance(block, ThinkingBlock):
                    preview = block.thinking[:150] + "..." if len(block.thinking) > 150 else block.thinking
                    print(f"  [{i}] ThinkingBlock: {preview}")

                elif isinstance(block, ToolUseBlock):
                    # 도구 입력값을 보기 좋게 표시
                    input_preview = json.dumps(block.input, ensure_ascii=False)
                    if len(input_preview) > 100:
                        input_preview = input_preview[:100] + "..."
                    print(f"  [{i}] ToolUseBlock: {block.name}(id={block.id[:8]}...)")
                    print(f"       input: {input_preview}")

                elif isinstance(block, ToolResultBlock):
                    content_preview = str(block.content)
                    if len(content_preview) > 100:
                        content_preview = content_preview[:100] + "..."
                    status = "ERROR" if block.is_error else "OK"
                    print(f"  [{i}] ToolResultBlock: [{status}] (tool_use_id={block.tool_use_id[:8]}...)")
                    print(f"       content: {content_preview}")

            if message.usage:
                print(f"  usage: {message.usage}")

        # ── TaskStartedMessage (SystemMessage 서브클래스) ──
        elif isinstance(message, TaskStartedMessage):
            message_count["system"] += 1
            print_header(f"TaskStartedMessage (task_id={message.task_id})")
            print(f"  description: {message.description}")

        # ── TaskProgressMessage (SystemMessage 서브클래스) ──
        elif isinstance(message, TaskProgressMessage):
            print(f"  [TaskProgress] 도구 {message.usage['tool_uses']}회, "
                  f"토큰 {message.usage['total_tokens']}, "
                  f"last_tool={message.last_tool_name}")

        # ── TaskNotificationMessage (SystemMessage 서브클래스) ──
        elif isinstance(message, TaskNotificationMessage):
            print_header(f"TaskNotificationMessage (task_id={message.task_id})")
            print(f"  status: {message.status}")
            print(f"  summary: {message.summary}")

        # ── SystemMessage (기타) ──
        # 주의: Task* 메시지를 먼저 체크해야 여기서 중복 처리되지 않음
        elif isinstance(message, SystemMessage):
            message_count["system"] += 1
            print_header(f"SystemMessage (subtype={message.subtype})")
            data_preview = json.dumps(message.data, ensure_ascii=False)
            if len(data_preview) > 200:
                data_preview = data_preview[:200] + "..."
            print(f"  data: {data_preview}")

        # ── RateLimitEvent ──
        elif isinstance(message, RateLimitEvent):
            message_count["rate_limit"] += 1
            info = message.rate_limit_info
            print_header(f"RateLimitEvent (status={info.status})")
            print(f"  type: {info.rate_limit_type}")
            print(f"  utilization: {info.utilization}")
            if info.resets_at:
                print(f"  resets_at: {info.resets_at}")

        # ── ResultMessage: 항상 마지막 ──
        elif isinstance(message, ResultMessage):
            message_count["result"] += 1
            print_header("ResultMessage (최종 결과)")
            print(f"  is_error:      {message.is_error}")
            print(f"  num_turns:     {message.num_turns}")
            print(f"  duration_ms:   {message.duration_ms}")
            print(f"  duration_api:  {message.duration_api_ms}")
            print(f"  stop_reason:   {message.stop_reason}")
            print(f"  total_cost:    ${message.total_cost_usd or 0:.4f}")
            print(f"  session_id:    {message.session_id}")

            if message.errors:
                print(f"  errors:        {message.errors}")
            if message.permission_denials:
                print(f"  denials:       {message.permission_denials}")

            if message.result:
                result_preview = message.result[:300] + "..." if len(message.result) > 300 else message.result
                print(f"  result:        {result_preview}")

    # ── 통계 ──
    print("\n" + "=" * 60)
    print("메시지 통계:")
    for k, v in message_count.items():
        print(f"  {k}: {v}개")


if __name__ == "__main__":
    asyncio.run(main())
