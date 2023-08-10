import argparse
import random
import json

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, Filters, CallbackContext, MessageHandler


class Client:
    def __init__(self, token, output_path, clusters_path, existing_markup_path, users):
        self.output_path = output_path
        self.users = users

        self.updater = Updater(token=token, use_context=True)
        dispatcher = self.updater.dispatcher
        start_handler = CommandHandler("start", self.start, filters=Filters.command)
        dispatcher.add_handler(start_handler)
        stop_handler = CommandHandler("stop", self.stop, filters=Filters.command)
        dispatcher.add_handler(stop_handler)

        dispatcher.add_handler(MessageHandler(callback=self.save, filters=~Filters.command))

        with open(clusters_path, "r") as r:
            self.clusters = [json.loads(line) for line in r][-500:]
        self.existing_clids = set()
        if existing_markup_path:
            with open(existing_markup_path, "r") as r:
                self.existing_clids = {json.loads(line)["clid"] for line in r}
                self.clusters = [cl for cl in self.clusters if cl["clid"] not in self.existing_clids]
        print("Bot is ready!")

    def write_result(self, result):
        self.output_file.write(json.dumps({
            "text": self.last_cluster["annotation_doc"]["patched_text"],
            "url": self.last_cluster["annotation_doc"]["url"],
            "clid": self.last_cluster["clid"],
            "result": result
        }, ensure_ascii=False) + "\n")
        self.existing_clids.add(self.last_cluster["clid"])
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

    def save(self, update: Update, context: CallbackContext) -> None:
        self.write_result(update.message.text)
        self.show(update, context)

    def show(self, update: Update, context: CallbackContext):
        chat_id = update.effective_chat.id
        while True:
            self.last_cluster = random.choice(self.clusters)
            if self.last_cluster["clid"] in self.existing_clids:
                continue
            text = self.last_cluster["annotation_doc"]["patched_text"]
            if not text:
                continue

            context.bot.send_message(
                text=f"{text}",
                parse_mode="Markdown",
                chat_id=chat_id
            )
            break


def main(
    token,
    clusters_path,
    existing_markup_path,
    output_path,
    username,
    seed
):
    random.seed(seed)
    client = Client(
        token=token,
        output_path=output_path,
        clusters_path=clusters_path,
        users=[username],
        existing_markup_path=existing_markup_path
    )
    client.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", type=str, required=True)
    parser.add_argument("--output-path", type=str, default="data/single_cluster_markup.jsonl")
    parser.add_argument("--existing-markup-path", type=str, default=None)
    parser.add_argument("--clusters-path", type=str, default="data/posted_clusters.jsonl")
    parser.add_argument("--username", type=str, required=True)
    parser.add_argument("--seed", type=int, default=32)
    args = parser.parse_args()
    main(**vars(args))
