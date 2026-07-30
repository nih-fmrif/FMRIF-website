CMN_PELICAN := /Users/molfesepj/Documents/Programming/cmn-website-2026/.venv/bin/pelican

ifeq ($(shell command -v pelican 2>/dev/null),)
ifneq ($(wildcard $(CMN_PELICAN)),)
PELICAN ?= $(CMN_PELICAN)
else
PELICAN ?= pelican
endif
else
PELICAN ?= pelican
endif
PELICANOPTS ?=

BASEDIR := $(CURDIR)
INPUTDIR := $(BASEDIR)/content
OUTPUTDIR := $(BASEDIR)/output
CONFFILE := $(BASEDIR)/pelicanconf.py
PUBLISHCONF := $(BASEDIR)/publishconf.py

.PHONY: help build clean rebuild serve publish

help:
	@echo "make build    Build the development site"
	@echo "make serve    Build, watch, and serve at http://127.0.0.1:8000"
	@echo "make publish  Build production site for https://fmrif.nimh.nih.gov"
	@echo "make clean    Remove generated output"

build:
	"$(PELICAN)" "$(INPUTDIR)" -o "$(OUTPUTDIR)" -s "$(CONFFILE)" $(PELICANOPTS)

clean:
	rm -rf "$(OUTPUTDIR)"

rebuild: clean build

serve:
	"$(PELICAN)" "$(INPUTDIR)" -o "$(OUTPUTDIR)" -s "$(CONFFILE)" -r -l $(PELICANOPTS)

publish:
	"$(PELICAN)" "$(INPUTDIR)" -o "$(OUTPUTDIR)" -s "$(PUBLISHCONF)" $(PELICANOPTS)
