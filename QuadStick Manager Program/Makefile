# Makefile for QuadStick Manager Program — macOS development and build
# (Windows builds still use build.bat and QuadStick.spec)
SERVICE = QuadStick Manager Program

# Variables
VENV_DIR = .venv
PYTHON = $(VENV_DIR)/bin/python
PIP = $(VENV_DIR)/bin/pip

.PHONY: help install clean run test build

# ── Environment ──────────────────────────────────────────────────────────────

help: ## Print this help message
	@printf '\033[01;32m${SERVICE} — macOS development and build\033[00;37m\n\n'
	@printf "\033[33mUsage:\033[0m\n  make [target] [arg=\"val\"...]\n\n\033[33mTargets:\033[0m\n"
	@grep -E '^[-a-zA-Z0-9_\.\/]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; \
		{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

install: ## Initialize the venv and install all dependencies
	@if [ ! -d "$(VENV_DIR)" ]; then \
		python3 -m venv $(VENV_DIR); \
		$(PIP) install -U pip; \
		$(PIP) install -r requirements-macos.txt; \
	fi; \
	echo "Environment setup complete."

clean: ## Remove venv, build output, and all temporary files
	rm -rf $(VENV_DIR) build dist
	find . -type d -name "__pycache__" -exec rm -rf {} +
	@echo "Cleanup complete."

# ── Development ──────────────────────────────────────────────────────────────

run: install ## Run QMP from source (usage: make run [debug=1])
	$(PYTHON) QuadStick.py $(if $(debug),-debug)

test: install ## Run the self-checks (HID report parser, build number recovery)
	$(PYTHON) hidcompat.py
	$(PYTHON) qsflash.py

# ── Build ────────────────────────────────────────────────────────────────────

build: install ## Build dist/QuadStick.app
	$(PYTHON) -m PyInstaller --clean --noconfirm QuadStick-macos.spec
