import re

EMOJI_PATTERN = re.compile(
    "(["
    "\U0001F1E0-\U0001F1FF"  # flags (iOS)
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F700-\U0001F77F"  # alchemical symbols
    "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
    "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
    "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
    "\U0001FA00-\U0001FA6F"  # Chess Symbols
    "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
    "\U00002600-\U00002B55"
    "\U0000FE0E-\U0000FE0F"
    "])", \
    flags=re.UNICODE
)
URL_PATTERN = re.compile(r"(http\S+|www\.\S+)", flags=re.UNICODE)
USERS_PATTERN = re.compile(r"@(\w+)", flags=re.UNICODE)
HASHTAG_PATTERN = re.compile(r"#(\w+)", flags=re.UNICODE)


def remove_emoji(text):
    return EMOJI_PATTERN.sub(r'', text)


def remove_hashtags(text):
    return HASHTAG_PATTERN.sub(r'', text)


def remove_urls(text):
    return URL_PATTERN.sub(r'', text)


def remove_users(text):
    return USERS_PATTERN.sub(r'', text)


def fix_paragraphs(text):
    paragraphs = text.split("\n")
    for i, paragraph in enumerate(paragraphs):
        paragraphs[i] = " ".join(paragraph.split()).strip()
    paragraphs = [p for p in paragraphs if len(p) >= 3]
    text = "\n".join(paragraphs)
    return text


def remove_bad_punct(text):
    paragraphs = text.split("\n")
    for i, paragraph in enumerate(paragraphs):
        paragraph = paragraph.replace(". .", ".").replace("..", ".")
        paragraph = paragraph.replace("« ", "«").replace(" »", "»")
        paragraph = paragraph.replace(" :", ":")
        paragraph = paragraph.replace("\xa0", " ")
        paragraphs[i] = paragraph
    text = "\n".join(paragraphs)
    return text


class TextProcessor:
    def __init__(self, config):
        self.pipeline = (
            remove_emoji,
            remove_hashtags,
            remove_users,
            remove_urls,
            remove_bad_punct,
            fix_paragraphs
        )
        self.skip_substrings = config["skip_substrings"]
        self.rm_substrings = config["rm_substrings"]

    def __call__(self, text):
        if self.is_bad_text(text):
            return None
        text = self.remove_bad_text(text)

        for step in self.pipeline:
            text = step(text)

        if self.is_bad_text(text):
            return None
        text = self.remove_bad_text(text)

        return text.strip()

    def is_bad_text(self, text):
        has_bad_ss = any(ss in text for ss in self.skip_substrings)
        return has_bad_ss

    def remove_bad_text(self, text):
        for ss in self.rm_substrings:
            if ss in text:
                text = text.replace(ss, " ")
        return text
