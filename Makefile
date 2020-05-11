# `make` is expected to be called from the directory that contains
# this Makefile

TAG ?= trolltunga
BUILDNR ?= 1

help:
	@echo "Available commands to 'make':"
	@echo "  set-buildnr  : set buildnr in all vantage6 packages"
	@echo "  uninstall    : uninstall all vantage6 packages"
	@echo "  install      : do a regular install of all vantage6 packages"
	@echo "  install-dev  : do an editable install of all vantage6 packages"
	@echo "  docker-image : build the node/server docker image"
	@echo "  docker-push  : push the node/server docker image"
	@echo "  rebuild      : rebuild all python packages"
	@echo "  publish-test : publish built python packages to test.pypi.org"
	@echo "  publish      : publish built python packages to pypi.org (BE CAREFUL!)"
	@echo "  clean        : clean all built packages"
	@echo ""
	@echo "Using tag: ${TAG}"

set-buildnr:
	find ./ -name __build__ -exec sh -c "echo ${BUILDNR} > {}" \;

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

docker-image:
	docker build -t vantage6-master .

docker-push:
	@echo "Processing node:${TAG}"
	docker tag vantage6-master harbor.distributedlearning.ai/infrastructure/node:${TAG}
	docker push harbor.distributedlearning.ai/infrastructure/node:${TAG}
	@echo "Processing node:latest"
	docker tag vantage6-master harbor.distributedlearning.ai/infrastructure/node:latest
	docker push harbor.distributedlearning.ai/infrastructure/node:latest
	@echo "Processing server:${TAG}"
	docker tag vantage6-master harbor.distributedlearning.ai/infrastructure/server:${TAG}
	docker push harbor.distributedlearning.ai/infrastructure/server:${TAG}
	@echo "Processing server:latest"
	docker tag vantage6-master harbor.distributedlearning.ai/infrastructure/server:latest
	docker push harbor.distributedlearning.ai/infrastructure/server:latest

rebuild:
	cd vantage6-common && make rebuild
	cd vantage6-client && make rebuild
	cd vantage6 && make rebuild
	cd vantage6-node && make rebuild
	cd vantage6-server && make rebuild

publish-test:
	cd vantage6-common && make publish-test
	cd vantage6-client && make publish-test
	cd vantage6 && make publish-test
	cd vantage6-node && make publish-test
	cd vantage6-server && make publish-test

publish:
	cd vantage6-common && make publish
	cd vantage6-client && make publish
	cd vantage6 && make publish
	cd vantage6-node && make publish
	cd vantage6-server && make publish

clean:
	cd vantage6-common && make clean
	cd vantage6-client && make clean
	cd vantage6 && make clean
	cd vantage6-node && make clean
	cd vantage6-server && make clean
