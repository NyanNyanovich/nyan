import argparse
from collections import defaultdict
import copy
import json
import random

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset
from transformers import AutoTokenizer, BertModel
from transformers import Trainer, TrainingArguments, EarlyStoppingCallback
from sklearn.metrics import roc_auc_score, precision_recall_curve, classification_report

from util import read_jsonl, read_table, set_random_seed


class CosineDistance(nn.Module):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.sim = nn.CosineSimilarity(*args, **kwargs)

    def forward(self, left, right):
        return -self.sim(left, right) + 1.0


DISTANCE_FUNCTIONS = {
    "l2": nn.PairwiseDistance(p=2),
    "cos": CosineDistance(dim=1)
}


class NewsDataset(Dataset):
    def __init__(self, records, max_tokens, tokenizer):
        self.tokenizer = tokenizer
        self.max_tokens = max_tokens
        self.records = list()
        for r in records:
            pivot, positive, negative = self.embed_record(r)
            self.records.append({
                "pivot_inputs": pivot["input_ids"],
                "positive_inputs": positive["input_ids"],
                "negative_inputs": negative["input_ids"],
                "pivot_mask": pivot["attention_mask"],
                "positive_mask": positive["attention_mask"],
                "negative_mask": negative["attention_mask"],
                "labels": r["label"]
            })

    def __len__(self):
        return len(self.records)

    def embed_record(self, record):
        pivot_text = record["pivot"]["title"] + " [SEP] " + record["pivot"]["text"]
        positive_text = record["positive"]["title"] + " [SEP] " + record["positive"]["text"]
        negative_text = record["negative"]["title"] + " [SEP] " + record["negative"]["text"]
        tokenize = (lambda x: self.tokenizer(
            text=x,
            add_special_tokens=True,
            max_length=self.max_tokens,
            padding="max_length",
            truncation="longest_first",
            return_tensors="pt"
        ))
        fix = (lambda x: {key: value.squeeze(0) for key, value in x.items()})
        pivot = fix(tokenize(pivot_text))
        positive = fix(tokenize(positive_text))
        negative = fix(tokenize(negative_text))
        return pivot, positive, negative

    def __getitem__(self, index):
        return self.records[index]


class Embedder(nn.Module):
    def __init__(
        self,
        model_path,
        freeze_bert,
        layer_num
    ):
        super().__init__()

        self.model = BertModel.from_pretrained(model_path)
        self.model.trainable = not freeze_bert
        self.bert_dim = self.model.config.hidden_size
        self.layer_num = layer_num

    def forward(self, input_ids, attention_mask):
        output = self.model(
            input_ids,
            attention_mask=attention_mask,
            return_dict=True,
            output_hidden_states=True
        )
        embeddings = output.pooler_output
        norm = embeddings.norm(p=2, dim=1, keepdim=True)
        embeddings = embeddings.div(norm)
        return embeddings


class ContrastiveLoss(nn.Module):
    def __init__(self, margin, distance_func):
        super().__init__()

        self.margin = margin
        self.distance_func = DISTANCE_FUNCTIONS[distance_func]

    def forward(self, pivot_embeddings, positive_embeddings, negative_embeddings, labels):
        positive_distances = self.distance_func(pivot_embeddings, positive_embeddings)
        negative_distances = self.distance_func(pivot_embeddings, negative_embeddings)

        p_dists = positive_distances.clone()
        p_dists[labels == 0] = -100.0
        p_dist = positive_distances[torch.argmax(p_dists)]
        p_dist = torch.pow(torch.clamp(p_dist, min=0.0, max=1.0), 2)

        n_dists = negative_distances.clone()
        n_dists[labels == 1] = 100.0
        n_dist = negative_distances[torch.argmin(n_dists)]
        n_dist = torch.pow(torch.clamp(self.margin - n_dist, min=0.0, max=2.0), 2)

        return p_dist + n_dist


class TripletLoss(nn.Module):
    def __init__(self, margin, distance_func):
        super().__init__()

        self.margin = margin
        self.distance_func = DISTANCE_FUNCTIONS[distance_func]
        self.loss = nn.TripletMarginWithDistanceLoss(margin=margin, distance_function=self.distance_func)

    def forward(self, pivot_embeddings, positive_embeddings, negative_embeddings, labels=None):
        return self.loss(pivot_embeddings, positive_embeddings, negative_embeddings)


