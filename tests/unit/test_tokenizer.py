from unittest.mock import patch

import docdeid.str
from docdeid.tokenizer import (
    SpaceSplitTokenizer,
    Token,
    Tokenizer,
    TokenList,
    WordBoundaryTokenizer,
)


class TestToken:
    def test_create_token(self):
        t = Token(text="test", start_char=0, end_char=4)

        assert t.text == "test"
        assert t.start_char == 0
        assert t.end_char == 4

    def test_equality(self):
        data = {"text": "test", "start_char": 0, "end_char": 4}

        t1 = Token(**data)
        t2 = Token(**data)

        assert t1 == t2

    def test_len(self):
        t = Token(text="test", start_char=0, end_char=4)

        assert len(t) == len("test")

    def test_next_token(self, short_tokens):
        short_tokens[0].set_next_token(short_tokens[1])
        short_tokens[1].set_next_token(short_tokens[2])

        assert short_tokens[0].next() is short_tokens[1]
        assert short_tokens[0].next(2) is short_tokens[2]
        assert short_tokens[0].next(3) is None
        assert short_tokens[1].next() is short_tokens[2]
        assert short_tokens[1].next(2) is None
        assert short_tokens[2].next() is None

    def test_previous_token(self, short_tokens):
        short_tokens[2].set_previous_token(short_tokens[1])
        short_tokens[1].set_previous_token(short_tokens[0])

        assert short_tokens[0].previous() is None
        assert short_tokens[1].previous() is short_tokens[0]
        assert short_tokens[1].previous(2) is None
        assert short_tokens[2].previous() is short_tokens[1]
        assert short_tokens[2].previous(2) is short_tokens[0]
        assert short_tokens[2].previous(3) is None


class TestTokenList:
    def test_create_tokenlist(self, short_tokens):
        token_list = TokenList(short_tokens)

        assert len(token_list) == len(short_tokens)

    def test_iterate(self, short_tokens):
        token_list = TokenList(short_tokens)

        for token1, token2 in zip(short_tokens, token_list):
            assert token1 == token2

        for i, token in enumerate(short_tokens):
            assert token == token_list[i]

    def test_index(self, short_tokens):

        token_list = TokenList(short_tokens)

        for i, token in enumerate(short_tokens):
            assert token_list.token_index(token) == i

    def test_create_tokenlist_link(self, short_tokens):
        token_list = TokenList(short_tokens)

        assert token_list[1].previous() is token_list[0]
        assert token_list[2].previous() is token_list[1]
        assert token_list[0].next() is token_list[1]
        assert token_list[1].next() is token_list[2]

    def test_create_tokenlist_non_linked(self, short_tokens):
        token_list = TokenList(short_tokens, link_tokens=False)

        for token in token_list:
            assert token.previous() is None
            assert token.next() is None

    def test_tokenlist_equal(self, short_tokens):
        token_list_1 = TokenList(short_tokens)
        token_list_2 = TokenList(short_tokens)

        assert token_list_1 == token_list_2

    def test_get_words(self, short_tokens):

        token_list = TokenList(short_tokens)

        assert token_list.get_words() == {"Hello", "I'm", "Bob"}

    def test_get_words_with_matching_pipeline(self, short_tokens):

        token_list = TokenList(short_tokens)
        matching_pipeline = [docdeid.str.LowercaseString()]

        assert token_list.get_words(matching_pipeline) == {"hello", "i'm", "bob"}

    def test_token_lookup(self, long_tokens):

        token_list = TokenList(long_tokens)

        assert token_list.token_lookup(lookup_values=set()) == set()
        assert token_list.token_lookup(lookup_values={"John", "Lucas"}) == {
            long_tokens[8],
            long_tokens[24],
        }
        assert (
            token_list.token_lookup(lookup_values={"something", "something_else"})
            == set()
        )
        assert token_list.token_lookup(lookup_values={" "}) == {
            long_tokens[1],
            long_tokens[3],
            long_tokens[5],
            long_tokens[9],
            long_tokens[13],
            long_tokens[15],
            long_tokens[17],
            long_tokens[19],
            long_tokens[21],
        }

    def test_token_lookup_with_matching_pipeline(self, long_tokens):

        token_list = TokenList(long_tokens)
        matching_pipeline = [docdeid.str.LowercaseString()]

        assert (
            token_list.token_lookup(
                lookup_values=set(), matching_pipeline=matching_pipeline
            )
            == set()
        )
        assert token_list.token_lookup(
            lookup_values={"john", "lucas"}, matching_pipeline=matching_pipeline
        ) == {
            long_tokens[8],
            long_tokens[24],
        }
        assert (
            token_list.token_lookup(
                lookup_values={"John", "Lucas"}, matching_pipeline=matching_pipeline
            )
            == set()
        )


class TestBaseTokenizer:
    @patch("docdeid.tokenizer.Tokenizer.__abstractmethods__", set())
    def test_tokenize_link(self, short_text, short_tokens):
        tokenizer = Tokenizer(link_tokens=True)

        with patch.object(tokenizer, "_split_text", return_value=short_tokens):
            tokens = tokenizer.tokenize(short_text)

        assert tokens[1].previous() is tokens[0]
        assert tokens[2].previous() is tokens[1]
        assert tokens[0].next() is tokens[1]
        assert tokens[1].next() is tokens[2]

    @patch("docdeid.tokenizer.Tokenizer.__abstractmethods__", set())
    def test_tokenize_no_link(self, short_text, short_tokens):
        tokenizer = Tokenizer(link_tokens=False)

        with patch.object(tokenizer, "_split_text", return_value=short_tokens):
            tokens = tokenizer.tokenize(short_text)

        for token in tokens:
            assert token.previous() is None
            assert token.next() is None


class TestSpaceSplitTokenizer:
    def test_space_split_tokenizer(self):
        text = "these are words"
        tokenizer = SpaceSplitTokenizer()
        expected_tokens = [
            Token(text="these", start_char=0, end_char=5),
            Token(text="are", start_char=6, end_char=9),
            Token(text="words", start_char=10, end_char=15),
        ]

        tokens = tokenizer._split_text(text)

        assert tokens == expected_tokens


class TestWordBoundaryTokenizer:
    def test_word_boundary_tokenizer(self):
        text = "Jane Keith-Lucas"
        tokenizer = WordBoundaryTokenizer()
        expected_tokens = [
            Token(text="Jane", start_char=0, end_char=4),
            Token(text=" ", start_char=4, end_char=5),
            Token(text="Keith", start_char=5, end_char=10),
            Token(text="-", start_char=10, end_char=11),
            Token(text="Lucas", start_char=11, end_char=16),
        ]

        tokens = tokenizer._split_text(text)

        assert tokens == expected_tokens

    def test_trimming(self):
        text = "Jane Keith-Lucas"
        tokenizer = WordBoundaryTokenizer(keep_blanks=False)
        expected_tokens = [
            Token(text="Jane", start_char=0, end_char=4),
            Token(text="Keith", start_char=5, end_char=10),
            Token(text="-", start_char=10, end_char=11),
            Token(text="Lucas", start_char=11, end_char=16),
        ]

        tokens = tokenizer._split_text(text)

        assert tokens == expected_tokens
