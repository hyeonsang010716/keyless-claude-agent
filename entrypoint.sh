#!/bin/bash
set -e

# ─── OAuth 토큰 → .claude.json 주입 ─────────────────────────
# claude_agent_sdk는 내부적으로 Claude CLI를 subprocess로 실행하는데,
# CLI가 ~/.claude.json에서 인증 정보를 읽음.
# CLAUDE_CODE_OAUTH_TOKEN 환경변수가 있으면 .claude.json에 자동 설정.

CLAUDE_JSON="$HOME/.claude.json"

if [ -n "$CLAUDE_CODE_OAUTH_TOKEN" ]; then
    echo "✅ OAuth 토큰 감지 → .claude.json에 인증 정보 설정 중..."

    # 기존 파일이 있으면 읽고, 없으면 기본값
    if [ -f "$CLAUDE_JSON" ]; then
        EXISTING=$(cat "$CLAUDE_JSON")
    else
        EXISTING='{}'
    fi

    # jq로 필요한 필드 주입
    echo "$EXISTING" | jq \
        --arg token "$CLAUDE_CODE_OAUTH_TOKEN" \
        '. + {
            "hasCompletedOnboarding": true,
            "oauthAccount": (.oauthAccount // {
                "emailAddress": "docker@claude-agent.local",
                "organizationName": "Docker Agent"
            })
        }' > "$CLAUDE_JSON"

    echo "✅ .claude.json 설정 완료"
else
    echo "⚠️  CLAUDE_CODE_OAUTH_TOKEN이 설정되지 않았습니다."
    echo "   → .env 파일에 토큰을 설정하거나 -e 플래그로 전달하세요."
    echo "   → 토큰 생성: claude setup-token"

    # 온보딩 플래그는 최소한 설정
    if [ ! -f "$CLAUDE_JSON" ]; then
        echo '{"hasCompletedOnboarding": true}' > "$CLAUDE_JSON"
    fi
fi

echo "─────────────────────────────────────────"
echo "📋 현재 설정:"
echo "   HOME=$HOME"
echo "   .claude.json 존재: $([ -f $CLAUDE_JSON ] && echo 'YES' || echo 'NO')"
echo "   OAuth 토큰: $([ -n \"$CLAUDE_CODE_OAUTH_TOKEN\" ] && echo 'SET' || echo 'NOT SET')"
echo "   Node.js: $(node --version 2>/dev/null || echo 'NOT FOUND')"
echo "   Python: $(python --version 2>/dev/null || echo 'NOT FOUND')"
echo "─────────────────────────────────────────"

# CMD 실행
exec "$@"
