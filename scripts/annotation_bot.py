import argparse
import random
import json

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, Filters, CallbackContext, CallbackQueryHandler

from scipy.spatial.distance import cosine
from annoy import AnnoyIndex


class Client:
    def __init__(self, token, output_path, documents_path, users):
        self.output_path = output_path
        self.users = users

        self.updater = Updater(token=token, use_context=True)
        dispatcher = self.updater.dispatcher
        start_handler = CommandHandler("start", self.start, filters=Filters.command)
        dispatcher.add_handler(start_handler)
        stop_handler = CommandHandler("stop", self.stop, filters=Filters.command)
        dispatcher.add_handler(stop_handler)

        dispatcher.add_handler(CallbackQueryHandler(self.button))

        self.last_doc1 = None
        self.last_doc2 = None
        with open(documents_path, "r") as r:
            self.docs = [json.loads(line) for line in r]

        embedding_dim = len(self.docs[0]["embedding"])
        self.ann_index = AnnoyIndex(embedding_dim, "angular")
        for i, doc in enumerate(self.docs):
            self.ann_index.add_item(i, doc["embedding"])
        self.ann_index.build(100)

    def write_result(self, result):
        self.output_file.write(json.dumps({
            "url1": self.last_doc1["url"],
            "url2": self.last_doc2["url"],
            "result": result
        }, ensure_ascii=False) + "\n")
        self.output_file.flush()

    def run(self):
        self.updater.start_polling()
        self.updater.idle()

    def start(self, update: Update, context: CallbackContext):
        self.output_file = open(self.output_path, "a+")
        username = update.message.chat.username
        if username in self.users:
            self.show(update, context)

    def stop(self, update: Update, context: CallbackContext):
        self.output_file.close()

    def button(self, update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        query.answer()
        data = query.data
        self.write_result(data)
        self.show(update, context)

    def show(self, update: Update, context: CallbackContext):
        chat_id = update.effective_chat.id
        self.last_doc1, self.last_doc2, distance = self.sample_pair()
        distance = int(distance * 100.0)
        text1, text2 = self.last_doc1["text"], self.last_doc2["text"]

        keyboard = [
            [
                InlineKeyboardButton("Yes", callback_data="ok"),
                InlineKeyboardButton("No", callback_data="bad")
            ],
            [
                InlineKeyboardButton("Trash", callback_data="trash")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(
            text=f"{text1}\n\n{text2}\n\n{distance}",
            reply_markup=reply_markup,
            parse_mode="Markdown",
            chat_id=chat_id
        )

    def sample_pair(self):
        first_doc_index = random.randint(0, len(self.docs))
        first_doc = self.docs[first_doc_index]
        neighbors, distances = self.ann_index.get_nns_by_item(first_doc_index, 300, include_distances=True)
        # distance = 2 * (1-cos)
        indices = [i for i, distance in zip(neighbors, distances) if 0.85 <= distance <= 1.02]
        if not indices:
            return self.sample_pair()
        indices = [i for i in indices if abs(self.docs[i]["pub_time"] - first_doc["pub_time"]) < 3600 * 9]
        if not indices:
            return self.sample_pair()
        second_doc_index = random.choice(indices)
        second_doc = self.docs[second_doc_index]
        return first_doc, second_doc, cosine(second_doc["embedding"], first_doc["embedding"])


def main(
    token,
    documents_path,
    output_path,
    username
):
    client = Client(token=token, output_path=output_path, documents_path=documents_path, users=[username])
    client.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", type=str, required=True)
    parser.add_argument("--output-path", type=str, default="data/clustering_markup.jsonl")
    parser.add_argument("--documents-path", type=str, default="data/docs.jsonl")
    parser.add_argument("--username", type=str, required=True)
    args = parser.parse_args()
    main(**vars(args))
