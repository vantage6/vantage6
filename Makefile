# `make` is expected to be called from the directory that contains
# this Makefile

TAG ?= trolltunga
BUILDNR ?= 1
BRANCH ?= master

help:
	@echo "Available commands to 'make':"
	@echo "  set-buildnr  : set buildnr in all vantage6 packages"
	@echo "  set-version  : set version (e.g set-version FLAGS=\"--version 2.0.0 --build 0 --spec alpha\")"
	@echo "  uninstall    : uninstall all vantage6 packages"
	@echo "  install      : do a regular install of all vantage6 packages"
	@echo "  install-dev  : do an editable install of all vantage6 packages"
	@echo "  image 		  : build the node/server docker image"
	@echo "  docker-push  : push the node/server docker image"
	@echo "  rebuild      : rebuild all python packages"
	@echo "  publish-test : publish built python packages to test.pypi.org"
	@echo "  publish      : publish built python packages to pypi.org (BE CAREFUL!)"
	@echo "  clean        : clean all built packages"
	@echo "  git-checkout : git checkout a BRANCH"
	@echo "  git-push     : push the active branch to the registry (optional: FLAGS)"
	@echo "  git-push     : pull the active"
	@echo "  git-merge    : merge BRANCH into active branch"
	@echo "  git-tag      : tag the current commit as a release TAG"
	@echo "  git-commit   : Commit all repos and all changes using MSG"
	@echo "  git-branch   : Create a new BRANCH"
	@echo "  git-reset    : Resets current working tree DISCARDING all uncommited changes!"
	@echo "  community    : Notify community FLAGS="--version 99.99.88 --notes 'I should have done more!' --post-notes 'Oh.. Maybe not'""
	@echo "Using tag: ${TAG}"

git-checkout:
	@echo "------------------------------------"
	@echo "   Checking out branch ${BRANCH}    "
	@echo "------------------------------------"
	cd vantage6-common && git checkout ${BRANCH}
	cd vantage6-client && git checkout ${BRANCH}
	cd vantage6 && git checkout ${BRANCH}
	cd vantage6-node && git checkout ${BRANCH}
	cd vantage6-server && git checkout ${BRANCH}
	@echo "------------------------------------"

git-branch:
	@echo "------------------------------------"
	@echo "       Create branch ${BRANCH}      "
	@echo "------------------------------------"
	cd vantage6-common && git branch ${BRANCH}
	cd vantage6-client && git branch ${BRANCH}
	cd vantage6 && git branch ${BRANCH}
	cd vantage6-node && git branch ${BRANCH}
	cd vantage6-server && git branch ${BRANCH}
	@echo "------------------------------------"

git-commit:
	cd vantage6-common && git commit -a -m "${MSG}"
	cd vantage6-client && git commit -a -m "${MSG}"
	cd vantage6 && git commit -a -m "${MSG}"
	cd vantage6-node && git commit -a -m "${MSG}"
	cd vantage6-server && git commit -a -m "${MSG}"

git-push:
	cd vantage6-common && git push ${FLAGS}
	cd vantage6-client && git push ${FLAGS}
	cd vantage6 && git push ${FLAGS}
	cd vantage6-node && git push ${FLAGS}
	cd vantage6-server && git push ${FLAGS}

git-pull:
	cd vantage6-common && git pull
	cd vantage6-client && git pull
	cd vantage6 && git pull
	cd vantage6-node && git pull
	cd vantage6-server && git pull

git-merge:
	cd vantage6-common && git merge ${BRANCH}
	cd vantage6-client && git merge ${BRANCH}
	cd vantage6 && git merge ${BRANCH}
	cd vantage6-node && git merge ${BRANCH}
	cd vantage6-server && git merge ${BRANCH}

git-tag:
	cd vantage6-common && git tag -a "${TAG}" -m "Release ${TAG}" && git push origin ${TAG}
	cd vantage6-client && git tag -a "${TAG}" -m "Release ${TAG}" && git push origin ${TAG}
	cd vantage6 && git tag -a "${TAG}" -m "Release ${TAG}" && git push origin ${TAG}
	cd vantage6-node && git tag -a "${TAG}" -m "Release ${TAG}" && git push origin ${TAG}
	cd vantage6-server && git tag -a "${TAG}" -m "Release ${TAG}" && git push origin ${TAG}

git-reset:
	@echo "------------------------------------"
	@echo "             GIT RESET              "
	@echo "------------------------------------"
	cd vantage6-common && git reset --hard
	cd vantage6-client && git reset --hard
	cd vantage6 && git reset --hard
	cd vantage6-node && git reset --hard
	cd vantage6-server && git reset --hard

set-version:
	# --version --build --spec --post
	cd tools && ls
	cd tools && python update-version.py ${FLAGS}

community:
	#  make community FLAGS="--version 99.99.88 --notes 'I should have done more!' --post-notes 'Oh.. Maybe not'"
	cd tools && python update-discord.py ${FLAGS}

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

image:
	docker build -t harbor2.vantage6.ai/infrastructure/node:${TAG} .
	docker tag harbor2.vantage6.ai/infrastructure/node:${TAG} harbor2.vantage6.ai/infrastructure/server:${TAG}

docker-push:
	docker push harbor2.vantage6.ai/infrastructure/node:${TAG}
	docker push harbor2.vantage6.ai/infrastructure/server:${TAG}

update-harukas:
	docker tag harbor2.vantage6.ai/infrastructure/server:${TAG} harbor2.vantage6.ai/infrastructure/server:live
	docker trust sign harbor2.vantage6.ai/infrastructure/server:live
	docker push harbor2.vantage6.ai/infrastructure/server:live

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
	@echo "------------------------------------"
	@echo "       CLEANING BUILD FOLDERS       "
	@echo "------------------------------------"
	cd vantage6-common && make clean
	cd vantage6-client && make clean
	cd vantage6 && make clean
	cd vantage6-node && make clean
	cd vantage6-server && make clean
