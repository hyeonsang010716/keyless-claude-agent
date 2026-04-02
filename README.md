# Keyless Claude Agent Server

API Key 없이 OAuth만으로 동작하는 셀프호스트 Claude Agent HTTP 서버입니다.   

## 구조

```
.
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh       # OAuth 토큰 주입 스크립트
├── .env.example        # 토큰 템플릿
├── .dockerignore
├── pyproject.toml      # Python 의존성 (uv)
├── uv.lock
├── main.py             # FastAPI 서버
├── workspace/          # 에이전트 작업 디렉토리 (마운트됨)
└── README.md
```

## 사용법

### 1. 토큰 생성

호스트에서 Claude Code CLI가 설치되어 있어야 합니다.

```bash
claude setup-token
```

출력된 `sk-ant-oat01-...` 토큰을 복사합니다.

### 2. 환경변수 설정

```bash
cp .env.example .env
# .env 파일을 열어서 토큰을 붙여넣기
```

### 3. 실행

```bash
docker compose up --build
```

### 4. API 사용

**동기 요청:**

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"prompt": "hello.py 만들어줘"}'
```

**스트리밍 요청 (SSE):**

```bash
curl -N -X POST http://localhost:8000/query/stream \
  -H "Content-Type: application/json" \
  -d '{"prompt": "피보나치 함수 작성해줘"}'
```

## API 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
|---|---|---|
| `/health` | GET | 헬스체크 |
| `/query` | POST | 동기식 전체 응답 |
| `/query/stream` | POST | SSE 스트리밍 응답 |

## 요청 파라미터

```json
{
  "prompt": "수행할 작업",
  "system_prompt": "시스템 프롬프트 (선택)",
  "allowed_tools": ["Read", "Write", "Edit", "Bash", "Glob"],
  "max_turns": null,
  "model": null
}
```

## 주의사항

- **개인용**으로만 사용하세요. 제3자에게 서비스하려면 API 키 인증을 사용해야 합니다.
- `.env` 파일은 절대 git에 커밋하지 마세요.
- `workspace/` 디렉토리가 에이전트의 작업 공간으로 마운트됩니다.
