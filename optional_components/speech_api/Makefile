SHELL := /bin/bash

.PHONY: tests build-image run-tests clean-up

IMAGE_NAME := speech_test
CONTAINER_NAME := speech_test_container

# Default target to run tests inside Docker container
tests: setup-tests run-tests clean-tests

setup-tests:
	docker build -t $(IMAGE_NAME) .

run-tests:
	docker run --rm --name $(CONTAINER_NAME) \
		--entrypoint "pytest" \
		$(IMAGE_NAME) --color=yes -rPQ tests/*

clean-tests:
	docker container prune -f
	docker image prune -f
