.PHONY: help build run stop clean test lint format dev-install

help:
	@echo "Available commands:"
	@echo "  make build       - Build Docker image"
	@echo "  make run         - Run services with docker-compose"
	@echo "  make stop        - Stop all services"
	@echo "  make clean       - Stop services and remove volumes"
	@echo "  make test        - Run tests"
	@echo "  make lint        - Run linting"
	@echo "  make format      - Format code with black"
	@echo "  make dev-install - Install development dependencies"

build:
	docker-compose build

run:
	docker-compose up -d
	@echo "URL Reputation Checker is running at http://localhost:5000"
	@echo "Redis is running at localhost:6379"

stop:
	docker-compose down

clean:
	docker-compose down -v
	rm -rf __pycache__ .pytest_cache .mypy_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

test:
	pytest tests/ -v

lint:
	ruff url_reputation_checker/
	mypy url_reputation_checker/

format:
	black url_reputation_checker/

dev-install:
	pip install -e ".[dev]"

logs:
	docker-compose logs -f

restart:
	docker-compose restart mcp-server

redis-cli:
	docker exec -it url-reputation-redis redis-cli