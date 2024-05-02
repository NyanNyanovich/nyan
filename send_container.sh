#!/bin/bash

mkdir -p data;

while :
do
    python3 -m nyan.send \
        --channels-info-path channels.json \
        --client-config-path configs/client_config.json \
        --mongo-config-path configs/mongo_container_config.json \
        --annotator-config-path configs/annotator_config.json \
        --renderer-config-path configs/renderer_config.json \
        --daemon-config-path configs/daemon_config.json;
done
