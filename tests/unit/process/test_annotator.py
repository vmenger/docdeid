import re
from collections import defaultdict
from unittest.mock import patch

import pytest

import docdeid.ds
from docdeid.annotation import Annotation
from docdeid.direction import Direction
from docdeid.document import Document
from docdeid.ds import DsCollection, LookupSet, LookupTrie
from docdeid.pattern import TokenPattern
from docdeid.process.annotator import (
    MultiTokenLookupAnnotator,
    RegexpAnnotator,
    SequenceAnnotator,
    SequencePattern,
    SingleTokenLookupAnnotator,
    TokenPatternAnnotator,
    as_token_pattern,
)
from docdeid.str.processor import LowercaseString
from docdeid.tokenizer import SpaceSplitTokenizer, WordBoundaryTokenizer


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


class TestSequenceAnnotator:
    @pytest.fixture
    def ds(self):
        ds = DsCollection()

        first_names = ["Andries", "pieter", "Aziz", "Bernard", "Won Jung"]
        surnames = ["Meijer", "Smit", "Bakker", "Heerma"]
        interfixes = ["v/d"]
        interfixed_surnames = ["Heck"]

        ds["first_names"] = LookupSet()
        ds["first_names"].add_items_from_iterable(items=first_names)

        ds["surnames"] = LookupSet()
        ds["surnames"].add_items_from_iterable(items=surnames)

        ds["interfixes"] = LookupSet()
        ds["interfixes"].add_items_from_iterable(items=interfixes)

        trie = LookupTrie()
        for phrase in interfixed_surnames:
            trie.add_item(phrase.split())
        ds["interfixed_surnames"] = trie

        return ds

    @pytest.fixture
    def pattern_doc(self):
        return Document(
            text="De man heet Andries Meijer-Heerma, voornaam Andries.",
            tokenizers={"default": WordBoundaryTokenizer(False)},
        )

    @pytest.fixture
    def interfixed_doc(self):
        return Document(
            text="De man heet v/d Heck.",
            tokenizers={"default": WordBoundaryTokenizer(False)},
        )

    @pytest.fixture
    def korean_doc(self):
        return Document(
            text="De mevrouw heet Won Jung Meijer-Heerma.",
            tokenizers={"default": WordBoundaryTokenizer(False)},
        )

    def test_validation(self, ds):
        with pytest.raises(ValueError) as exc_info:
            SequenceAnnotator(pattern=[], ds=ds, tag="_")
        assert "missing or empty" in str(exc_info)

        # Lookup structures are not required if there are no lookup token patterns.
        SequenceAnnotator(pattern=[{"like_name": True}], tag="_")
        assert True

        with pytest.raises(ValueError) as exc_info:
            SequenceAnnotator(pattern=[{"lookup": "undefined_entity"}], tag="_")
        assert "no lookup structures were provided" in str(exc_info)

        with pytest.raises(ValueError) as exc_info:
            SequenceAnnotator(pattern=[{"lookup": "undefined_entity"}],
                              ds=ds,
                              tag="_")
        assert "Unknown lookup entity types: undefined_entity." in str(exc_info)

        with pytest.raises(ValueError) as exc_info:
            SequenceAnnotator(
                pattern=[{"or": [{"lookup": "undefined_entity"},
                                 {"lookup": "another_entity"}]}],
                ds=ds,
                tag="_")
        assert ("Unknown lookup entity types: another_entity, undefined_entity."
                in str(exc_info))

        # References to entities from metadata must not cause validation errors.
        SequenceAnnotator(pattern=[{"or": [{"lookup": "patient.name"},
                                           {"lookup": "doctor.surname"}]}],
                          tag="_")
        SequenceAnnotator(pattern=[{"or": [{"lookup": "interfixes"},
                                           {"lookup": "doctor.surname"}]}],
                          ds=ds,
                          tag="_")
        assert True

        with pytest.raises(ValueError) as exc_info:
            SequenceAnnotator(
                pattern=[{"or": [{"lookup": "interfixes"},
                                 {"and": [{"lookup": "first_names"},
                                          {"lookup": "alien_entity"}]}]},
                         {"lookup": "another_entity"}],
                ds=ds,
                tag="_")
        assert ("Unknown lookup entity types: alien_entity, another_entity."
                in str(exc_info))

        with pytest.raises(ValueError) as exc_info:
            SequenceAnnotator(
                pattern=[{"lookup": "interfixed_surnames"}],
                ds=ds,
                tag="_")
        assert ("is backed by a LookupTrie" in str(exc_info))

    def test_match_sequence(self, pattern_doc, ds):
        pattern = [{"lookup": "first_names"}, {"like_name": True}]

        tpa = SequenceAnnotator(pattern=pattern, ds=ds, tag="_")

        assert tpa._match_sequence(
            pattern_doc,
            tpa._seq_pattern,
            start_token=pattern_doc.get_tokens()[3],
            annos_by_token=defaultdict(list),
            dicts=ds,
        ) == Annotation(text="Andries Meijer", start_char=12, end_char=26, tag="_")
        assert (
            tpa._match_sequence(
                pattern_doc,
                tpa._seq_pattern,
                start_token=pattern_doc.get_tokens()[7],
                annos_by_token=defaultdict(list),
                dicts=ds,
            )
            is None
        )

    def test_match_sequence_left(self, pattern_doc, ds):
        """
        Matching is always performed in the direction left-to-right by
        SequenceAnnotator proper but the same method is also called by
        ContextAnnotator in Deduce, where matching may proceed also right-to-left.
        """
        pattern = [{"lookup": "first_names"}, {"like_name": True}]

        tpa = SequenceAnnotator(pattern=pattern, ds=ds, tag="_")

        assert tpa._match_sequence(
            pattern_doc,
            SequencePattern(
                Direction.LEFT, set(), [as_token_pattern(it) for it in pattern]
            ),
            start_token=pattern_doc.get_tokens()[4],
            annos_by_token=defaultdict(list),
            dicts=ds,
        ) == Annotation(text="Andries Meijer", start_char=12, end_char=26, tag="_")

        assert (
            tpa._match_sequence(
                pattern_doc,
                SequencePattern(
                    Direction.LEFT, set(), [as_token_pattern(it) for it in pattern]
                ),
                start_token=pattern_doc.get_tokens()[8],
                annos_by_token=defaultdict(list),
                dicts=ds,
            )
            is None
        )

    def test_match_sequence_skip(self, pattern_doc, ds):
        pattern = [{"lookup": "surnames"}, {"like_name": True}]

        tpa = SequenceAnnotator(pattern=pattern, ds=ds, tag="_")
        tpa_skipping = SequenceAnnotator(pattern=pattern, ds=ds, skip=["-"], tag="_")

        assert tpa_skipping._match_sequence(
            pattern_doc,
            tpa_skipping._seq_pattern,
            start_token=pattern_doc.get_tokens()[4],
            annos_by_token=defaultdict(list),
            dicts=ds,
        ) == Annotation(text="Meijer-Heerma", start_char=20, end_char=33, tag="_")
        assert (
            tpa._match_sequence(
                pattern_doc,
                SequencePattern(
                    Direction.RIGHT, set(), [as_token_pattern(it) for it in pattern]
                ),
                start_token=pattern_doc.get_tokens()[4],
                annos_by_token=defaultdict(list),
                dicts=ds,
            )
            is None
        )

    def test_annotate(self, pattern_doc, ds):
        pattern = [{"lookup": "first_names"}, {"like_name": True}]

        tpa = SequenceAnnotator(pattern=pattern, ds=ds, tag="_")

        assert tpa.annotate(pattern_doc) == [
            Annotation(text="Andries Meijer", start_char=12, end_char=26, tag="_")
        ]

    @pytest.mark.xfail(reason="The lookup token pattern only ever matches a single "
                              "token and the SequenceAnnotator docstring accordingly "
                              "rules the case of multiple tokens per pattern out of "
                              "scope. Yet, the packaged base_config.json seems to "
                              "rely on such multi-word matches, most notably in the "
                              "case of the interfix_with_name annotator.")
    def test_annotate_multiword(self, interfixed_doc, korean_doc, ds):
        inter_pattern = [{"lookup": "interfixes"}, {"lookup": "interfixed_surnames"}]
        ipa = SequenceAnnotator(pattern=inter_pattern, ds=ds,
                                # tokenizer=WordBoundaryTokenizer(False),
                                tag="_")
        assert ipa.annotate(interfixed_doc) == [
            Annotation(text="v/d Heck", start_char=12, end_char=20, tag="_")
        ]

        pattern = [{"lookup": "first_names"}, {"like_name": True}]
        kpa = SequenceAnnotator(pattern=pattern, ds=ds,
                                # tokenizer=WordBoundaryTokenizer(False),
                                tag="_")
        assert kpa.annotate(korean_doc) == [
            Annotation(text="Won Jung Meijer", start_char=16, end_char=31, tag="_")
        ]
