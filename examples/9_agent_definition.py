"""
커스텀 에이전트 정의 — 역할 분담하는 멀티 에이전트 만들기

실행:
    uv run examples/9_agent_definition.py

2가지 시나리오를 실행합니다:
    1. 분석자 + 실행자 — 읽기 전용 에이전트가 분석, 쓰기 에이전트가 실행
    2. 태스크 추적 — 서브 에이전트 실행 중 Task 메시지를 실시간 모니터링

핵심 포인트:
    - AgentDefinition의 description이 메인 에이전트의 위임 판단 기준
    - 각 에이전트에 다른 tools, model, maxTurns 할당 가능
    - TaskStartedMessage/TaskProgressMessage/TaskNotificationMessage로 진행 추적
"""

import asyncio
import json

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AgentDefinition,
    # 메시지 타입
    AssistantMessage,
    ResultMessage,
    SystemMessage,
    TaskStartedMessage,
    TaskProgressMessage,
    TaskNotificationMessage,
    # 콘텐츠 블록
    TextBlock,
    ToolUseBlock,
)


# ─────────────────────────────────────────────────
# 시나리오 1: 분석자 + 실행자
# ─────────────────────────────────────────────────

async def scenario_analyst_executor():
    """읽기 전용 분석자가 코드를 분석하고, 실행자가 파일을 생성"""
    print("\n" + "=" * 60)
    print("시나리오 1: 분석자 + 실행자 — 역할 분리")
    print("=" * 60)

    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        max_turns=20,
        agents={
            "analyst": AgentDefinition(
                description="프로젝트 구조와 코드를 분석합니다. 파일을 수정하지 않습니다.",
                prompt=(
                    "너는 코드 분석 전문가야.\n"
                    "프로젝트 구조를 파악하고, 사용된 기술 스택을 정리해.\n"
                    "파일을 수정하거나 생성하지 마. 분석 결과만 보고해."
                ),
                tools=["Read", "Glob", "Grep"],  # 읽기 도구만
                maxTurns=5,
                effort="high",
            ),
            "writer": AgentDefinition(
                description="분석 결과를 바탕으로 요약 파일을 생성합니다.",
                prompt=(
                    "너는 문서 작성자야.\n"
                    "주어진 분석 결과를 깔끔한 마크다운 파일로 정리해.\n"
                    "파일 이름은 analysis_result.md 로 해."
                ),
                tools=["Write"],  # 쓰기 도구만
                maxTurns=3,
            ),
        },
    )

    print("  프롬프트: 이 프로젝트를 분석하고 결과를 파일로 정리해줘.\n")

    task_tracker: dict[str, str] = {}  # task_id → description

    async for message in query(
        prompt="이 프로젝트의 구조를 분석하고 결과를 analysis_result.md 파일로 정리해줘.",
        options=options,
    ):
        # 서브 에이전트 추적
        if isinstance(message, TaskStartedMessage):
            task_tracker[message.task_id] = message.description
            print(f"  [태스크 시작] {message.description}")

        elif isinstance(message, TaskProgressMessage):
            desc = task_tracker.get(message.task_id, "?")
            usage = message.usage
            last = message.last_tool_name or "—"
            print(f"  [진행] {desc}: 도구 {usage['tool_uses']}회, "
                  f"토큰 {usage['total_tokens']}, 마지막={last}")

        elif isinstance(message, TaskNotificationMessage):
            desc = task_tracker.pop(message.task_id, "?")
            summary = message.summary[:100] + "..." if len(message.summary) > 100 else message.summary
            print(f"  [태스크 {message.status}] {desc}")
            print(f"    요약: {summary}")
            if message.usage:
                print(f"    사용량: 토큰 {message.usage['total_tokens']}, "
                      f"도구 {message.usage['tool_uses']}회")

        # 메인 에이전트 응답
        elif isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    text = block.text[:200] + "..." if len(block.text) > 200 else block.text
                    print(f"  Claude: {text}")
                elif isinstance(block, ToolUseBlock):
                    print(f"  [도구] {block.name}")

        # 기타 시스템 메시지 (Task* 이외)
        elif isinstance(message, SystemMessage):
            pass  # Task 서브클래스가 아닌 SystemMessage는 무시

        elif isinstance(message, ResultMessage):
            print(f"\n  완료: {message.num_turns}턴, {message.duration_ms}ms")
            if message.total_cost_usd:
                print(f"  비용: ${message.total_cost_usd:.4f}")


