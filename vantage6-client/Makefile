# `make` is expected to be called from the directory that contains
# this Makefile

TAG ?= latest

rebuild: clean build-dist

build-dist:
	# Build the PyPI package
	python setup.py sdist bdist_wheel

publish-test:
	# Uploading to test.pypi.org
	twine upload --repository testpypi dist/*

publish:
	# Uploading to pypi.org
	twine upload --repository pypi dist/*

clean:
	# Cleaning ...
	-rm -r build
	-rm dist/*
