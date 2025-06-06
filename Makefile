#DOCKER_IMAGE:=incredible_bulk_api
#DOCKER_RUN:=docker run --rm -it --publish 8000:8000
# 	${DOCKER_RUN} ${DOCKER_IMAGE}
# 	docker build --tag ${DOCKER_IMAGE} --target test .
# 	${DOCKER_RUN} --volume ${PWD}:/app/ ${DOCKER_IMAGE} /bin/sh

DOCKER_DEV:=docker compose --file docker-compose.yaml --file docker-compose.test.yaml

.PHONY: help
.DEFAULT_GOAL:=help
help:	## display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-8s\033[0m %s\n", $$1, $$2 } END{print ""}' $(MAKEFILE_LIST)

run: imagePreviewAPI  ## run production container stack
	docker compose up --build
build: imagePreviewAPI ## build test containers (needed for `make shell`)
	${DOCKER_DEV} build
shell:  ## development shell (mounting '.' to workdir) (no `nginx`)
	${DOCKER_DEV} run --rm -it --service-ports incredible_bulk_api /bin/sh
	${DOCKER_DEV} down
stop:
	${DOCKER_DEV} down
run_local:  ## launch app (when in `shell`)
	python3 -m sanic --host 0.0.0.0 sanic_app.app:app --debug --noisy-exceptions --no-motd --single-process
	# --verbosity

imagePreviewAPI:
	git clone https://github.com/calaldees/imagePreviewAPI.git

.PHONY: cloc
cloc:  ## count lines of code stats
	cloc --vcs=git
