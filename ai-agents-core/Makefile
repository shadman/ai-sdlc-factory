# AI Factory Orchestrator Makefile

.PHONY: test-jira test-ci setup help

help:
	@echo "Available commands:"
	@echo "  make test-jira    : Runs the full Python Jira lifecycle simulation"
	@echo "  make test-ci      : Runs the shell script for CI/CD repair simulation"
	@echo "  make setup        : Sets up test permissions"

setup:
	chmod +x tests/test_ci_trigger.sh

test-jira:
	@echo "--- 🧪 Running Full Jira Lifecycle Simulation ---"
	python3 tests/test_jira_flow.py

test-ci:
	@echo "--- ⚡ Running CI/CD Auto-Repair Simulation ---"
	./tests/test_ci_trigger.sh

# If you need to clean up Redis state for a fresh test
clean-state:
	@echo "--- 🧹 Clearing Redis Task State ---"
	docker exec -it redis redis-cli flushall