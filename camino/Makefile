#!make

.PHONY: deploy-all
deploy-all:
	docker-compose stop
	docker-compose up -d
	docker-compose restart nginx

.PHONY: down
down:
	docker-compose down $(service)