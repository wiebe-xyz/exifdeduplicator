SHELL := /bin/bash

build:
	@echo Use 'make start'

reset-test-data:
	rm -rf data/target/* data/source/*
	cp -r data/testdata/* data/source/

start:
	docker-compose -f docker-compose.yml up -d --build
	docker-compose -f docker-compose-deduplicator.yml up --build

stop-all: stop stop-rabbit

stop:
	docker-compose -f docker-compose-deduplicator.yml down

stop-rabbit:
	docker-compose -f docker-compose.yml down

filelist:
	docker-compose -f docker-compose-deduplicator.yml up --build filelist

exifscanner:
	docker-compose -f docker-compose-deduplicator.yml up -d --build exifscanner

filemover:
	docker-compose -f docker-compose-deduplicator.yml up -d --build filemover

duplicate-scanner:
	docker-compose -f docker-compose-deduplicator.yml up -d --build duplicate-scanner

duplicate-remover:
	docker-compose -f docker-compose-deduplicator.yml up -d --build duplicate-remover

deploy:
	git push && ssh wiebe@ssh.wiebe.xyz 'cd exifdeduplicator && git fetch && git reset --hard origin/master && make start-bot'

deploy-meukbak:
	git push && ssh wiebe@meukbak.local 'cd stockbot && git fetch && git reset --hard origin/master && make start-bot'

force-deploy:
	git commit -a --amend --no-edit && git push -f
	make deploy

init-server:
	ssh wiebe@ssh.wiebe.xyz 'git clone git@github.com:wiebe-xyz/exifdeduplicator.git'

update:
	ssh wiebe@ssh.wiebe.xyz 'cd exifdeduplicator; docker-compose pull; make start'

requirements: activate
	python -m pip install -r requirements.txt

activate:
		source ./venv/bin/activate;

install:
	source ./venv/bin/activate; python -m pip install -r requirements.txt

freeze:
	pip freeze > requirements.txt

clean:
	rm -rf venv || true
	python -m venv venv
