up:
	docker compose up --build

down:
	docker compose down

test:
	python -m pytest services/attendance-service/tests -q
	python -m pytest services/scheduling-service/tests -q
	python -m pytest services/ai-vision-service/tests -q

compile:
	python -m compileall -q libs/shared-core/shared_core services/*/app
