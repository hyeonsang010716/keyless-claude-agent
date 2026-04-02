"""
세션 관리 — 대화 이력 조회, 분기, 삭제

실행:
    uv run examples/8_session_management.py

4가지 시나리오를 실행합니다:
    1. 세션 목록 조회 — list_sessions()로 현재 프로젝트의 세션을 나열
    2. 대화 내역 열람 — get_session_messages()로 특정 세션의 대화를 읽기
    3. 세션 이름/태그 — rename_session(), tag_session()으로 메타데이터 변경
    4. 세션 분기(fork) — fork_session()으로 대화를 복제하고 분기

주의: 이 예시는 CLI 없이 동작합니다.
      모든 세션 함수는 동기 함수이며, ~/.claude/projects/ 의 JSONL 파일을 직접 읽습니다.
      세션이 하나도 없으면 시나리오 2~4는 건너뜁니다.
"""

import os
from datetime import datetime
from collections import Counter

from claude_agent_sdk import (
    list_sessions,
    get_session_info,
    get_session_messages,
    rename_session,
    tag_session,
    fork_session,
    delete_session,
    SDKSessionInfo,
)


# ─────────────────────────────────────────────────
# 시나리오 1: 세션 목록 조회
# ─────────────────────────────────────────────────

def scenario_list():
    print("\n" + "=" * 60)
    print("시나리오 1: 세션 목록 조회")
    print("=" * 60)

    # 현재 프로젝트 디렉토리 기준
    cwd = os.getcwd()
    print(f"  프로젝트: {cwd}")

    sessions = list_sessions(directory=cwd, limit=10)
    print(f"  세션 수: {len(sessions)}개 (최근 10개)")

    if not sessions:
        # 전체 프로젝트에서 시도
        print("  현재 프로젝트에 세션이 없습니다. 전체 프로젝트에서 검색합니다.")
        sessions = list_sessions(limit=10)
        print(f"  전체 세션 수: {len(sessions)}개 (최근 10개)")

    for i, s in enumerate(sessions):
        modified = datetime.fromtimestamp(s.last_modified / 1000)
        branch = f" [{s.git_branch}]" if s.git_branch else ""
        tag_str = f" #{s.tag}" if s.tag else ""
        size = f" ({s.file_size / 1024:.0f}KB)" if s.file_size else ""

        title = s.summary[:50] + "..." if len(s.summary) > 50 else s.summary
        print(f"  [{i + 1}] {title}{branch}{tag_str}{size}")
        print(f"       ID: {s.session_id}")
        print(f"       수정: {modified:%Y-%m-%d %H:%M}")

    # 간단한 통계
    if sessions:
        branches = Counter(s.git_branch for s in sessions if s.git_branch)
        if branches:
            print(f"\n  브랜치별: {dict(branches.most_common(5))}")

    return sessions


# ─────────────────────────────────────────────────
# 시나리오 2: 대화 내역 열람
# ─────────────────────────────────────────────────

def scenario_messages(session: SDKSessionInfo):
    print("\n" + "=" * 60)
    print("시나리오 2: 대화 내역 열람")
    print("=" * 60)
    print(f"  세션: {session.summary[:60]}")
    print(f"  ID: {session.session_id}")

    # get_session_info로 단일 조회 확인
    info = get_session_info(session.session_id)
    if info:
        print(f"  get_session_info 확인: OK (summary={info.summary[:40]}...)")
    else:
        print(f"  get_session_info 확인: 찾을 수 없음")
        return

    # 대화 메시지 조회 (처음 10개)
    messages = get_session_messages(session.session_id, limit=10)
    print(f"  메시지 수: {len(messages)}개 (최대 10개)")

    for j, msg in enumerate(messages):
        role = "사용자  " if msg.type == "user" else "Claude  "

        content = msg.message.get("content", "")
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            # 텍스트 블록만 추출
            text_parts = []
            tool_count = 0
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        text_parts.append(block["text"])
                    elif block.get("type") == "tool_use":
                        tool_count += 1
            text = " ".join(text_parts)
            if tool_count:
                text += f" [도구 {tool_count}개 사용]"
        else:
            text = str(content)

        # 80자로 잘라서 표시
        preview = text.replace("\n", " ")
        if len(preview) > 80:
            preview = preview[:80] + "..."

        print(f"\n  [{j + 1}] {role} (uuid={msg.uuid[:8]}...)")
        print(f"       {preview}")

    return messages


