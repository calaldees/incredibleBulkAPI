DOCKER_IMAGE:=sanic_bulk
DOCKER_RUN:=docker run --rm -it --publish 8000:8000

run: build
	${DOCKER_RUN} ${DOCKER_IMAGE}
build:
	docker build --tag ${DOCKER_IMAGE} .
shell:
	${DOCKER_RUN} --volume ${PWD}:/app/ ${DOCKER_IMAGE} /bin/sh
