.PHONY: help install run dev test format lint clean

help:
	@echo "Backend API - Available Commands"
	@echo "================================"
	@echo "make install    - Install dependencies"
	@echo "make run        - Run production server"
	@echo "make dev        - Run development server with hot-reload"
	@echo "make test       - Run tests"
	@echo "make format     - Format code with black and isort"
	@echo "make lint       - Run linters (flake8, mypy)"
	@echo "make clean      - Remove cache files and directories"

install:
	pip install -r requirements.txt

run:
	python -m uvicorn src.main:app --host 0.0.0.0 --port 8000

dev:
	python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest -v --cov=src

test-watch:
	pytest-watch -- -v --cov=src

format:
	black src tests
	isort src tests

lint:
	flake8 src tests
	mypy src

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name .coverage -exec rm -rf {} +
	find . -name "*.pyc" -delete
