ifeq ($(OS),Windows_NT)
PYTHON := .venv/Scripts/python.exe
else
PYTHON := .venv/bin/python
endif

.PHONY: setup dev test check smoke demo

setup:
ifeq ($(OS),Windows_NT)
	cmd /c start.bat --setup
else
	./scripts/setup.sh
endif

dev:
ifeq ($(OS),Windows_NT)
	cmd /c start.bat
else
	./scripts/dev.sh
endif

test:
	$(PYTHON) -m pytest backend/tests -q

check: test
	$(PYTHON) -m ruff check backend scripts/smoke.py
	$(PYTHON) -m ruff format --check backend scripts/smoke.py
	$(PYTHON) -m mypy backend/app --ignore-missing-imports
	$(PYTHON) backend/scripts/generate_types.py --check
	cd frontend && npm run typecheck
	cd frontend && npm run format:check
	cd frontend && npm run build
	$(PYTHON) scripts/smoke.py

smoke:
	$(PYTHON) scripts/smoke.py

demo: dev
