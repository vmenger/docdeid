from unittest.mock import patch

import pytest

from docdeid.document import Document, MetaData
from docdeid.tokenize import Tokenizer, TokenList


class TestDocument:
    def test_create_document(self):

        text = "Hello I'm Bob"
        doc = Document(text=text)

        assert doc.text == text

    def test_deidentified_text_noset(self):

        text = "Hello I'm Bob"
        doc = Document(text=text)

        assert doc.deidentified_text is None

    def test_deidentified_text(self):

        text = "Hello I'm Bob"
        deidentified_text = "Hello I'm <NAME>"
        doc = Document(text=text)

        doc.set_deidentified_text(deidentified_text)

        assert doc.text == text
        assert doc.deidentified_text == deidentified_text

    def test_annotation(self, annotations):

        text = "Hello I'm Bob"
        doc = Document(text=text)

        doc.annotations.update(annotations)

        for annotation in annotations:
            assert annotation in doc.annotations

    @patch("docdeid.tokenize.Tokenizer.__abstractmethods__", set())
    def test_get_tokens(self, short_tokens):

        text = "Hello I'm Bob"
        tokenizer = Tokenizer()
        doc = Document(text=text, tokenizers={"default": tokenizer})

        with patch.object(tokenizer, "tokenize", return_value=short_tokens):
            assert doc.get_tokens() == short_tokens

    @patch("docdeid.tokenize.Tokenizer.__abstractmethods__", set())
    def test_get_tokens_multiple_tokenizers(self, short_tokens):

        text = "Hello I'm Bob"
        tokenizer1 = Tokenizer()
        tokenizer2 = Tokenizer()
        doc = Document(text=text, tokenizers={"tokenizer_1": tokenizer1, "tokenizer_2": tokenizer2})

        with patch.object(tokenizer1, "tokenize", return_value=short_tokens), patch.object(
            tokenizer2, "_split_text", return_value=[]
        ):

            assert doc.get_tokens(tokenizer_name="tokenizer_1") == short_tokens
            assert doc.get_tokens(tokenizer_name="tokenizer_2") == TokenList([])

    def test_metadata(self):

        text = "Hello I'm Bob"
        metadata = {"person_name": "Bob"}

        doc = Document(text=text, metadata=metadata)

        assert doc.metadata["person_name"] == "Bob"


class TestMetaData:
    def test_add_metadata_item(self):

        metadata = MetaData()

        metadata["person_name"] = "Bob"

        assert metadata["person_name"] == "Bob"

    def test_overwrite_metadata_item_error(self):

        metadata = MetaData()

        metadata["person_name"] = "Bob"

        with pytest.raises(RuntimeError):
            metadata["person_name"] = "Mary"

    def test_metadata_item_nonexistant(self):

        metadata = MetaData()

        metadata["person_name"] = "Bob"

        assert metadata["something_that_doesnt_exist"] is None
