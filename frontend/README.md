# Frontend

Next.js App Router frontend for `lets-debate`.

## Requirements

- Node.js 20+
- Backend running on `http://localhost:8000`

## Environment

Create `.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

## Run

```bash
bun install
bun run dev
```

Open `http://localhost:3000`.

## Auth Flow

- `POST /auth/login`
- `POST /auth/register`
- `POST /auth/refresh` on `401`
- `GET /auth/me` for profile
