# НЯН

НЯН — автоматический агрегатор разных новостных каналов в Телеграме. НЯН собирает сообщения с других новостных каналов в Телеграме, склеивает похожие сообщения в сюжеты и разбивает источники на 3 типа. Помогает быстро понимать, кто написал новость, и стоит ли ей доверять

Сам канал: [NyanNews](https://t.me/nyannews)

Подробное описание: [Whitepaper](https://telegra.ph/NYAN-Whitepaper-04-03)

## Install

Install git and pip
```
sudo apt-get install git python3-pip
```

Clone repo
```
git clone https://github.com/NyanNyanovich/nyan
```

Install Python requirements
```
pip3 install -r requirements.txt
```

Download models
```
bash download_models.sh
```

Install Docker and Docker Compose.
* Docker instructions: https://docs.docker.com/engine/install
* Docker Compose instructions: https://docs.docker.com/compose/install

Provide Telegram API credentials to [configs/client_config.json](https://github.com/NyanNyanovich/nyan/blob/main/configs/client_config.json).

## Run

Run Mongo container
```
docker-compose up
```

Run crawler
```
bash crawl.sh
```

Run server
```
bash send.sh
```
