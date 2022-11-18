import re
from abc import ABC, abstractmethod
from typing import Callable, Optional

import numpy as np
import numpy.typing as npt

from docdeid.annotation import Annotation, AnnotationSet
from docdeid.document import Document
from docdeid.process.doc import DocProcessor


class AnnotationProcessor(DocProcessor, ABC):
    """Processes an :class:`.AnnotationSet`."""

    def process(self, doc: Document, **kwargs) -> None:

        if len(doc.annotations) == 0:
            return

        doc.annotations = self.process_annotations(doc.annotations, doc.text)

    @abstractmethod
    def process_annotations(self, annotations: AnnotationSet, text: str) -> AnnotationSet:
        """
        Process an :class:`.AnnotationSet`.

        Args:
            annotations: The input :class:`.AnnotationSet`.
            text: The corresponding text.

        Returns:
            An :class:`.AnnotationSet` that is processed according to the class logic.
        """


class OverlapResolver(AnnotationProcessor):
    """
    Resolves overlap in an :class:`.AnnotationSet`, if any. Use the ``sort_by`` and ``sort_by_callbacks`` arguments to
    specify how overlap should be resolved. For instance: ``sort_by=['start_char']`` will solve overlap from left to
    right, while ``sort_by=['length']`` will sort from short to long.

    Args:
        sort_by: A list of :class:`.Annotation` attributes to use for sorting.
        sort_by_callbacks: A mapping from class attribute (by string) to callable, to influence sort order
            (e.g. reverse with ``lambda x: -x``).
    """

    def __init__(self, sort_by: list[str], sort_by_callbacks: Optional[dict[str, Callable]] = None) -> None:

        self._sort_by = sort_by
        self._sort_by_callbacks = sort_by_callbacks

    @staticmethod
    def _zero_runs(arr: npt.NDArray) -> npt.NDArray:
        """
        Finds al zero runs in a numpy array.
        Source: https://stackoverflow.com/questions/24885092/finding-the-consecutive-zeros-in-a-numpy-array

        Args:
            arr: The input array.

        Returns:
            A (num_zero_runs, 2)-dim array, containing the start and end indeces of the zero runs.

        Examples:
            _zero_runs(np.array([0,1,2,0,0,0,3]) = array([[0,1], [3,6]])
        """

        iszero: npt.NDArray = np.concatenate((np.array([0]), np.equal(arr, 0).view(np.int8), np.array([0])))
        absdiff = np.abs(np.diff(iszero))
        return np.where(absdiff == 1)[0].reshape(-1, 2)

    def process_annotations(self, annotations: AnnotationSet, text: str) -> AnnotationSet:

        processed_annotations = []

        mask = np.zeros(max(annotation.end_char for annotation in annotations))

        annotations_sorted = annotations.sorted(by=self._sort_by, callbacks=self._sort_by_callbacks, deterministic=True)

        for annotation in annotations_sorted:

            mask_annotation = mask[annotation.start_char : annotation.end_char]

            if all(val == 0 for val in mask_annotation):  # no overlap
                processed_annotations.append(annotation)

            else:  # overlap

                for start_char_run, end_char_run in self._zero_runs(mask_annotation):

                    processed_annotations.append(
                        Annotation(
                            text=annotation.text[start_char_run:end_char_run],
                            start_char=annotation.start_char + start_char_run,
                            end_char=annotation.start_char + end_char_run,
                            tag=annotation.tag,
                        )
                    )

            mask[annotation.start_char : annotation.end_char] = 1

        return AnnotationSet(processed_annotations)


class MergeAdjacentAnnotations(AnnotationProcessor):
    """
    Merge adjacent annotations, with possibility for some slack (e.g. whitespaces) in between. Assumes the annotations
    do not overlap. You can disable checking by setting ``check_overlap=False`` to gain some performance, if you are
    very sure that no overlap can be present.

    Args:
        slack_regexp: A regexp that is used to match the characters between two annotations.
        check_overlap: If set to ``False``, there is no check if annotations are non-overlapping. This will give some
            minor performance benefit if you are sure there can be no overlap.
    """

    def __init__(self, slack_regexp: Optional[str] = None, check_overlap: bool = True) -> None:
        self.slack_regexp = slack_regexp
        self.check_overlap = check_overlap

    def _tags_match(self, left_tag: str, right_tag: str) -> bool:
        """
        Define whether two tags match, when considering whether to merge two annotations. By default, string equality.

        Args:
            left_tag: The left tag.
            right_tag: The right tag.

        Returns:
            ``True`` if they match, ``False`` if not.
        """

        return left_tag == right_tag

    def _tag_replacement(self, left_tag: str, right_tag: str) -> str:
        """
        Determine what to replace the tag of two merged annotations with. By default, the left tag.

        Args:
            left_tag: The left tag.
            right_tag: The right tag.

        Returns:
            A replacement for the two tags that is used for the merged annotation.
        """

        return left_tag

    def _are_adjacent_annotations(self, left_annotation: Annotation, right_annotation: Annotation, text: str) -> bool:
        """
        Check whether two annotations are adjacent.

        Args:
            left_annotation: The left annotation.
            right_annotation: The right annotation.
            text: The text corresponding to the annotation set

        Returns:
            ``True`` if adjacent according to the logic, ``False`` otherwise.
        """

        if not self._tags_match(left_annotation.tag, right_annotation.tag):
            return False

        between_text = text[left_annotation.end_char : right_annotation.start_char]

        if self.slack_regexp is None:
            return between_text == ""

        return re.fullmatch(self.slack_regexp, between_text) is not None

    def _adjacent_annotations_replacement(
        self, left_annotation: Annotation, right_annotation: Annotation, text: str
    ) -> Annotation:
        """
        Get a replacement for two adjacent annotations.

        Args:
            left_annotation: The left annotation.
            right_annotation: A right annotation.
            text: The text corresponding to the annotation set.

        Returns:
            A new annotation, that encompasses both old annotations as determined by the internal logic.
        """

        return Annotation(
            text=text[left_annotation.start_char : right_annotation.end_char],
            start_char=left_annotation.start_char,
            end_char=right_annotation.end_char,
            tag=self._tag_replacement(left_annotation.tag, right_annotation.tag),
        )

    def process_annotations(self, annotations: AnnotationSet, text: str) -> AnnotationSet:

        if self.check_overlap and annotations.has_overlap():
            raise ValueError(f"{self.__class__} received input with overlapping annotations.")

        processed_annotations = AnnotationSet()

        annotations_sorted = annotations.sorted(by=["start_char"])

        for index in range(len(annotations_sorted) - 1):

            annotation, next_annotation = annotations_sorted[index], annotations_sorted[index + 1]

            if self._are_adjacent_annotations(annotation, next_annotation, text):
                annotations_sorted[index + 1] = self._adjacent_annotations_replacement(
                    annotation, next_annotation, text
                )
            else:
                processed_annotations.add(annotation)

        processed_annotations.add(annotations_sorted[-1])  # add last one

        return processed_annotations
