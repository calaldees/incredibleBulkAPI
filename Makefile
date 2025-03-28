DOCKER_IMAGE:=incredible_bulk_api
DOCKER_RUN:=docker run --rm -it --publish 8000:8000

.PHONY: help
.DEFAULT_GOAL:=help
help:	## display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-8s\033[0m %s\n", $$1, $$2 } END{print ""}' $(MAKEFILE_LIST)

run: build  ## run from container
	${DOCKER_RUN} ${DOCKER_IMAGE}
build:  ## build container (needed for shell)
	docker build --tag ${DOCKER_IMAGE} --target test .
shell:  ## dev shell (mounting '.' to workdir)
	${DOCKER_RUN} --volume ${PWD}:/app/ ${DOCKER_IMAGE} /bin/sh
run_local:  ## launch app (when in container)
	python3 -m sanic --host 0.0.0.0 sanic_app.app:app --debug --noisy-exceptions --no-motd
	# --verbosity
	# --single-process

