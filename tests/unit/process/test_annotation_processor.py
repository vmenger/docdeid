import numpy as np
import pytest
from frozendict import frozendict

from docdeid.annotation import Annotation, AnnotationSet
from docdeid.process.annotation_set import MergeAdjacentAnnotations, OverlapResolver


class TestOverlapResolver:
    def test_zero_runs(self):
        a = np.array([0, 0, 1, 2, 3, 0, 3, 2, 0])
        res = OverlapResolver._zero_runs(a)

        print("res", res)

        np.testing.assert_array_equal(res, np.array([[0, 2], [5, 6], [8, 9]]))

    def test_zero_runs_no_zeroes(self):
        a = np.array([1, 2, 3, 4, 3, 2, 5])
        res = OverlapResolver._zero_runs(a)

        print("res", res)

        np.testing.assert_array_equal(res, np.empty((0, 2)))

    def test_zero_runs_all_zero(self):
        a = np.array([0, 0, 0, 0, 0, 0])
        res = OverlapResolver._zero_runs(a)

        print("res", res)

        np.testing.assert_array_equal(res, np.array([[0, 6]]))

    def test_non_overlapping_annotations(self):
        text = "Hello I'm Bob"
        annotations = AnnotationSet(
            [
                Annotation(text="Hello", start_char=0, end_char=5, tag="word"),
                Annotation(text="I'm", start_char=6, end_char=9, tag="word"),
                Annotation(text="Bob", start_char=10, end_char=13, tag="name"),
            ]
        )
        proc = OverlapResolver(sort_by=("start_char",))

        processed_annotations = proc.process_annotations(annotations, text)

        assert processed_annotations == annotations

    def test_overlapping_annotations_left_right(self):
        text = "My name is Billy Bob Thornton"
        annotations = AnnotationSet(
            [
                Annotation(text="Billy Bob", start_char=11, end_char=20, tag="fist_name"),
                Annotation(text="Bob Thornton", start_char=17, end_char=29, tag="full_name"),
            ]
        )
        expected_annotations = AnnotationSet(
            [
                Annotation(text="Billy Bob", start_char=11, end_char=20, tag="fist_name"),
                Annotation(text=" Thornton", start_char=20, end_char=29, tag="full_name"),
            ]
        )
        proc = OverlapResolver(sort_by=("start_char",))  # left-right

        processed_annotations = proc.process_annotations(annotations, text)

        assert processed_annotations == expected_annotations

    def test_overlapping_annotations_right_left(self):
        text = "My name is Billy Bob Thornton"
        annotations = AnnotationSet(
            [
                Annotation(text="Billy Bob", start_char=11, end_char=20, tag="fist_name"),
                Annotation(text="Bob Thornton", start_char=17, end_char=29, tag="full_name"),
            ]
        )
        expected_annotations = AnnotationSet(
            [
                Annotation(text="Bob Thornton", start_char=17, end_char=29, tag="full_name"),
                Annotation(text="Billy ", start_char=11, end_char=17, tag="fist_name"),
            ]
        )
        proc = OverlapResolver(
            sort_by=("start_char",), sort_by_callbacks=frozendict(start_char=lambda x: -x)
        )  # right-left

        processed_annotations = proc.process_annotations(annotations, text)

        assert processed_annotations == expected_annotations


class TestMergeAdjacentAnnotations:
    def test_merge(self):
        text = "John Smith"
        annotations = AnnotationSet(
            [
                Annotation(text="John", start_char=0, end_char=4, tag="name"),
                Annotation(text="Smith", start_char=5, end_char=10, tag="name"),
            ]
        )
        expected_annotations = AnnotationSet([Annotation(text="John Smith", start_char=0, end_char=10, tag="name")])
        proc = MergeAdjacentAnnotations(slack_regexp=r"\s")

        processed_annotations = proc.process_annotations(annotations, text=text)

        assert processed_annotations == expected_annotations

    def test_not_adjacent(self):
        text = "John Smith"
        annotations = AnnotationSet(
            [
                Annotation(text="John", start_char=0, end_char=4, tag="name"),
                Annotation(text="Smith", start_char=5, end_char=10, tag="name"),
            ]
        )
        proc = MergeAdjacentAnnotations()

        processed_annotations = proc.process_annotations(annotations, text=text)

        assert processed_annotations == annotations

    def test_non_matching_tags(self):
        text = "John Smith"
        annotations = AnnotationSet(
            [
                Annotation(text="John", start_char=0, end_char=4, tag="first_name"),
                Annotation(text="Smith", start_char=5, end_char=10, tag="last_name"),
            ]
        )
        proc = MergeAdjacentAnnotations()

        processed_annotations = proc.process_annotations(annotations, text=text)

        assert processed_annotations == annotations

    def test_has_overlap(self):
        text = "My name is Billy Bob Thornton"
        annotations = AnnotationSet(
            [
                Annotation(text="Billy Bob", start_char=11, end_char=20, tag="fist_name"),
                Annotation(text="Bob Thornton", start_char=17, end_char=29, tag="full_name"),
            ]
        )

        proc = MergeAdjacentAnnotations(check_overlap=True)

        with pytest.raises(ValueError):
            _ = proc.process_annotations(annotations, text=text)

    def test_triple_merge(self):
        text = "My name is Billy Bob Thornton"
        annotations = AnnotationSet(
            [
                Annotation(text="Billy", start_char=11, end_char=16, tag="name"),
                Annotation(text="Bob", start_char=17, end_char=20, tag="name"),
                Annotation(text="Thornton", start_char=21, end_char=29, tag="name"),
            ]
        )
        expected_annotations = AnnotationSet(
            [Annotation(text="Billy Bob Thornton", start_char=11, end_char=29, tag="name")]
        )
        proc = MergeAdjacentAnnotations(slack_regexp=r"\s")

        processed_annotations = proc.process_annotations(annotations, text)

        assert processed_annotations == expected_annotations
