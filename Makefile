_python_pkg := github_metrics

results_dir ?= results

export ACCESS_TOKEN=$(shell secret-tool lookup datawrapper-github personal-access-token-metrics)

.PHONY: run
run: $(results_dir)/stats.csv  ## Run

$(results_dir)/stats.csv: | $(results_dir)
	./github-metrics -v \
		--owner datawrapper --repo code \
		--cache cache \
		--data $(results_dir)/data.csv \
		--stats-daily $(results_dir)/stats_daily.csv \
		--stats-weekly $(results_dir)/stats_weekly.csv

$(results_dir):
	mkdir -p "$@"

.PHONY: setup
setup:  ## Create virtual environment and install dependencies.
	poetry install

.PHONY: test
test:  ## Run unit tests
	poetry run python -m unittest

.PHONY: lint
lint:  ## Run linting
	poetry run flake8 $(_python_pkg)
	poetry run mypy $(_python_pkg) --ignore-missing-imports
	poetry run isort -c $(_python_pkg)

.PHONY: reformat
reformat:  ## Reformat Python code using Black
	black -l 79 --skip-string-normalization $(_python_pkg)
	poetry run isort -rc $(_python_pkg)

.PHONY: python-shell
python-shell:  ## Run Python shell with all dependencies installed
	poetry run ipython --no-banner --no-confirm-exit

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'
