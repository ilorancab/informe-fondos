.PHONY: install test web up down logs image arm64 buildx push

IMAGE ?= ilbravo/informe-fondos
TAG ?= latest
PLATFORMS ?= linux/amd64,linux/arm64

TAGS = -t $(IMAGE):$(TAG)
ifneq ($(TAG),latest)
TAGS += -t $(IMAGE):latest
endif

install:
	uv sync

test:
	uv run pytest

web:
	uv run uvicorn informe_fondos.web.app:app --host 127.0.0.1 --port 8000 --reload

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

image:
	docker build -f docker/Dockerfile -t $(IMAGE):$(TAG) .

buildx:
	@docker buildx use multiarch 2>/dev/null || \
		docker buildx create --name multiarch --driver docker-container --use
	@docker buildx inspect --bootstrap >/dev/null

arm64:
	docker buildx build --platform linux/arm64 -t $(IMAGE):arm64 -f docker/Dockerfile --load .

push:
	docker buildx build --platform $(PLATFORMS) $(TAGS) -f docker/Dockerfile --push .
