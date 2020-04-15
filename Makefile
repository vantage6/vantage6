# `make` is expected to be called from the directory that contains
# this Makefile

TAG ?= trolltunga

docker-image:
	# Building docker image
	docker build \
	  -t infrastructure/node:${TAG} \
	  -t harbor.distributedlearning.ai/infrastructure/node:${TAG} \
	  ./

docker-push:
	# Pushing docker image
	docker push harbor.distributedlearning.ai/infrastructure/node:${TAG}

all: docker-image docker-push