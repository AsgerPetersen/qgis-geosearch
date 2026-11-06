# Developer tasks for Geosearch DK.
#
#   make dev             symlink the plugin into the "geosearch-dev" profile and start QGIS 4
#   make dev QGIS=3      same, with QGIS 3 (Qt5)
#   make visual          run tests/manual/visual_run.py in QGIS and write out/report.html
#   make help            list all targets and variables
#
# The plugin's packaging Makefile is src/geosearch_dk/Makefile; this file is
# only for the development loop. Add new targets (test, test-qgis, test-live,
# mock, ...) in their own section below "Development loop".
#
# See docs/development.md (Windows, Linux, Plugin Reloader, macOS 27 crash).

SHELL := /bin/bash
.DEFAULT_GOAL := help

PLUGIN_NAME := geosearch_dk
PLUGIN_SRC  := $(CURDIR)/src/$(PLUGIN_NAME)

# QGIS major version: 4 (Qt6) or 3 (Qt5). The plugin supports both.
QGIS    ?= 4
# Separate QGIS profile, so a released plugin in the "default" profile is left alone
PROFILE ?= geosearch-dev

UNAME_S := $(shell uname -s)

ifeq ($(UNAME_S),Darwin)
  # Newest QGIS*.app in /Applications or ~/Applications whose version starts
  # with $(QGIS); a "*patched*" copy (make macos-patch-qgis) wins a tie.
  # Override with QGIS_APP=/path/to/QGIS.app
  ifeq ($(origin QGIS_APP),undefined)
  QGIS_APP := $(shell for a in /Applications/QGIS*.app "$(HOME)"/Applications/QGIS*.app; do \
      [ -f "$$a/Contents/Info.plist" ] || continue; \
      v=$$(/usr/libexec/PlistBuddy -c 'Print CFBundleShortVersionString' "$$a/Contents/Info.plist" 2>/dev/null); \
      case "$$a" in (*patched*) p=1;; (*) p=0;; esac; \
      case "$$v" in ($(QGIS).*) echo "$$v $$p $$a";; esac; \
    done | sort -V | tail -n 1 | cut -d' ' -f3-)
  endif
  QGIS_USER_DIR ?= $(HOME)/Library/Application Support/QGIS/QGIS$(QGIS)
  PROFILE_INI    = $(PROFILE_DIR)/qgis.org/QGIS$(QGIS).ini
else
  # Linux. Set QGIS_BIN if QGIS 3 and 4 are installed side by side
  QGIS_BIN ?= qgis
  QGIS_USER_DIR ?= $(HOME)/.local/share/QGIS/QGIS$(QGIS)
  PROFILE_INI    = $(PROFILE_DIR)/QGIS/QGIS$(QGIS).ini
endif

PROFILES_INI := $(QGIS_USER_DIR)/profiles/profiles.ini
PROFILE_DIR  := $(QGIS_USER_DIR)/profiles/$(PROFILE)
PLUGINS_DIR  := $(PROFILE_DIR)/python/plugins
PLUGIN_LINK  := $(PLUGINS_DIR)/$(PLUGIN_NAME)

# QGIS records --profile as the last used profile, so a plain start of QGIS
# would open the dev profile. These save and restore it around a run.
SAVE_LAST_PROFILE    = export last=$$(sed -n 's/^lastProfile=//p' "$(PROFILES_INI)" 2>/dev/null)
RESTORE_LAST_PROFILE = if [ -n "$$last" ]; then perl -pi -e "s/^lastProfile=.*/lastProfile=$$last/" "$(PROFILES_INI)"; fi

# Visual run (tests/manual/visual_run.py)
CASES        ?= $(firstword $(wildcard tests/cases.yaml) tests/manual/sample_cases.yaml)
OUT          ?= out
ONLY         ?=
VISUAL_ARGS  ?=
VISUAL_RUN_ARGS = --cases '$(abspath $(CASES))' --out '$(abspath $(OUT))' $(if $(ONLY),--only '$(ONLY)') --quit $(VISUAL_ARGS)

.PHONY: help
help: ## Show targets and variables
	@echo "Targets:"
	@grep -E '^[a-zA-Z0-9_-]+:.*## ' $(MAKEFILE_LIST) | awk -F ':.*## ' '{ printf "  %-17s %s\n", $$1, $$2 }'
	@echo
	@echo "Variables (current value):"
	@echo "  QGIS=$(QGIS)  PROFILE=$(PROFILE)"
ifeq ($(UNAME_S),Darwin)
	@echo "  QGIS_APP=$(QGIS_APP)"
else
	@echo "  QGIS_BIN=$(QGIS_BIN)"
endif
	@echo "  PROFILE_DIR=$(PROFILE_DIR)"
	@echo "  CASES=$(CASES)  OUT=$(OUT)  ONLY=$(ONLY)"

