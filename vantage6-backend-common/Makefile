# `make` is expected to be called from the directory that contains
# this Makefile

TAG ?= latest

rebuild: clean build-dist

build-dist:
	# Build the PyPI package
	cp ../README.md .
	uv build
	rm README.md

publish:
	# Uploading to pypi.org
	twine upload --repository pypi dist/*

test:
	coverage run --source=vantage6 --omit="utest.py" ./utest.py

clean:
	# Cleaning ...
	-rm -r build
	-rm dist/*