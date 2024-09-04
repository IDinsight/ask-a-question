.PHONY: tests

tests: setup-tests run-tests clean-tests

run-tests:
	@set -a && source ./tests/test.env && set +a && \
	python -m pytest -rPQ tests

setup-tests:
	set -a && source ./tests/test.env && set +a && \
	mkdir -p $$WHISPER_MODEL_DIR && \
	chmod -R 755 $$WHISPER_MODEL_DIR && \
	mkdir -p $$PIPER_MODELS_DIR && \
	chmod -R 755 $$PIPER_MODELS_DIR && \
	pip install -r requirements.txt && \
	curl -OL https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/arctic/medium/en_US-arctic-medium.onnx && \
	curl -OL https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/arctic/medium/en_US-arctic-medium.onnx.json && \
	curl -OL https://huggingface.co/rhasspy/piper-voices/resolve/main/sw/sw_CD/lanfrica/medium/sw_CD-lanfrica-medium.onnx && \
	curl -OL https://huggingface.co/rhasspy/piper-voices/resolve/main/sw/sw_CD/lanfrica/medium/sw_CD-lanfrica-medium.onnx.json && \
	mv en_US-arctic-medium.onnx $$PIPER_MODELS_DIR/ && \
	mv en_US-arctic-medium.onnx.json $$PIPER_MODELS_DIR/ && \
	mv sw_CD-lanfrica-medium.onnx $$PIPER_MODELS_DIR/ && \
	mv sw_CD-lanfrica-medium.onnx.json $$PIPER_MODELS_DIR/

clean-tests:
	@set -a && source ./tests/test.env && set +a && \
	rm -rf $$WHISPER_MODEL_DIR $$PIPER_MODELS_DIR
