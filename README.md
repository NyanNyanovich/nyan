# НЯН

[![Tests Status](https://github.com/NyanNyanovich/nyan/actions/workflows/python.yml/badge.svg)](https://github.com/NyanNyanovich/nyan/actions/workflows/python.yml)
[![https://t.me/nyannews](https://img.shields.io/badge/Telegram-nyannews-blue.svg?logo=telegram)](https://t.me/nyannews)
[![License](https://img.shields.io/github/license/NyanNyanovich/nyan)](https://github.com/NyanNyanovich/nyan/blob/master/LICENSE)

<img width="1189" alt="изображение" src="https://user-images.githubusercontent.com/104140467/193427932-f5b3ecdd-835f-493f-9901-553c03bdff9b.png">

НЯН (Nyan) is a news aggregator that scrapes news from different Telegram channels, clusters similar posts, and forms a united feed. All sources are split into several groups, so anyone can understand whether they can trust them.

Channel itself: [NyanNews](https://t.me/nyannews)

Extensive description (in Russian): [Whitepaper](https://telegra.ph/NYAN-Whitepaper-04-03)

Detailed instruction (in Russian): [Как поднять свой НЯН](https://github.com/NyanNyanovich/nyan/wiki/%D0%9A%D0%B0%D0%BA-%D0%BF%D0%BE%D0%B4%D0%BD%D1%8F%D1%82%D1%8C-%D1%81%D0%B2%D0%BE%D0%B9-%D0%9D%D0%AF%D0%9D)

## Prerequisites

2 CPU cores, 8Gb RAM, 50Gb SSD
Ubuntu 18.04 or higher
Python 3.7 or higher
Docker: [installation doc](https://docs.docker.com/engine/install)
Docker Compose: [installation doc](https://docs.docker.com/compose/install)

Install the required packages

```shell
sudo apt-get install git git-lfs python3-pip wget
```

Clone repo

```shell
git clone https://github.com/NyanNyanovich/nyan
cd nyan
```

## Setup

1. Create Telegram channel and linked discussion group: all this done in Telegram
2. Create Telegram bot via BotFather: [installation doc](https://t.me/BotFather)
3. Bot needs to be admin in both channel and group
4. Provide Telegram API credentials to [configs/client_config.json](https://github.com/NyanNyanovich/nyan/blob/main/configs/client_config.json)

## Fill in information about the channel and bot

You need to edit the `configs/client_config.json` file. You can leave only `main` section for one channel. The number of sections and their names should be the same as in `configs/ranker_config.json`.

### channel_id

ID of the channel. For private channels can be obtained via any message link by right clicking on and selecting "Copy message link".
Example message link: https://t.me/c/1770334618/2. For this link, the channel ID is: `1770334618`.
For the Telegram format, you need to add the prefix `-100`.
The final `channel_id` for the example is: `-1001770334618`.


### discussion_id

ID of the group with comments.
It is built similarly to `channel_id`, only for the linked group.

### bot_token

Token, given when creating a bot. You just need to copy it.
Usually it is in the `number:string` format.

## Run option 1: Local Install

This option suits better for developers.

Install Python requirements. Create and activate `venv` before doing this.

```shell
python3 -m venv $(pwd)
source ./bin/activate
pip3 install -r requirements.txt
```

Download models

```shell
bash download_models.sh
```

### Run

Run Mongo container

```shell
docker-compose run mongodb
```

Run crawler

```shell
bash crawl.sh
```

Run server

```shell
bash send.sh
```

## Run option 2: Run all in docker-compose

This option is better to run as a service

```shell
docker-compose up
```
