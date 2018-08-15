.PHONY: run lynt clean

BIN = ./birch_bin

run:
# запустить сервер напрямую из репозитория
	python3 $(BIN) -d -c ./config.ini


test: lynt
# прогнать все тесты
	pytest

lynt:
# проверить на соответствие pep8 и синтаксических ошибок
	pylint $(BIN)
	vulture $(BIN)

clean:
# вычистить репозиторий от ненужного хлама
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -empty -delete
	rm -rf ./.temp
	rm -rf ./.pytest_cache

build: test clean
# подготовить проект к билду
	pipreqs --savepath ./dist/raw/requirements.txt ./birch

build-docker: build
# билд репозитория в образ docker
	cp -r ./birch ./dist/docker/
	cp ./birch_bin ./dist/docker/

	cp ./dist/raw/config.ini ./dist/docker/config.ini
	docker build -t xelaj/birch ./dist/docker
	doclker save -o ./build/birch-docker.tar xelaj/birch