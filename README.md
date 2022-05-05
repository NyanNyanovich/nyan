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