class ClusteringModel(nn.Module):
    def __init__(
        self,
        model_path,
        loss_params,
        freeze_bert=False,
        layer_num=-1
    ):
        super().__init__()

        self.embedder = Embedder(
            model_path,
            freeze_bert=freeze_bert,
            layer_num=layer_num
        )
        self.loss_name = loss_params.pop("name")
        self.loss_params = loss_params

        if self.loss_name == "contrastive":
            self.loss = ContrastiveLoss(**self.loss_params)
        elif self.loss_name == "triplet":
            self.loss = TripletLoss(**self.loss_params)

    def forward(
        self,
        pivot_inputs,
        positive_inputs,
        negative_inputs,
        pivot_mask,
        positive_mask,
        negative_mask,
        labels
    ):
        labels = labels.long()
        pivot_embeddings = self.embedder(pivot_inputs, pivot_mask)
        positive_embeddings = self.embedder(positive_inputs, positive_mask)
        negative_embeddings = self.embedder(negative_inputs, negative_mask)
        loss = self.loss(pivot_embeddings, positive_embeddings, negative_embeddings, labels)
        return {
            "loss": loss,
            "pivot_embeddings": pivot_embeddings,
            "positive_embeddings": positive_embeddings,
            "negative_embeddings": negative_embeddings
        }


class CustomTrainer(Trainer):
    def compute_loss(self, model, inputs, return_outputs=False):
        outputs = model(**inputs)
        loss = outputs["loss"]
        return (loss, outputs) if return_outputs else loss


def transform(records):
    result_mapping = {
        "different": 0,
        "related": 0,
        "same": 1
    }

    positives = defaultdict(list)
    negatives = defaultdict(list)
    for r in records:
        r1 = {"title": r["title1"], "text": r["text1"], "url": r["url1"]}
        r2 = {"title": r["title2"], "text": r["text2"], "url": r["url2"]}
        label = result_mapping.get(r.get("result", r.get("target")))
        if label == 1:
            positives[r1["url"]].append(r2)
            positives[r2["url"]].append(r1)
        elif label == 0:
            negatives[r1["url"]].append(r2)
            negatives[r2["url"]].append(r1)
    negative_urls = list(negatives.keys())

    fixed_records = []
    for r in records:
        label = result_mapping.get(r.get("result", r.get("target")))
        pivot_record = {"title": r["title1"], "text": r["text1"], "url": r["url1"]}
        other_record = {"title": r["title2"], "text": r["text2"], "url": r["url2"]}
        if random.random() < 0.5:
            pivot_record, other_record = other_record, pivot_record
        pivot_url = pivot_record["url"]
        new_record = {
            "iter_ts": r["iter_ts"],
            "label": label,
            "pivot": pivot_record
        }
        if label == 1:
            new_record["positive"] = other_record
            record_negatives = negatives[pivot_url]
            if not record_negatives:
                record_negatives = [negatives[random.choice(negative_urls)][0]]
            for negative in record_negatives:
                new_record["negative"] = negative
                fixed_records.append(copy.copy(new_record))
        elif label == 0:
            new_record["negative"] = other_record
            record_positives = positives[pivot_url]
            if not record_positives:
                record_positives = [pivot_record]
            for positive in record_positives:
                new_record["positive"] = positive
                fixed_records.append(copy.copy(new_record))
    return fixed_records