# ─────────────────────────────────────────────────
# 시나리오 3: 세션 이름/태그 변경
# ─────────────────────────────────────────────────

def scenario_rename_tag(session: SDKSessionInfo):
    print("\n" + "=" * 60)
    print("시나리오 3: 세션 이름/태그 변경")
    print("=" * 60)
    print(f"  대상 세션: {session.summary[:60]}")

    # 이름 변경
    new_title = f"[SDK 예시] {session.summary[:30]}"
    print(f"\n  rename_session() 호출...")
    print(f"    변경 전: {session.summary[:50]}")
    print(f"    변경 후: {new_title}")

    try:
        rename_session(session.session_id, new_title)
        print(f"    결과: 성공")
    except (ValueError, FileNotFoundError) as e:
        print(f"    결과: 실패 — {e}")
        return

    # 태그 설정
    print(f"\n  tag_session() 호출...")
    print(f"    태그: sdk-example")

    try:
        tag_session(session.session_id, "sdk-example")
        print(f"    결과: 성공")
    except (ValueError, FileNotFoundError) as e:
        print(f"    결과: 실패 — {e}")
        return

    # 변경 확인
    updated = get_session_info(session.session_id)
    if updated:
        print(f"\n  변경 확인:")
        print(f"    summary: {updated.summary[:60]}")
        print(f"    custom_title: {updated.custom_title}")
        print(f"    tag: {updated.tag}")

    # 태그 해제 (원래대로)
    print(f"\n  태그 해제 중...")
    try:
        tag_session(session.session_id, None)
        print(f"    결과: 태그 해제 성공")
    except Exception as e:
        print(f"    결과: {e}")


# ─────────────────────────────────────────────────
# 시나리오 4: 세션 분기 (fork)
# ─────────────────────────────────────────────────

def scenario_fork(session: SDKSessionInfo):
    print("\n" + "=" * 60)
    print("시나리오 4: 세션 분기 (fork)")
    print("=" * 60)
    print(f"  원본 세션: {session.summary[:60]}")
    print(f"  원본 ID: {session.session_id}")

    # 메시지 목록에서 분기점 찾기
    messages = get_session_messages(session.session_id, limit=5)
    if not messages:
        print("  메시지가 없어 fork를 할 수 없습니다.")
        return

    # 첫 번째 메시지 시점에서 분기
    branch_point = messages[0]
    print(f"  분기점: 첫 번째 메시지 (uuid={branch_point.uuid[:12]}...)")

    print(f"\n  fork_session() 호출...")
    try:
        result = fork_session(
            session.session_id,
            up_to_message_id=branch_point.uuid,
            title=f"Fork 테스트 — {session.summary[:20]}",
        )
        print(f"    결과: 성공")
        print(f"    새 세션 ID: {result.session_id}")

        # fork된 세션 확인
        forked_info = get_session_info(result.session_id)
        if forked_info:
            print(f"    새 세션 제목: {forked_info.summary}")
            print(f"    새 세션 custom_title: {forked_info.custom_title}")

        forked_messages = get_session_messages(result.session_id)
        print(f"    새 세션 메시지 수: {len(forked_messages)}개")

        # fork된 세션 정리 (테스트이므로 삭제)
        print(f"\n  fork 세션 삭제 중... (테스트 정리)")
        delete_session(result.session_id)
        print(f"    삭제 완료")

    except (ValueError, FileNotFoundError) as e:
        print(f"    결과: 실패 — {e}")


# ─────────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────────

def main():
    # 시나리오 1: 목록 조회
    sessions = scenario_list()

    if not sessions:
        print("\n" + "=" * 60)
        print("세션이 없으므로 시나리오 2~4를 건너뜁니다.")
        print("Claude Code CLI에서 대화를 한 번 진행하면 세션이 생성됩니다.")
        print("=" * 60)
        return

    # 가장 최근 세션으로 나머지 시나리오 진행
    target = sessions[0]
    print(f"\n  대상 세션 선택: {target.summary[:50]}")

    # 시나리오 2: 대화 내역
    scenario_messages(target)

    # 시나리오 3: 이름/태그 (세션 파일을 수정함)
    scenario_rename_tag(target)

    # 시나리오 4: fork (새 세션 파일 생성 후 삭제)
    scenario_fork(target)

    print("\n" + "=" * 60)
    print("모든 시나리오 완료")
    print("=" * 60)


if __name__ == "__main__":
    main()
