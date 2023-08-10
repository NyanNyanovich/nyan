import argparse
import json
import numpy as np
import matplotlib.pyplot as plt
from seaborn import scatterplot
from gensim.models import Word2Vec


def main(
    channels_path,
    clusters_path,
    output_png
):
    with open(channels_path) as r:
        channels = json.load(r)
        channels = {channel["name"]: channel for channel in channels}

    with open(clusters_path) as r:
        clusters = [json.loads(line) for line in r]

    texts = []
    for cluster in clusters:
        cluster_channels = {doc["channel_id"].lower() for doc in cluster["docs"]}
        texts.append(list(cluster_channels))

    model = Word2Vec(
        sentences=texts,
        vector_size=2,
        window=15,
        min_count=1,
        workers=16,
        sg=0,
        epochs=60,
        hs=1,
        negative=0
    )

    vectors = model.wv
    keys = list(vectors.key_to_index.keys())
    print(keys)
    names = [channels[key]["alias"] for key in keys]
    colors = [channels[key]["group"] for key in keys]

    matrix = np.zeros((len(keys), 2), dtype=np.float)
    for i, key in enumerate(keys):
        for j, elem in enumerate(vectors[key]):
            matrix[i, j] = elem
    x = matrix[:, 0]
    y = matrix[:, 1]

    plt.figure(figsize=(8, 8), dpi=100)
    scatterplot(x, y, c=colors)
    plt.title("Agency2Vec на постах канала")
    for point_x, point_y, name in zip(x, y, names):
        plt.text(point_x + 0.015, point_y + 0.015, name)
    plt.savefig("agency2vec.png")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--channels-path', type=str, required=True)
    parser.add_argument('--clusters-path', type=str, required=True)
    parser.add_argument('--output-png', type=str, required=True)
    args = parser.parse_args()
    main(**vars(args))