# ─────────────────────────────────────────────────
# 시나리오 2: 모델별 역할 분배 + 태스크 모니터링
# ─────────────────────────────────────────────────

async def scenario_model_split():
    """에이전트별로 다른 모델을 사용하고, 태스크 진행을 상세 모니터링"""
    print("\n" + "=" * 60)
    print("시나리오 2: 모델별 역할 분배 + 태스크 모니터링")
    print("=" * 60)

    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        max_turns=15,
        agents={
            "quick-scanner": AgentDefinition(
                description="프로젝트에서 Python 파일 목록을 빠르게 스캔합니다.",
                prompt=(
                    "너는 빠른 파일 스캐너야.\n"
                    "프로젝트에서 .py 파일을 찾고 각 파일의 줄 수를 보고해.\n"
                    "간결하게 보고해."
                ),
                tools=["Glob", "Bash"],
                maxTurns=3,
                effort="low",
            ),
            "deep-reader": AgentDefinition(
                description="특정 파일의 코드를 읽고 핵심 함수/클래스를 요약합니다.",
                prompt=(
                    "너는 코드 분석가야.\n"
                    "주어진 파일을 읽고 핵심 함수와 클래스를 나열해.\n"
                    "각각의 역할을 한 줄로 요약해."
                ),
                tools=["Read", "Grep"],
                maxTurns=5,
                effort="high",
            ),
        },
    )

    print("  프롬프트: Python 파일을 스캔하고 main.py를 상세 분석해줘.\n")

    # 태스크별 통계 수집
    task_stats: dict[str, dict] = {}

    async for message in query(
        prompt=(
            "다음을 순서대로 해줘:\n"
            "1. quick-scanner로 프로젝트의 .py 파일 목록을 스캔해\n"
            "2. deep-reader로 main.py의 핵심 구조를 분석해\n"
            "3. 두 결과를 종합해서 프로젝트 개요를 한 문단으로 정리해"
        ),
        options=options,
    ):
        if isinstance(message, TaskStartedMessage):
            task_stats[message.task_id] = {
                "description": message.description,
                "started": True,
                "progress_count": 0,
            }
            print(f"  [시작] {message.description}")

        elif isinstance(message, TaskProgressMessage):
            stats = task_stats.get(message.task_id)
            if stats:
                stats["progress_count"] += 1
                stats["last_usage"] = message.usage
            print(f"  [진행 #{stats['progress_count'] if stats else '?'}] "
                  f"도구 {message.usage['tool_uses']}회, "
                  f"토큰 {message.usage['total_tokens']}")

        elif isinstance(message, TaskNotificationMessage):
            stats = task_stats.get(message.task_id, {})
            summary = message.summary[:120] + "..." if len(message.summary) > 120 else message.summary
            print(f"  [{message.status.upper()}] {stats.get('description', '?')}")
            print(f"    요약: {summary}")
            print(f"    progress 업데이트: {stats.get('progress_count', 0)}회")

        elif isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    text = block.text[:300] + "..." if len(block.text) > 300 else block.text
                    print(f"  Claude: {text}")

        elif isinstance(message, SystemMessage):
            pass

        elif isinstance(message, ResultMessage):
            print(f"\n  완료: {message.num_turns}턴")
            if message.total_cost_usd:
                print(f"  비용: ${message.total_cost_usd:.4f}")

    # 태스크 통계 요약
    if task_stats:
        print(f"\n  {'─' * 40}")
        print(f"  태스크 통계:")
        for tid, stats in task_stats.items():
            usage = stats.get("last_usage", {})
            print(f"    {stats['description']}: "
                  f"토큰 {usage.get('total_tokens', '?')}, "
                  f"도구 {usage.get('tool_uses', '?')}회, "
                  f"업데이트 {stats['progress_count']}회")


async def main():
    await scenario_analyst_executor()
    await scenario_model_split()

    print("\n" + "=" * 60)
    print("모든 시나리오 완료")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
