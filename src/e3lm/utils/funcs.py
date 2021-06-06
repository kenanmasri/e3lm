import re


def strip_once(text, chars=" "):  # pragma: no cover
    text = re.sub(re.compile("^["+chars+"]"), "", text)
    text = re.sub(re.compile("["+chars+"]$"), "", text)
    return text