# --- Development loop -------------------------------------------------------

.PHONY: check-qgis
check-qgis:
ifeq ($(UNAME_S),Darwin)
	@[ -n "$(QGIS_APP)" ] || { echo "No QGIS $(QGIS).x found in /Applications. Set QGIS_APP=/path/to/QGIS.app" >&2; exit 1; }
else
	@command -v "$(QGIS_BIN)" >/dev/null || { echo "$(QGIS_BIN) not found. Set QGIS_BIN=/path/to/qgis" >&2; exit 1; }
endif

.PHONY: dev
dev: check-qgis dev-link ## Symlink the plugin into the dev profile and start QGIS (QGIS=4 or 3)
ifeq ($(UNAME_S),Darwin)
	@echo "Starting $(QGIS_APP) with --profile $(PROFILE)"
	@$(SAVE_LAST_PROFILE); \
	  nohup bash -c 'open -n -W -a "$(QGIS_APP)" --args --profile "$(PROFILE)"; $(RESTORE_LAST_PROFILE)' >/dev/null 2>&1 &
else
	@echo "Starting $(QGIS_BIN) with --profile $(PROFILE)"
	@$(SAVE_LAST_PROFILE); \
	  nohup bash -c '"$(QGIS_BIN)" --profile "$(PROFILE)"; $(RESTORE_LAST_PROFILE)' >/dev/null 2>&1 &
endif

.PHONY: dev-link
dev-link: ## Only create the dev profile and the plugin symlink
	@mkdir -p "$(PLUGINS_DIR)"
	@if [ -e "$(PLUGIN_LINK)" ] && [ ! -L "$(PLUGIN_LINK)" ]; then \
	  echo "$(PLUGIN_LINK) exists and is not a symlink. Remove it first." >&2; exit 1; \
	fi
	@ln -sfn "$(PLUGIN_SRC)" "$(PLUGIN_LINK)"
	@echo "Linked $(PLUGIN_LINK) -> $(PLUGIN_SRC)"
	@# A new profile has no settings file yet: create one with the plugin enabled.
	@# An existing settings file is never modified.
	@if [ ! -f "$(PROFILE_INI)" ]; then \
	  mkdir -p "$$(dirname "$(PROFILE_INI)")"; \
	  printf '[PythonPlugins]\n$(PLUGIN_NAME)=true\n' > "$(PROFILE_INI)"; \
	  echo "Created $(PROFILE_INI) with $(PLUGIN_NAME) enabled"; \
	fi

.PHONY: dev-unlink
dev-unlink: ## Remove the plugin symlink from the dev profile (keeps the profile)
	@if [ -L "$(PLUGIN_LINK)" ]; then rm "$(PLUGIN_LINK)" && echo "Removed $(PLUGIN_LINK)"; else echo "No symlink at $(PLUGIN_LINK)"; fi

.PHONY: visual
visual: check-qgis dev-link ## Run the visual run in QGIS, then quit (CASES=..., ONLY=id1,id2, OUT=out)
	@mkdir -p "$(OUT)"
ifeq ($(UNAME_S),Darwin)
	@echo "Running the visual run in $(QGIS_APP) (log: $(OUT)/qgis.log)"
	@# Started through `open`: QGIS 4 crashes when its binary is started directly
	@$(SAVE_LAST_PROFILE); \
	  open -n -W -a "$(QGIS_APP)" --env "VISUAL_RUN_ARGS=$(VISUAL_RUN_ARGS)" \
	    --stdout "$(abspath $(OUT))/qgis.log" --stderr "$(abspath $(OUT))/qgis.log" \
	    --args --profile "$(PROFILE)" --nologo --code "$(CURDIR)/tests/manual/visual_run.py"; \
	  $(RESTORE_LAST_PROFILE)
	@grep -F '[visual_run]' "$(OUT)/qgis.log" || true
else
	@$(SAVE_LAST_PROFILE); \
	  VISUAL_RUN_ARGS="$(VISUAL_RUN_ARGS)" "$(QGIS_BIN)" --profile "$(PROFILE)" --nologo \
	    --code "$(CURDIR)/tests/manual/visual_run.py"; \
	  $(RESTORE_LAST_PROFILE)
endif
	@[ -f "$(OUT)/report.html" ] || { echo "No report was written. See $(OUT)/qgis.log" >&2; exit 1; }
	@echo "Report: $(abspath $(OUT))/report.html"

.PHONY: macos-patch-qgis
macos-patch-qgis: check-qgis ## macOS 27: make a patched QGIS copy in ~/Applications that does not crash at start
	python3 scripts/macos_patch_qgis.py "$(QGIS_APP)" \
	  "$(HOME)/Applications/$(basename $(notdir $(QGIS_APP)))-patched.app"
