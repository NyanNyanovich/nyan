# НЯН

[![Tests Status](https://github.com/NyanNyanovich/nyan/actions/workflows/python.yml/badge.svg)](https://github.com/NyanNyanovich/nyan/actions/workflows/python.yml)
[![https://t.me/nyannews](https://img.shields.io/badge/Telegram-nyannews-blue.svg?logo=telegram)](https://t.me/nyannews)
[![License](https://img.shields.io/github/license/NyanNyanovich/nyan)](https://github.com/NyanNyanovich/nyan/blob/master/LICENSE)

<img width="1189" alt="изображение" src="https://user-images.githubusercontent.com/104140467/193427932-f5b3ecdd-835f-493f-9901-553c03bdff9b.png">

НЯН (Nyan) is a news aggregator that scrapes news from different Telegram channels, clusters similar posts, and forms a united feed. All sources are split into several groups, so anyone can understand whether they can trust them.

Channel itself: [NyanNews](https://t.me/nyannews)

Extensive description (in Russian): [Whitepaper](https://telegra.ph/NYAN-Whitepaper-04-03)

Detailed instruction (in Russian): [Как поднять свой НЯН](https://github.com/NyanNyanovich/nyan/wiki/%D0%9A%D0%B0%D0%BA-%D0%BF%D0%BE%D0%B4%D0%BD%D1%8F%D1%82%D1%8C-%D1%81%D0%B2%D0%BE%D0%B9-%D0%9D%D0%AF%D0%9D)


## Docker compose setup

1. Install Docker and Docker Compose.
> Docker instructions: https://docs.docker.com/engine/install \
> Docker Compose instructions: https://docs.docker.com/compose/install

2. Clone the repository.
```
git clone https://github.com/NyanNyanovich/nyan
```

3. Go to the repository directory.
```
cd nyan
```

4. Provide Telegram API credentials to
> [configs/client_config.json](https://github.com/NyanNyanovich/nyan/blob/main/configs/client_config.json)

6. Run everything.
> [!NOTE]
> `core` Dockerfile incorporates model preloading during build so you don't have to wait for models to load during runtime. \
> If you'd like to disable this you can comment out the `RUN until python3 -m nyan.preloader ...` instruction.
```
docker compose up -d
```

## Kubernetes setup

Assuming you already have a running kubernetes cluster.

1. Clone the repository.
```
git clone https://github.com/NyanNyanovich/nyan
```

2. Go to the kubernetes directory.
```
cd nyan/kubernetes
```

4. Provide Telegram API credentials to
> [../configs/client_config.json](https://github.com/NyanNyanovich/nyan/blob/main/configs/client_config.json)

3. Prepare configmaps and secret (entire [configs/client_config.json](https://github.com/NyanNyanovich/nyan/blob/main/configs/client_config.json) is stored as a secret).
```
bash generate-configs.sh
```

4. Apply kubernetes configuration.
> [!WARNING]
> Default setup assumes you have a ceph filesystem named `ceph-filesystem`. \
> If that is not the case modify [mongo/mongo-pvc.yaml](https://github.com/NyanNyanovich/nyan/blob/main/kubernetes/mongo/mongo-pvc.yaml) to suit your needs.
```
kubectl apply -f ns.yaml
kubectl apply -f mongo/
kubectl apply -f configs/
kubectl apply -f nyan/
```
---
> [!TIP]
> You can provide `OPENAI_API_KEY` environment variable in the `core` container to use LLM-related features for both deployment scenarios.
