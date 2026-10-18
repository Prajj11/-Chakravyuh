ifeq ($(OS),Windows_NT)
PYTHON := .venv/Scripts/python.exe
else
PYTHON := .venv/bin/python
endif

.PHONY: setup dev test check smoke demo e2e

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

check:
	$(PYTHON) scripts/check.py

e2e:
	cd frontend && npm run test:e2e

smoke:
	$(PYTHON) scripts/smoke.py

demo: dev