def main(
    train_table,
    val_table,
    test_table,
    config_file,
    nrows,
    out_dir,
    logging
):
    with open(config_file) as f:
        config = json.load(f)

    min_agreement = config["min_agreement"]
    train_records = [r for r in read_table(train_table) if r.get("agreement", 1.0) >= min_agreement]
    val_records = [r for r in read_table(val_table) if r.get("agreement", 1.0) >= min_agreement]
    test_records = [r for r in read_table(test_table) if r.get("agreement", 1.0) >= min_agreement]

    if nrows:
        train_records = train_records[:nrows]
        val_records = val_records[:nrows // 8]
        test_records = test_records[:nrows // 8]

    set_random_seed(config["seed"])
    random.shuffle(train_records)

    print("Train records: ", len(train_records))
    print("Val records: ", len(val_records))
    print("Test records: ", len(test_records))
    print("First test iter_ts:", test_records[0]["iter_ts"])

    extended_train = transform(train_records)
    extended_val = transform(val_records)

    model_name = config["model_name"]
    max_tokens = config["max_tokens"]
    tokenizer = AutoTokenizer.from_pretrained(model_name, do_lower_case=False)
    train_dataset = NewsDataset(extended_train, max_tokens, tokenizer)
    val_dataset = NewsDataset(extended_val, max_tokens, tokenizer)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    loss_params = config.pop("loss")
    if logging == "wandb":
        import wandb
        wandb.init()
        wandb.config.update({"config." + k: v for k, v in config.items()})
        wandb.config.update({"config.loss." + k: v for k, v in loss_params.items()})

    model = ClusteringModel(model_name, loss_params)
    model = model.to(device)

    training_args = TrainingArguments(
        output_dir="checkpoints",
        evaluation_strategy="steps",
        save_strategy="steps",
        per_device_train_batch_size=config["batch_size"],
        per_device_eval_batch_size=config["batch_size"],
        logging_steps=config["eval_steps"],
        save_steps=config["eval_steps"],
        warmup_steps=config["warmup_steps"],
        learning_rate=config["lr"],
        num_train_epochs=config["epochs"],
        gradient_accumulation_steps=config["grad_accum_steps"],
        report_to=logging,
        load_best_model_at_end=True,
        save_total_limit=2
    )

    trainer = CustomTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset
    )

    trainer.train()

    embedder = model.embedder.cuda()
    embedder.model.save_pretrained(out_dir)
    tokenizer.save_pretrained(out_dir)

    y_true, y_pred = [], []
    distance_func = model.loss.distance_func
    with torch.no_grad():
        for r in test_records:
            text1 = r["title1"] + " [SEP] " + r["text1"]
            text2 = r["title2"] + " [SEP] " + r["text2"]
            tokenize = (lambda x: tokenizer(
                text=x,
                add_special_tokens=True,
                max_length=max_tokens,
                padding="max_length",
                truncation="longest_first",
                return_tensors="pt"
            ))
            fix = (lambda x: {key: value.squeeze(0) for key, value in x.items()})
            inputs1 = fix(tokenize(text1))
            inputs2 = fix(tokenize(text2))
            left_inputs = inputs1["input_ids"].unsqueeze(0).to(device)
            left_mask = inputs1["attention_mask"].unsqueeze(0).to(device)
            right_inputs = inputs2["input_ids"].unsqueeze(0).to(device)
            right_mask = inputs2["attention_mask"].unsqueeze(0).to(device)
            left_embeddings = embedder(left_inputs, left_mask)
            right_embeddings = embedder(right_inputs, right_mask)
            distance = distance_func(left_embeddings, right_embeddings)[0].item()
            y_pred.append(1.0 - distance)
            y_true.append(int(r["result"] == "same"))

    auc = roc_auc_score(y_true, y_pred)
    print("AUC:", auc)

    precision, recall, thresholds = precision_recall_curve(y_true, y_pred)
    f1_scores = 2 * recall * precision / (recall + precision)
    best_threshold = thresholds[np.argmax(f1_scores)]
    f1 = max(f1_scores)
    print('Best threshold: ', best_threshold)
    print("F1: ", f1)

    if logging == "wandb":
        wandb.log({
            "auc": auc,
            "best_threshold": best_threshold,
            "f1": f1
        })
        y_proba = np.array([np.array((1.0 - p, p)) for p in y_pred])
        wandb.sklearn.plot_roc(y_true, y_proba)
        wandb.sklearn.plot_precision_recall(y_true, y_proba)

    y_pred = np.array(y_pred)
    y_true = np.array(y_true, dtype=np.int32)
    print(classification_report(y_true, y_pred >= best_threshold))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-table", type=str, required=True)
    parser.add_argument("--val-table", type=str, required=True)
    parser.add_argument("--test-table", type=str, required=True)
    parser.add_argument("--config-file", type=str, required=True)
    parser.add_argument("--out-dir", type=str, required=True)
    parser.add_argument("--nrows", type=int, default=None)
    parser.add_argument("--logging", type=str, default="none")
    args = parser.parse_args()
    main(**vars(args))
