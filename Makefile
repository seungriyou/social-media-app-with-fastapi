.PHONY: help
help:
	@echo "[ Available tasks ]"
	@echo " install	: Install dependencies for production"
	@echo " install-dev	: Install dependencies for development"
	@echo " run		: Run application"
	@echo " test		: Run test suite"
	@echo " lint		: Fix with linter"
	@echo " lint-check	: Check with linter"
	@echo " tree		: Show project directory structure as tree"
	@echo " help		: Display this help message"

.PHONY: install
install:
	poetry install --without dev

.PHONY: install-dev
install-dev:
	poetry install

.PHONY: run
run:
	uvicorn socialapi.main:app --reload

.PHONY: test
test:
	pytest .

.PHONY: lint
lint:
	ruff format . && ruff check --fix .

.PHONY: lint-check
lint-check:
	ruff format --check . && ruff check .

.PHONY: tree
tree:
	tree -a -I '__pycache__|*.pyc|*.pyo|.pytest_cache|.venv|.git|.idea|__init__.py'

# .PHONY: run
# run:
# 	poetry run alembic upgrade head && poetry run uvicorn src.main:app --reload

# .PHONY: migrate
# migrate:
# 	poetry run alembic revision --autogenerate && poetry run alembic upgrade head

# .PHONY: install
# install:
# 	pip install -U poetry && poetry install

# .PHONY: update
# update:
# 	poetry update
