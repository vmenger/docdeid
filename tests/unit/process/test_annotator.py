import re
from unittest.mock import patch

import docdeid.ds
from docdeid.annotation import Annotation
from docdeid.document import Document
from docdeid.ds import LookupTrie
from docdeid.pattern import TokenPattern
from docdeid.process.annotator import (
    MultiTokenLookupAnnotator,
    RegexpAnnotator,
    SingleTokenLookupAnnotator,
    TokenPatternAnnotator,
)
from docdeid.str.processor import LowercaseString
from docdeid.tokenizer import SpaceSplitTokenizer


class TestSingleTokenLookupAnnotator:
    def test_single_token(self, long_text, long_tokenlist):
        doc = Document(long_text)
        annotator = SingleTokenLookupAnnotator(
            lookup_values=["John", "Jane", "Lucas"], tag="first_name"
        )
        expected_annotations = [
            Annotation(text="John", start_char=15, end_char=19, tag="first_name"),
            Annotation(text="Lucas", start_char=58, end_char=63, tag="first_name"),
        ]

        with patch.object(doc, "get_tokens", return_value=long_tokenlist):

            annotations = annotator.annotate(doc)

        assert set(annotations) == set(expected_annotations)

    def test_single_token_with_matching_pipeline(self, long_text, long_tokenlist):
        doc = Document(long_text)
        annotator = SingleTokenLookupAnnotator(
            lookup_values=["John", "Jane", "Lucas"],
            matching_pipeline=[LowercaseString()],
            tag="first_name",
        )
        expected_annotations = {
            Annotation(text="John", start_char=15, end_char=19, tag="first_name"),
            Annotation(text="jane", start_char=47, end_char=51, tag="first_name"),
            Annotation(text="Lucas", start_char=58, end_char=63, tag="first_name"),
        }

        with patch.object(doc, "get_tokens", return_value=long_tokenlist):

            annotations = set(annotator.annotate(doc))

        assert annotations == expected_annotations


class TestMultiTokenLookupAnnotator:
    def test_multi_token(self, long_text, long_tokenlist):
        doc = Document(long_text)
        my_trie = LookupTrie()
        my_trie.add_item(("my", " ", "name"))
        my_trie.add_item(("my", " ", "wife"))
        annotator = MultiTokenLookupAnnotator(trie=my_trie, tag="prefix")
        expected_annotations = [
            Annotation(text="my wife", start_char=39, end_char=46, tag="prefix"),
        ]

        with patch.object(doc, "get_tokens", return_value=long_tokenlist):

            annotations = annotator.annotate(doc)

        assert annotations == expected_annotations

    def test_multi_token_with_matching_pipeline(self, long_text, long_tokenlist):
        doc = Document(long_text)

        my_trie = LookupTrie(matching_pipeline=[LowercaseString()])
        my_trie.add_item(("my", " ", "name"))
        my_trie.add_item(("my", " ", "wife"))
        annotator = MultiTokenLookupAnnotator(trie=my_trie, tag="prefix")
        expected_annotations = [
            Annotation(text="My name", start_char=0, end_char=7, tag="prefix"),
            Annotation(text="my wife", start_char=39, end_char=46, tag="prefix"),
        ]

        with patch.object(doc, "get_tokens", return_value=long_tokenlist):
            annotations = annotator.annotate(doc)

        assert annotations == expected_annotations

    def test_multi_token_lookup_with_overlap(self, long_text, long_tokenlist):

        doc = Document(long_text)

        dr_trie = LookupTrie()
        dr_trie.add_item(("dr", ". ", "John"))
        dr_trie.add_item(("John", " ", "Smith"))
        annotator = MultiTokenLookupAnnotator(
            trie=dr_trie,
            tag="prefix",
            overlapping=True,
        )

        expected_annotations = [
            Annotation(text="dr. John", start_char=11, end_char=19, tag="prefix"),
            Annotation(text="John Smith", start_char=15, end_char=25, tag="prefix"),
        ]

        with patch.object(doc, "get_tokens", return_value=long_tokenlist):
            annotations = annotator.annotate(doc)

        assert annotations == expected_annotations

    def test_multi_token_lookup_no_overlap(self, long_text, long_tokenlist):

        doc = Document(long_text)

        dr_trie = LookupTrie()
        dr_trie.add_item(("dr", ". ", "John"))
        dr_trie.add_item(("John", " ", "Smith"))
        annotator = MultiTokenLookupAnnotator(
            trie=dr_trie,
            tag="prefix",
            overlapping=False,
        )

        expected_annotations = [
            Annotation(text="dr. John", start_char=11, end_char=19, tag="prefix"),
        ]

        with patch.object(doc, "get_tokens", return_value=long_tokenlist):
            annotations = annotator.annotate(doc)

        assert annotations == expected_annotations

    def test_multi_token_lookup_with_trie(self, long_text, long_tokenlist):

        doc = Document(long_text)

        trie = docdeid.ds.LookupTrie(matching_pipeline=[LowercaseString()])
        trie.add_item(["my", " ", "name"])
        trie.add_item(["my", " ", "wife"])
        annotator = MultiTokenLookupAnnotator(
            trie=trie,
            tag="prefix",
        )

        expected_annotations = [
            Annotation(text="My name", start_char=0, end_char=7, tag="prefix"),
            Annotation(text="my wife", start_char=39, end_char=46, tag="prefix"),
        ]

        with patch.object(doc, "get_tokens", return_value=long_tokenlist):
            annotations = annotator.annotate(doc)

        assert annotations == expected_annotations

    def test_trie_modified(self, long_text):
        # The user of Deduce may want to amend the resources shipped with Deduce.
        # Loading those happens in the Deduce initializer, which also constructs
        # annotators according to the configuration.

        # Run the interesting portions of Deduce initialization.
        doc = Document(long_text, tokenizers={"default": SpaceSplitTokenizer()})
        trie = docdeid.ds.LookupTrie()
        # Yeah, the comma in "Smith," seems off... but then again, WordBoundaryTokenizer
        # considers whitespace to be tokens. There is no good choice.
        trie.add_item(("John", "Smith,"))
        annotator = MultiTokenLookupAnnotator(trie=trie, tag="name")

        # Let's add our own resources.
        trie.add_item(("jane", "Keith-Lucas"))
        # ...including phrases with a potential to confuse the algorithm.
        trie.add_item(("jane", "joplane"))
        trie.add_item(("dr.", "John", "Hopkin"))
        trie.add_item(("Smith,", "please"))

        # Expect also our phrases to be detected.
        want = [
            Annotation(text="John Smith,", start_char=15, end_char=26, tag="name"),
            Annotation(text="jane Keith-Lucas", start_char=47, end_char=63, tag="name"),
        ]
        got = annotator.annotate(doc)
        assert got == want


