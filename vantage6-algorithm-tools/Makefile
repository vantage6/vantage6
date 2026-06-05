# `make` is expected to be called from the directory that contains
# this Makefile

TAG ?= latest

rebuild: clean build-dist

build-dist:
	# Build the PyPI package
	uv build

publish:
	# Uploading to pypi.org (workspace builds land in the root dist/)
	twine upload --repository pypi ../dist/vantage6_algorithm_tools*

clean:
	# Cleaning ...
	-rm -r build
	-rm dist/*