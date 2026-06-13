.PHONY: dev backend-test backend-lint frontend-typecheck

dev:
	docker compose up --build

backend-test:
	cd backend && python -m pytest

backend-lint:
	cd backend && ruff check app tests

frontend-typecheck:
	cd frontend && npm run typecheck