class TestRegexpAnnotator:
    def test_regexp_annotator(self, long_text):
        doc = Document(long_text)
        annotator = RegexpAnnotator(
            regexp_pattern=re.compile(r"[A-Z][a-z]+"), tag="capitalized"
        )
        expected_annotations = [
            Annotation(text="My", start_char=0, end_char=2, tag="capitalized"),
            Annotation(text="John", start_char=15, end_char=19, tag="capitalized"),
            Annotation(text="Smith", start_char=20, end_char=25, tag="capitalized"),
            Annotation(text="Keith", start_char=52, end_char=57, tag="capitalized"),
            Annotation(text="Lucas", start_char=58, end_char=63, tag="capitalized"),
        ]

        annotations = annotator.annotate(doc)

        assert annotations == expected_annotations

    def test_regexp_annotator_with_string(self, short_text):

        doc = Document(short_text)

        annotator = RegexpAnnotator(regexp_pattern=r"[A-Z][a-z]+", tag="capitalized")

        expected_annotations = [
            Annotation(text="Hello", start_char=0, end_char=5, tag="capitalized"),
            Annotation(text="Bob", start_char=10, end_char=13, tag="capitalized"),
        ]

        annotations = annotator.annotate(doc)

        assert annotations == expected_annotations

    def test_regexp_annotator_with_group(self, long_text):
        doc = Document(long_text)
        annotator = RegexpAnnotator(
            regexp_pattern=re.compile(r"([A-Z])[a-z]+"),
            capturing_group=1,
            tag="only_the_capital",
        )
        expected_annotations = [
            Annotation(text="M", start_char=0, end_char=1, tag="only_the_capital"),
            Annotation(text="J", start_char=15, end_char=16, tag="only_the_capital"),
            Annotation(text="S", start_char=20, end_char=21, tag="only_the_capital"),
            Annotation(text="K", start_char=52, end_char=53, tag="only_the_capital"),
            Annotation(text="L", start_char=58, end_char=59, tag="only_the_capital"),
        ]

        annotations = annotator.annotate(doc)

        assert annotations == expected_annotations

    def test_regexp_with_validate(self, long_text):

        doc = Document(long_text)
        annotator = RegexpAnnotator(
            regexp_pattern=re.compile(r"([A-Z])[a-z]+"),
            capturing_group=1,
            tag="only_the_capital",
        )

        with patch.object(annotator, "_validate_match", return_value=False):
            assert annotator.annotate(doc) == []


class TestTokenPatternAnnotator:
    @patch("docdeid.pattern.TokenPattern.__abstractmethods__", set())
    def test_doc_precondition(self):
        doc = Document("_")
        pattern = TokenPattern(tag="_")
        annotator = TokenPatternAnnotator(pattern)

        with patch.object(
            pattern, "doc_precondition", return_value=False
        ), patch.object(pattern, "match") as mock_match:
            annotator.annotate(doc)
            mock_match.assert_not_called()

    def test_basic_pattern(self, long_text, long_tokenlist, basic_pattern):
        annotator = TokenPatternAnnotator(pattern=basic_pattern)
        doc = Document(text=long_text)

        expected_annotations = [
            Annotation(text="My", start_char=0, end_char=2, tag="capitalized"),
            Annotation(text="John", start_char=15, end_char=19, tag="capitalized"),
            Annotation(text="Smith", start_char=20, end_char=25, tag="capitalized"),
            Annotation(text="Keith", start_char=52, end_char=57, tag="capitalized"),
            Annotation(text="Lucas", start_char=58, end_char=63, tag="capitalized"),
        ]

        with patch.object(doc, "get_tokens", return_value=long_tokenlist):
            annotations = annotator.annotate(doc)

        assert annotations == expected_annotations

    def test_multi_pattern(self, long_text, long_tokens_linked, multi_pattern):
        annotator = TokenPatternAnnotator(pattern=multi_pattern)
        doc = Document(text=long_text)

        expected_annotations = [
            Annotation(
                text="Keith-Lucas", start_char=52, end_char=63, tag="compound_surname"
            )
        ]

        with patch.object(doc, "get_tokens", return_value=long_tokens_linked):
            annotations = annotator.annotate(doc)

        assert annotations == expected_annotations
