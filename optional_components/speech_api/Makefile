.PHONY: tests

# Main test target
tests: setup-tests run-tests clean-tests

# Test runner
run-tests:
	@set -a && source ./tests/test.env && set +a && \
	python -m pytest -rPQ tests

# Target to create the directory with the correct permissions
setup-tests:
	set -a && source ./tests/test.env && set +a && \
	mkdir -p $$WHISPER_MODEL_DIR && \
	chmod -R 755 $$WHISPER_MODEL_DIR

clean-tests:
	@set -a && source ./tests/test.env && set +a && \
	rm -rf $$WHISPER_MODEL_DIR
