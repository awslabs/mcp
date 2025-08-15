.PHONY: install test run clean

install:
	pip install -e .[test]
	@echo "✅ Installation complete"

test:
	python -m pytest tests/unit/ -v
	@echo "✅ Tests passed"

install-and-test: install test
	@echo "✅ Ready to run server"

run: install-and-test
	awslabs.etl-replatforming-mcp-server

clean:
	pip uninstall awslabs.etl-replatforming-mcp-server -y
