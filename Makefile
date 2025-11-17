# Makefile for Discord Soundboard Generator
# Cross-platform build automation

# Python executable
PYTHON := python

# Version file
VERSION_FILE := .version

# Default version if file doesn't exist
DEFAULT_VERSION := 1.0.0

# Distribution directory
DIST_DIR := distributions

# Build directory
BUILD_DIR := build
PYINSTALLER_DIST := dist

.PHONY: help build clean install test version release

help:
	@echo "Discord Soundboard Generator - Build System"
	@echo ""
	@echo "Available commands:"
	@echo "  make build       - Build executable with automatic version increment"
	@echo "  make clean       - Remove build artifacts"
	@echo "  make install     - Install dependencies"
	@echo "  make version     - Show current version"
	@echo "  make test        - Test the application"
	@echo "  make release     - Create GitHub release with ZIP archive"
	@echo ""

build:
	@echo "Building Discord Soundboard Generator..."
	@$(PYTHON) build_versioned.py

clean:
	@echo "Cleaning build artifacts..."
	@if [ -d "$(BUILD_DIR)" ]; then rm -rf "$(BUILD_DIR)"; fi
	@if [ -d "$(PYINSTALLER_DIST)" ]; then rm -rf "$(PYINSTALLER_DIST)"; fi
	@echo "Build artifacts cleaned"

install:
	@echo "Installing dependencies..."
	@$(PYTHON) -m pip install -r requirements.txt
	@echo "Dependencies installed"

test:
	@echo "Running application..."
	@$(PYTHON) main.py

version:
	@if [ -f "$(VERSION_FILE)" ]; then \
		cat $(VERSION_FILE); \
	else \
		echo "$(DEFAULT_VERSION)"; \
	fi

release:
	@$(PYTHON) -c "v = open('.version').read().strip(); import os; os.system(f'powershell Compress-Archive -Path .\\distributions\\DiscordSoundboardGenerator_v{v} -DestinationPath .\\distributions\\DiscordSoundboardGenerator_v{v}.zip -Force'); os.system(f'git tag -a v{v} -m \"Discord Soundboard Generator v{v}\" 2>nul || echo Tag v{v} already exists'); os.system(f'git push origin v{v}'); os.system(f'gh release create v{v} --title \"Discord Soundboard Generator v{v}\" --notes \"Release v{v}\" .\\distributions\\DiscordSoundboardGenerator_v{v}.zip')"
