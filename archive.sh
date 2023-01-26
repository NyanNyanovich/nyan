python3 -m scripts.mongo_to_jsonl --output-path data/raw_new_docs.jsonl
python3 -m scripts.clean_docs --input-path data/raw_new_docs.jsonl --output-path data/new_docs.jsonl
python3 -m scripts.clean_docs --input-path data/raw_old_docs.jsonl --output-path data/old_docs.jsonl

cp data/old_docs.jsonl data/all_docs.jsonl
cat data/new_docs.jsonl >> data/all_docs.jsonl

python3 -m scripts.filter_documents data/all_docs.jsonl data/documents.jsonl

python3 -m scripts.clusters_to_jsonl --output-path data/new_clusters.jsonl
cp data/old_clusters.jsonl data/all_clusters.jsonl
cat data/new_clusters.jsonl >> data/all_clusters.jsonl
python3 -m scripts.filter_posted_clusers data/all_clusters.jsonl data/clusters.jsonl data/documents.jsonl

cp channels.json data/channels.json
rm data/nyan_archive.tar.gz
cd data && tar -czvf nyan_archive.tar.gz clusters.jsonl documents.jsonl channels.json
