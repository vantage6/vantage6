# `make` is expected to be called from the directory that contains
# this Makefile

TAG ?= trolltunga
BUILDNR ?= 1
BRANCH ?= master

help:
	@echo "Available commands to 'make':"
	@echo "  set-version  : set version (e.g set-version FLAGS=\"--version 2.0.0 --build 0 --spec alpha\")"
	@echo "  uninstall    : uninstall all vantage6 packages"
	@echo "  install      : do a regular install of all vantage6 packages"
	@echo "  install-dev  : do an editable install of all vantage6 packages"
	@echo "  image 		  : build the node/server docker image"
	@echo "  docker-push  : push the node/server docker image"
	@echo "  rebuild      : rebuild all python packages"
	@echo "  publish      : publish built python packages to pypi.org (BE CAREFUL!)"
	@echo "  community    : Notify community FLAGS="--version 99.99.88 --notes 'I should have done more!' --post-notes 'Oh.. Maybe not'""
	@echo "Using tag: ${TAG}"

set-version:
	# --version --build --spec --post
	cd tools && ls
	cd tools && python update-version.py ${FLAGS}

community:
	#  make community FLAGS="--version 99.99.88 --notes 'I should have done more!' --post-notes 'Oh.. Maybe not'"
	cd tools && python update-discord.py ${FLAGS}

uninstall:
	pip uninstall -y vantage6
	pip uninstall -y vantage6-client
	pip uninstall -y vantage6-common
	pip uninstall -y vantage6-node
	pip uninstall -y vantage6-server

install:
	cd vantage6-common && pip install .
	cd vantage6-client && pip install .
	cd vantage6 && pip install .
	cd vantage6-node && pip install .
	cd vantage6-server && pip install .

install-dev:
	cd vantage6-common && pip install -e .
	cd vantage6-client && pip install -e .
	cd vantage6 && pip install -e .
	cd vantage6-node && pip install -e .
	cd vantage6-server && pip install -e .

image:
	docker build -t harbor2.vantage6.ai/infrastructure/node:${TAG} .
	docker tag harbor2.vantage6.ai/infrastructure/node:${TAG} harbor2.vantage6.ai/infrastructure/server:${TAG}

docker-push:
	docker push harbor2.vantage6.ai/infrastructure/node:${TAG}
	docker push harbor2.vantage6.ai/infrastructure/server:${TAG}

rebuild:
	@echo "------------------------------------"
	@echo "         BUILDING PROJECT           "
	@echo "------------------------------------"
	@echo "------------------------------------"
	@echo "         VANTAGE6 COMMON            "
	@echo "------------------------------------"
	cd vantage6-common && make rebuild
	@echo "------------------------------------"
	@echo "         VANTAGE6 CLIENT            "
	@echo "------------------------------------"
	cd vantage6-client && make rebuild
	@echo "------------------------------------"
	@echo "         VANTAGE6 CLI            "
	@echo "------------------------------------"
	cd vantage6 && make rebuild
	@echo "------------------------------------"
	@echo "         VANTAGE6 NODE            "
	@echo "------------------------------------"
	cd vantage6-node && make rebuild
	@echo "------------------------------------"
	@echo "         VANTAGE6 SERVER            "
	@echo "------------------------------------"
	cd vantage6-server && make rebuild

publish:
	cd vantage6-common && make publish
	cd vantage6-client && make publish
	cd vantage6 && make publish
	cd vantage6-node && make publish
	cd vantage6-server && make publish

test:
	coverage run --source=vantage6 --omit="utest.py","*.html","*.htm","*.txt","*.yml","*.yaml" utest.py
