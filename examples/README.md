# Examples

Claude Agent SDK 블로그 시리즈의 예시 코드입니다.

## 사전 준비

```bash
# Claude Code CLI에 로그인되어 있거나, OAuth 토큰을 설정하세요.
claude setup-token
export CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-...
```

## 예시 목록

| 파일 | 블로그 편 | 핵심 내용 | 실행 |
|---|---|---|---|
| `1_basic_query.py` | 1편 서버 만들기 | `query()` 기본 호출, 파일 생성 | `uv run examples/1_basic_query.py` |
| `2_options_showcase.py` | 2편 옵션 가이드 | plan 모드, thinking, 구조화 출력 3가지 시나리오 | `uv run examples/2_options_showcase.py` |
| `3_message_types.py` | 3편 메시지 타입 | 모든 메시지/블록 타입을 분류 출력하는 핸들러 | `uv run examples/3_message_types.py` |
| `4_error_handling.py` | 4편 에러 처리 | 정상/잘못된 cwd/도구 에러 3가지 시나리오 | `uv run examples/4_error_handling.py` |
| `5_permission_system.py` | 5편 권한 심화 | 감사 로그, 위험 명령 차단, 경로 격리 3가지 시나리오 | `uv run examples/5_permission_system.py` |
| `6_hook_system.py` | 6편 훅 시스템 | 도구 로깅, Bash 차단, 경로 강제 변환 3가지 시나리오 | `uv run examples/6_hook_system.py` |
| `7_mcp_server.py` | 7편 MCP 서버 | 계산기, 앱 상태 노출, 복수 서버 조합 3가지 시나리오 | `uv run examples/7_mcp_server.py` |
| `8_session_management.py` | 8편 세션 관리 | 목록 조회, 대화 열람, 이름/태그, fork 4가지 시나리오 | `uv run examples/8_session_management.py` |
| `9_agent_definition.py` | 9편 에이전트 정의 | 분석자+실행자, 모델별 역할 분배+태스크 모니터링 2가지 시나리오 | `uv run examples/9_agent_definition.py` |
