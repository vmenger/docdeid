import pytest

from docdeid.annotation import Annotation
from docdeid.pattern import TokenPattern
from docdeid.tokenizer import Token, TokenList


@pytest.fixture
def annotations():
    return [
        Annotation(text="Hello", start_char=0, end_char=5, tag="word", priority=10),
        Annotation(text="I'm", start_char=6, end_char=9, tag="word", priority=10),
        Annotation(text="Bob", start_char=10, end_char=13, tag="name", priority=5),
    ]


@pytest.fixture
def short_text():
    return "Hello I'm Bob"


@pytest.fixture
def short_tokens():
    return [
        Token(text="Hello", start_char=0, end_char=5),
        Token(text="I'm", start_char=6, end_char=9),
        Token(text="Bob", start_char=10, end_char=13),
    ]


@pytest.fixture
def short_tokenlist(short_tokens):
    return TokenList(short_tokens)


@pytest.fixture
def long_text():
    return "My name is dr. John Smith, please meet my wife jane Keith-Lucas"


@pytest.fixture
def long_tokens():
    return [
        Token(text="My", start_char=0, end_char=2),
        Token(text=" ", start_char=2, end_char=3),
        Token(text="name", start_char=3, end_char=7),
        Token(text=" ", start_char=7, end_char=8),
        Token(text="is", start_char=8, end_char=10),
        Token(text=" ", start_char=10, end_char=11),
        Token(text="dr", start_char=11, end_char=13),
        Token(text=". ", start_char=13, end_char=15),
        Token(text="John", start_char=15, end_char=19),
        Token(text=" ", start_char=19, end_char=20),
        Token(text="Smith", start_char=20, end_char=25),
        Token(text=", ", start_char=25, end_char=27),
        Token(text="please", start_char=27, end_char=33),
        Token(text=" ", start_char=33, end_char=34),
        Token(text="meet", start_char=34, end_char=38),
        Token(text=" ", start_char=38, end_char=39),
        Token(text="my", start_char=39, end_char=41),
        Token(text=" ", start_char=41, end_char=42),
        Token(text="wife", start_char=42, end_char=46),
        Token(text=" ", start_char=46, end_char=47),
        Token(text="jane", start_char=47, end_char=51),
        Token(text=" ", start_char=51, end_char=52),
        Token(text="Keith", start_char=52, end_char=57),
        Token(text="-", start_char=57, end_char=58),
        Token(text="Lucas", start_char=58, end_char=63),
    ]


@pytest.fixture
def long_tokenlist(long_tokens):
    return TokenList(long_tokens)


@pytest.fixture
def long_tokens_linked(long_tokens):
    for token, next_token in zip(long_tokens, long_tokens[1:]):
        token.set_next_token(next_token)
        next_token.set_previous_token(token)

    return long_tokens


class BasicPattern(TokenPattern):
    def match(self, token, metadata=None):
        if token.text[0].isupper():
            return token, token


class MultiPattern(TokenPattern):
    def token_precondition(self, token):
        return token.previous() is not None and token.next() is not None

    def match(self, token, metadata=None):
        if (
            token.text == "-"
            and token.previous().text[0].isupper()
            and token.next().text[0].isupper()
        ):
            return token.previous(), token.next()


@pytest.fixture
def basic_pattern():
    return BasicPattern(tag="capitalized")


@pytest.fixture
def multi_pattern():
    return MultiPattern(tag="compound_surname")
