build:
	@echo Use 'make start'

reset-test-data:
	rm -rf data/target/* data/source/*
	cp -r data/testdata/* data/source/

start:
	docker-compose -f docker-compose.yml up -d --build
	docker-compose -f docker-compose-deduplicator.yml up --build

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

requirements:
	python -m pip install -r requirements.txt

activate:
	. ./venv/bin/activate

install: activate
	python -m pip install -r requirements.txt

freeze:
	pip freeze > requirements.txt

clean:
	rm -rf venv || true
	python -m venv venv
