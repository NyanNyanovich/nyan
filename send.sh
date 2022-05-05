mkdir -p data;
python3 -m nyan.send \
    --channels-info-path channels.json \
    --posted-clusters data/posted_clusters.jsonl \
    --client-config-path configs/client_config.json \
    --mongo-config-path configs/mongo_config.json \
    --annotator-config-path configs/annotator_config.json \
    --renderer-config-path configs/renderer_config.json;
