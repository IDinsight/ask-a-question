SHELL := /bin/bash

.PHONY: tests build-image run-tests clean-up

IMAGE_NAME := my_test_image
CONTAINER_NAME := my_test_container

# Default target to run tests inside Docker container
tests: build-image run-tests clean-up

build-image:
	docker build -t $(IMAGE_NAME) .

run-tests:
	docker run --rm --name $(CONTAINER_NAME) \
		--entrypoint "pytest" \
		$(IMAGE_NAME) --color=yes -rPQ tests/*

clean-up:
	docker container prune -f
	docker image prune -f
