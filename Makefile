.PHONY: up down migrate bot worker logs test

up:
	docker compose up -d

down:
	docker compose down

migrate:
	docker compose run --rm bot alembic upgrade head

bot:
	docker compose up bot

worker:
	docker compose up worker

logs:
	docker compose logs -f

test:
	pytest tests/ -v
