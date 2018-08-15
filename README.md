# Birch

Birch -- это легкая erp-система для российского бизнеса, котороая позволяет легко и быстро вести всю бухгалтерию, а так же управлять расходами небольшой фирмы, команды или компании.

Birch создан с целью избавить людей от нагрузки российского законодательства, обобщить данные, которые требуются для ведения бизнеса, а так же предоставить более удобное взаимодействие системой, чем это предлагают иные сервисы.

## Как установить

Обратите внимание, что запустить Birch можно только в операционных системах на базе Linux. Релиз Birch на иных системах не планируется.

Если вы ни разу не запускали сервисы xelaj на рабочей машине, для начала вам следует установить сервис Julia:
```bash
git clone https://github.com/xelaj/julia.git
cd julia/build/docker
sudo docker image 'xelaj-julia.tar.gz'
sudo docker run -p 80:80 xelaj-julia
```

Когда вы установили Julia, можно запускать Birch. Cкачайте готовый docker-image из репозитория, затем запустите контейнер с данным образом в docker:
```bash
git clone https://github.com/xelaj/birch.git
cd birch/build/docker
sudo docker image 'xelaj-birch.tar.gz'
sudo docker run -p 8888:8888 xelaj-birch
```

## Как использовать

* Методы api описаны [здесь](./doc/README.md).
* Настройка и конфигурация объясняется [вот тут](./doc/README.md)

## Как собрать образ

```bash
make build-docker
```
Образ создастся в папке build/docker

_Другие команды можно посмотреть в Makefile, каждая команда имеет комментарий, с описанием, что она делает_

## Как протестировать

```bash
make test
```

_Обратите внимание, что в данный момент покрытие тестами почти нулевое. Если у вас есть возможность, помогите написать тесты!_

## Как помочь развитию проекта

Перед тем, как начать что-либо делать проекту, обратитьесь к [Документации](./doc/README.md). В ней описана архитектура сервиса, библиотеки, общая структура кода, и прочие полезные штуки, которые полезно осознать.

Не бойтесь писать в issues, спрашивайте, сообщайте о багах, предлагайте решение проблем. Это помогает как разработчикам, так и сообществу в целом.

Текущие задачи записываются в [Projects](https://github.com/xelaj/birch/projects). Охотней всего принимаются пулл реквесты, связаные с тасками в проектах. _Но вообще реквесты принимаются любые._

-----------------

#### Для разработчиков:
Несмотря на то, что архитектура была кропотливо продумана, одобрена, и даже протестирована, в целях экономии времени, код писался наспех. Поэтому говорим честно — код говно. Но мы работаем над его исправлением, и работаем ежедневно. Поэтому не пугайтесь, лучше пишите сразу в issues, если хотите разгрести одну из наших какашек :)

-----------------

## Лицензия

Birch распстраняется по лицензиии [GNU AGPL v3](./LICENSE.md).