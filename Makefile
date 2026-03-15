start:
	docker compose up

build:
	docker compose build

stop:
	docker compose stop

down:
	make stop
	docker compose down

test:
	docker compose run --rm fastapi pytest tests/ -v
