import pytest

from docdeid.annotation import Annotation, AnnotationSet
from docdeid.deidentifier import DocDeid
from docdeid.process.annotator import (
    MultiTokenLookupAnnotator,
    SingleTokenLookupAnnotator,
)
from docdeid.process.redactor import SimpleRedactor
from docdeid.tokenize import SpaceSplitTokenizer


@pytest.fixture
def short_text():
    return "Hello my name is Bob"


@pytest.fixture
def long_text():
    return "Hello my name is Bob and I live in the United States of America"


class TestDeidentify:
    def test_single_annotator(self, short_text):

        deidentifier = DocDeid()
        deidentifier.tokenizers["default"] = SpaceSplitTokenizer()
        deidentifier.processors.add_processor(
            "name_annotator", SingleTokenLookupAnnotator(lookup_values=["Bob"], tag="name")
        )
        deidentifier.processors.add_processor("redactor", SimpleRedactor())

        doc = deidentifier.deidentify(text=short_text)

        expected_annotations = AnnotationSet([Annotation(text="Bob", start_char=17, end_char=20, tag="name")])

        expected_text = "Hello my name is [NAME-1]"

        assert doc.annotations == expected_annotations
        assert doc.deidentified_text == expected_text

    def test_multipe_annotators(self, long_text):

        deidentifier = DocDeid()
        tokenizer = SpaceSplitTokenizer()
        deidentifier.tokenizers["default"] = tokenizer
        deidentifier.processors.add_processor(
            "name_annotator", SingleTokenLookupAnnotator(lookup_values=["Bob"], tag="name")
        )
        deidentifier.processors.add_processor(
            "location_annotator",
            MultiTokenLookupAnnotator(
                lookup_values=["the United States of America"], tokenizer=tokenizer, tag="location"
            ),
        )
        deidentifier.processors.add_processor("redactor", SimpleRedactor())

        doc = deidentifier.deidentify(text=long_text)

        expected_annotations = AnnotationSet(
            [
                Annotation(text="Bob", start_char=17, end_char=20, tag="name"),
                Annotation(text="the United States of America", start_char=35, end_char=63, tag="location"),
            ]
        )

        expected_text = "Hello my name is [NAME-1] and I live in [LOCATION-1]"

        assert doc.annotations == expected_annotations
        assert doc.deidentified_text == expected_text

    def test_processors_enabled(self, long_text):

        deidentifier = DocDeid()
        tokenizer = SpaceSplitTokenizer()
        deidentifier.tokenizers["default"] = tokenizer
        deidentifier.processors.add_processor(
            "name_annotator", SingleTokenLookupAnnotator(lookup_values=["Bob"], tag="name")
        )
        deidentifier.processors.add_processor(
            "location_annotator",
            MultiTokenLookupAnnotator(
                lookup_values=["the United States of America"], tokenizer=tokenizer, tag="location"
            ),
        )
        deidentifier.processors.add_processor("redactor", SimpleRedactor())

        doc = deidentifier.deidentify(text=long_text, processors_enabled={"location_annotator", "redactor"})

        expected_annotations = AnnotationSet(
            [Annotation(text="the United States of America", start_char=35, end_char=63, tag="location")]
        )

        expected_text = "Hello my name is Bob and I live in [LOCATION-1]"

        assert doc.annotations == expected_annotations
        assert doc.deidentified_text == expected_text
