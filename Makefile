.PHONY: up down test migrate logs ps

up:
	docker compose up --build

down:
	docker compose down

# Runs each service's test suite inside its own container
test:
	docker compose run --rm scheduling-service pytest
	docker compose run --rm attendance-service pytest
	docker compose run --rm ai-vision-service pytest

# Runs alembic migrations for services that have a migrations/ folder set up
migrate:
	docker compose run --rm scheduling-service alembic upgrade head
	docker compose run --rm attendance-service alembic upgrade head

logs:
	docker compose logs -f

ps:
	docker compose ps
