from TurkishStemmer import TurkishStemmer
import string
import re

from recommender.preproccess.stopwords import tr


# text normalization? zemberek-python ?
stoplist = tr.stop_words
stemmer = TurkishStemmer()


# "I'm dealing with natural language processing." -> ["i", "m", "dealing", "with" ...]
def tokenize_sentence(sentence: str) -> list[str]:
    return re.sub("[" + string.punctuation + "]", "", sentence.lower()).split()


# ["i", "m", "dealing", "with" ...] -> ["i", "m", "deal", "with", ...]
def stem_sentence(sentence: list[str]) -> list[str]:
    return [stemmer.stem(word) for word in sentence]


# ["i", "m", "deal", "with", ...] -> ["deal", "natural", "language", "process"]
def remove_stopwords(sentence: list[str]) -> list[str]:
    return [word for word in sentence if word not in stoplist]


def process(sentence: str) -> str:
    sentence = sentence if sentence is not None else ""
    sentence = tokenize_sentence(sentence)
    sentence = remove_stopwords(sentence)
    sentence = stem_sentence(sentence)
    return " ".join(sentence)
