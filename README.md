# Let's Debate

LangChain-powered multi-agent AI debate app with a FastAPI backend and Next.js frontend.

## Demo Video

https://github.com/user-attachments/assets/9b83f6bd-cac6-4109-a7d0-5b057d778b10

## Tech Stack

- Backend: FastAPI, SQLAlchemy, Alembic, PostgreSQL, Pydantic
- AI: LangChain (OpenAI, Google Gemini, and Ollama chat model integrations)
- Frontend: Next.js (App Router), React, TypeScript, Zustand, Axios, CSS
- Realtime: WebSocket (FastAPI WebSocket endpoint + browser WebSocket client)
- Auth/Security: JWT (`python-jose`), password hashing (`pwdlib`), encrypted API-key storage (`cryptography`/Fernet)

## AI Engine (LangChain)

- LangChain is used in `backend/app/services/llm_service.py` to create provider-specific chat models via `init_chat_model(...)`.
- For each debate turn, the app builds a message history using `SystemMessage`, `HumanMessage`, and `AIMessage`, then streams model output token-by-token.
- Supported providers are OpenAI (`model_provider="openai"`), Gemini (`model_provider="google_genai"`), and Ollama (`model_provider="ollama"`) for local models.
- Debate orchestration (turn loop, pause/resume, message persistence, WS events) is handled by app services, while LangChain handles model invocation and message primitives.
- User API keys from profile settings are required for OpenAI and Gemini agents; missing keys block debate execution with a WS error. Ollama agents require no API key — only a running Ollama server.
- Available Ollama models are auto-detected from the local server and shown in a dropdown during debate creation.

## Quick Start

### 1) Start backend

From `backend/`:

```bash
uv sync
uv run uvicorn app.main:app --reload
```

Backend runs on `http://localhost:8000`.

### 2) Start frontend

From `frontend/`:

```bash
bun install
bun run dev
```

Frontend runs on `http://localhost:3000`.

## Environment Variables

### Backend (`backend/.env`)

Create `backend/.env`:

```dotenv
DATABASE_URL=postgresql+psycopg://debate_user:debate_pass@localhost:5432/ai_debate
SECRET_KEY=your-secret-key
```

Optional backend vars:

- `BACKEND_CORS_ORIGINS` (default allows `http://localhost:3000`)
- `ALGORITHM` (default `HS256`)
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `REFRESH_TOKEN_EXPIRE_DAYS`
- `REFRESH_TOKEN_CLEANUP_INTERVAL_SECONDS`
- `OLLAMA_BASE_URL` (default `http://localhost:11434`)
- `ENVIRONMENT`

### Frontend (`frontend/.env.local`)

Create `frontend/.env.local`:

```dotenv
BACKEND_URL=http://localhost:8000
```

Optional frontend vars:

- `NEXT_PUBLIC_API_URL` (default `/api/v1`)
- `NEXT_PUBLIC_WS_URL` (default derived from `NEXT_PUBLIC_API_URL`, else `ws://localhost:8000`)
- `NEXT_PUBLIC_FORCE_DIRECT_API=true` (bypass Next proxy and call API directly)
- `NEXT_PUBLIC_WITH_CREDENTIALS=true` (enable cookie credentials on Axios)

## Common URLs

- Frontend: `http://localhost:3000`
- Backend API docs: `http://localhost:8000/docs`
- Backend health: `http://localhost:8000/health`

## Local Models (Ollama)

To use local LLMs via [Ollama](https://ollama.com):

1. Install Ollama and start the server.
2. Pull a model: `ollama pull llama3.2`
3. In the debate creation form, select "Ollama (Local)" as the provider — available models are detected automatically.

Set `OLLAMA_BASE_URL` in `backend/.env` if Ollama runs on a non-default address.

## Notes

- Run database migrations before first use.
- If ports differ in your setup, update env values accordingly.

## Migrations

From `backend/`:

```bash
uv run alembic upgrade head
```
