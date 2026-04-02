"""
Claude Agent SDK - 개인용 Docker 서비스
FastAPI 서버로 HTTP API를 통해 Claude Agent에 접근
"""

import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
)


# ─── 요청/응답 모델 ────────────────────────────────────────

class QueryRequest(BaseModel):
    prompt: str
    system_prompt: str | None = None
    allowed_tools: list[str] = Field(
        default=["Read", "Write", "Edit", "Bash", "Glob"],
        description="자동 승인할 도구 목록",
    )
    max_turns: int | None = None
    model: str | None = None


class QueryResponse(BaseModel):
    result: str
    usage: dict | None = None


# ─── FastAPI 앱 ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("✅ Claude Agent 서비스 시작")
    yield
    print("🛑 Claude Agent 서비스 종료")


app = FastAPI(
    title="Claude Agent Service",
    description="개인용 Claude Agent SDK Docker 서비스",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
async def run_query(req: QueryRequest):
    """동기식 응답 - 전체 결과를 모아서 반환"""
    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        allowed_tools=req.allowed_tools,
        cwd="/app/workspace"
    )
    if req.system_prompt:
        options.system_prompt = req.system_prompt
    if req.max_turns:
        options.max_turns = req.max_turns
    if req.model:
        options.model = req.model

    result_text = ""
    try:
        async for message in query(prompt=req.prompt, options=options):
            if isinstance(message, ResultMessage):
                result_text = getattr(message, "result", str(message))
            elif isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        result_text += block.text
    except Exception as e:
        import traceback, os

        # SDK의 "Check stderr output for details"는 하드코딩 문자열이라
        # 실제 원인 파악을 위해 가능한 모든 정보를 로깅
        error_detail = {
            "error": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc(),
            "env_check": {
                "CLAUDE_CODE_OAUTH_TOKEN": "SET" if os.getenv("CLAUDE_CODE_OAUTH_TOKEN") else "NOT SET",
                "HOME": os.getenv("HOME"),
                "NODE_VERSION": os.popen("node --version 2>&1").read().strip(),
                "claude_json_exists": os.path.exists(os.path.expanduser("~/.claude.json")),
            },
        }
        print(f"❌ Query 실패: {json.dumps(error_detail, indent=2, ensure_ascii=False)}")
        raise HTTPException(status_code=500, detail=error_detail)

    return QueryResponse(result=result_text)


@app.post("/query/stream")
async def run_query_stream(req: QueryRequest):
    """스트리밍 응답 - SSE로 메시지를 실시간 전달"""

    async def event_stream():
        options = ClaudeAgentOptions(
            permission_mode="bypassPermissions",
            allowed_tools=req.allowed_tools,
        )
        if req.system_prompt:
            options.system_prompt = req.system_prompt
        if req.max_turns:
            options.max_turns = req.max_turns
        if req.model:
            options.model = req.model

        try:
            async for message in query(prompt=req.prompt, options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            data = json.dumps(
                                {"type": "text", "content": block.text},
                                ensure_ascii=False,
                            )
                            yield f"data: {data}\n\n"
                        elif isinstance(block, ToolUseBlock):
                            data = json.dumps(
                                {
                                    "type": "tool_use",
                                    "tool": block.name,
                                    "input": block.input,
                                },
                                ensure_ascii=False,
                            )
                            yield f"data: {data}\n\n"
                elif isinstance(message, ResultMessage):
                    data = json.dumps(
                        {
                            "type": "result",
                            "content": getattr(message, "result", str(message)),
                        },
                        ensure_ascii=False,
                    )
                    yield f"data: {data}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            error_data = json.dumps(
                {"type": "error", "content": str(e)},
                ensure_ascii=False,
            )
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
