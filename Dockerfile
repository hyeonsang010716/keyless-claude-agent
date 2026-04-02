# ============================================================
# Claude Agent SDK - Docker 개인용 서비스
#
# 핵심 포인트:
#   - .claude.json에 hasCompletedOnboarding: true (온보딩 위저드 우회)
#   - Node.js 20 설치 (번들 CLI가 내부적으로 필요)
#   - entrypoint.sh에서 OAuth 토큰을 .claude.json에 주입
#   - 비루트 사용자로 실행
#
# 사용법:
#   1. 호스트에서 토큰 생성: claude setup-token
#   2. .env 파일에 토큰 입력
#   3. docker compose up --build
# ============================================================

FROM python:3.12-slim

# 시스템 의존성 + Node.js 20 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        git \
        ripgrep \
        jq \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 비루트 사용자 생성
RUN groupadd -r claude && useradd -r -g claude -m -s /bin/bash claude

# ─── 온보딩 우회 설정 ───────────────────────────────────────
# Claude CLI는 .claude.json에 hasCompletedOnboarding이 없으면
# 대화형 온보딩을 시도 → TTY 없는 Docker에서 exit code 1로 죽음
RUN mkdir -p /home/claude/.claude \
    && echo '{"hasCompletedOnboarding": true}' > /home/claude/.claude.json \
    && chown -R claude:claude /home/claude/.claude /home/claude/.claude.json

WORKDIR /app

# Python 의존성
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# 애플리케이션 코드
COPY --chown=claude:claude . .

# workspace 디렉토리
RUN mkdir -p /app/workspace && chown -R claude:claude /app/workspace

# entrypoint 스크립트
COPY --chown=claude:claude entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER claude

ENV PYTHONUNBUFFERED=1
ENV CLAUDE_CODE_DISABLE_UPDATE_CHECK=1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "main.py"]
