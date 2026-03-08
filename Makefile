start:
	docker compose up

build:
	docker compose build

stop:
	docker compose stop

down:
	make stop
	docker compose down