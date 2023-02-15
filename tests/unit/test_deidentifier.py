from unittest.mock import patch

from docdeid.deidentifier import DocDeid
from docdeid.process.doc import DocProcessor
from docdeid.tokenize import Tokenizer


class TestDocDeid:
    def test_create_docdeid(self):
        dd = DocDeid()
        doc = dd.deidentify(text="test")
        assert doc.text == "test"

    @patch("docdeid.process.doc.DocProcessor.__abstractmethods__", set())
    def test_add_processors(self):
        proc_1 = DocProcessor()
        proc_2 = DocProcessor()

        dd = DocDeid()
        dd.processors.add_processor("proc_1", proc_1)
        dd.processors.add_processor("proc_2", proc_2)

        with patch.object(proc_1, "process") as proc1_process, patch.object(proc_2, "process") as proc2_process:

            dd.deidentify(text="_")

            proc1_process.assert_called_once()
            proc2_process.assert_called_once()

    @patch("docdeid.tokenize.Tokenizer.__abstractmethods__", set())
    def test_add_tokenizers(self):
        tokenizer_1 = Tokenizer()
        tokenizer_2 = Tokenizer()

        dd = DocDeid()
        dd.tokenizers["tokenizer_1"] = tokenizer_1
        dd.tokenizers["tokenizer_2"] = tokenizer_2

        doc = dd.deidentify(text="_")

        assert doc._tokenizers["tokenizer_1"] is tokenizer_1
        assert doc._tokenizers["tokenizer_2"] is tokenizer_2

    def test_metadata(self):
        metadata = {"some_item": "some_value"}
        dd = DocDeid()

        doc = dd.deidentify(text="_", metadata=metadata)

        assert doc.metadata["some_item"] == "some_value"
