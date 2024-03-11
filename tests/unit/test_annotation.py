import re

import pytest
from frozendict import frozendict

from docdeid import Document
from docdeid.annotation import Annotation, AnnotationSet
from docdeid.tokenizer import Token, WordBoundaryTokenizer, Tokenizer


class TestAnnotation:
    def test_create_annotation(self):
        annotation = Annotation(text="cat", start_char=0, end_char=3, tag="animal")

        assert annotation.text == "cat"
        assert annotation.start_char == 0
        assert annotation.end_char == 3
        assert annotation.tag == "animal"

    def test_create_annotation_with_token(self):
        t1 = Token(text="cat", start_char=0, end_char=3)
        t2 = Token(text="dog", start_char=8, end_char=11)

        annotation = Annotation(
            text="cat and dog",
            start_char=0,
            end_char=11,
            tag="animal",
            start_token=t1,
            end_token=t2,
        )

        assert annotation.start_token == t1
        assert annotation.end_token == t2

    def test_annotation_length(self):
        annotation = Annotation(text="cat", start_char=0, end_char=3, tag="animal")

        assert annotation.length == 3

    def test_annotation_equality(self):
        annotation1 = Annotation(text="cat", start_char=0, end_char=3, tag="animal")
        annotation2 = Annotation(text="cat", start_char=0, end_char=3, tag="animal")

        assert annotation1 == annotation2

    def test_annotation_nonequal(self):
        annotation1 = Annotation(text="cat", start_char=0, end_char=3, tag="animal")
        annotation2 = Annotation(
            text="cat", start_char=0, end_char=3, tag="living_being"
        )

        assert annotation1 != annotation2

    def test_create_annotation_incorrect_span(self):
        with pytest.raises(ValueError):
            _ = Annotation(text="cat", start_char=0, end_char=100, tag="animal")

    def test_create_annotation_with_prio(self):
        _ = Annotation(text="cat", start_char=0, end_char=3, tag="animal", priority=10)

    def test_get_sort_key(self):
        annotation = Annotation(text="cat", start_char=0, end_char=3, tag="animal")

        key = annotation.get_sort_key(by=("text", "tag"))

        assert key[0] == "cat"
        assert key[1] == "animal"

    def test_get_sort_key_reversed(self):
        annotation = Annotation(text="cat", start_char=0, end_char=3, tag="animal")

        key = annotation.get_sort_key(
            by=("end_char",), callbacks=frozendict(end_char=lambda x: -x)
        )

        assert key[0] == -3

    def test_get_sort_key_deterministic(self):
        annotation = Annotation(text="cat", start_char=0, end_char=3, tag="animal")

        key = annotation.get_sort_key(by=("start_char",), deterministic=True)

        assert len(key) > 1

    def test_get_sort_key_non_deterministic(self):
        annotation = Annotation(text="cat", start_char=0, end_char=3, tag="animal")

        key = annotation.get_sort_key(by=("start_char",), deterministic=False)

        assert len(key) == 1

    def test_get_sort_key_unknown_attr(self):
        annotation = Annotation(text="cat", start_char=0, end_char=3, tag="animal")

        key = annotation.get_sort_key(
            by=("this_attr_does_not_exist",), deterministic=False
        )

        assert len(key) > 0


class TestAnnotationSet:
    def test_add_annotation(self, annotations):
        annotation_set = AnnotationSet([annotations[0]])

        assert annotations[0] in annotation_set
        assert annotations[1] not in annotation_set
        assert annotations[2] not in annotation_set

    def test_add_annotations(self, annotations):
        annotation_set = AnnotationSet(annotations)

        assert annotations[0] in annotation_set
        assert annotations[1] in annotation_set
        assert annotations[2] in annotation_set

    def test_remove_annotations(self, annotations):
        annotation_set = AnnotationSet(annotations)

        annotation_set.remove(annotations[0])

        assert annotations[0] not in annotation_set
        assert annotations[1] in annotation_set
        assert annotations[2] in annotation_set

    def test_clear_annotations(self, annotations):
        annotation_set = AnnotationSet(annotations)

        annotation_set.clear()

        assert len(annotation_set) == 0
        assert annotations[0] not in annotation_set
        assert annotations[1] not in annotation_set
        assert annotations[2] not in annotation_set

    def test_get_annotations_sorted(self, annotations):
        annotation_set = AnnotationSet(annotations)

        sorted_annotations = annotation_set.sorted(
            by=("tag", "end_char"), callbacks=frozendict(end_char=lambda x: -x)
        )

        assert sorted_annotations == [annotations[2], annotations[1], annotations[0]]

    def test_get_annotations_sorted_priority(self, annotations):
        annotation_set = AnnotationSet(annotations)

        sorted_annotations = annotation_set.sorted(
            by=("priority", "length"), callbacks=frozendict(length=lambda x: -x)
        )

        assert sorted_annotations == [annotations[2], annotations[0], annotations[1]]

    def test_get_annotations_sorted_no_frozendict(self, annotations):

        annotation_set = AnnotationSet(annotations)

        with pytest.raises(RuntimeError):
            _ = annotation_set.sorted(
                by=("priority", "length"), callbacks=dict(length=lambda x: -x)
            )

    def test_annos_by_token(self, annotations):
        doc = Document("1 2 3 1 2 3 hum Hello hum I'm Bob - said Cindy",
                       tokenizers={"default": WordBoundaryTokenizer(False)})
        aset = AnnotationSet([
            a1 := Annotation("Hello", 16, 21, "word"),
            a2 := Annotation("I", 26, 27, "ltr"),
            a3 := Annotation("I'm", 26, 29, "words"),
            a4 := Annotation("Bob", 30, 33, "name"),
            a5 := Annotation("I'm Bob", 26, 33, "stmt"),
        ])

        # import pydevd_pycharm
        # pydevd_pycharm.settrace()

        got = aset.annos_by_token(doc)

        want = {
            Token("Hello", 16, 21): {a1},
            Token("I", 26, 27): {a2, a3, a5},
            Token("'", 27, 28): {a3, a5},
            Token("m", 28, 29): {a3, a5},
            Token("Bob", 30, 33): {a4, a5},
        }

        assert got == want

    def test_annos_by_token_2(self, annotations):
        class HumTokenizer(Tokenizer):
            """Extracts each "hum" word and the following word as a token."""
            def _split_text(self, text: str) -> list[Token]:
                return [
                    Token(match.group(0), match.start(), match.end())
                    for match in re.finditer("\\bhum\\s+\\w+", text)
                ]

        doc = Document("1 2 3 1 2 3 hum Hello hum I'm Bob - said Cindy",
                       tokenizers={"default": WordBoundaryTokenizer(False),
                                   "for_fun": HumTokenizer()})
        aset = AnnotationSet([
            a1 := Annotation("Hello", 16, 21, "word"),
            a2 := Annotation("I", 26, 27, "ltr"),
            a3 := Annotation("I'm", 26, 29, "words"),
            a4 := Annotation("Bob", 30, 33, "name"),
            a5 := Annotation("I'm Bob", 26, 33, "stmt"),
        ])

        got = aset.annos_by_token(doc)

        want = {
            Token("Hello", 16, 21): {a1},
            Token("I", 26, 27): {a2, a3, a5},
            Token("'", 27, 28): {a3, a5},
            Token("m", 28, 29): {a3, a5},
            Token("Bob", 30, 33): {a4, a5},
            Token("hum Hello", 12, 21): {a1},
            Token("hum I", 22, 27): {a2, a3, a5},
        }

        assert got == want
