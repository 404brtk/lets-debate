Generic single-database configuration.

Run commands:

- Create revision:
  uv run alembic revision --autogenerate -m "message"

- Apply migrations:
  uv run alembic upgrade head

- Show current revision:
  uv run alembic current
