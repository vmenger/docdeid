from abc import ABC, abstractmethod
from collections import defaultdict

from docdeid.annotation import Annotation, AnnotationSet
from docdeid.document import Document
from docdeid.process.doc import DocProcessor


class Redactor(DocProcessor, ABC):
    """
    Takes care of redacting the text by modifying it, based on the input text and annotations.

    Instantiations should implement the logic in :meth:`.Redactor.redact`.
    """

    def process(self, doc: Document, **kwargs) -> None:
        """
        Process a document by redacting it, according to the logic in :meth:`.Redactor.redact`.
        Args:
            doc: The document to process.
            **kwargs: Any other arguments.
        """
        redacted_text = self.redact(doc.text, doc.annotations)
        doc.set_deidentified_text(redacted_text)

    @abstractmethod
    def redact(self, text: str, annotations: AnnotationSet) -> str:
        """
        Redact the text.

        Args:
            text: The input text.
            annotations: The annotations that are produced by previous document processors.

        Returns:
            The redacted text.
        """


class RedactAllText(Redactor):
    """
    Literally redacts all text. Might for example be used when an error is raised.

    Args:
        open_char: The open char to use for the REPLACED tag.
        close_char: The close char to use for the REPLACED tag.

    Returns:
        The text ``REDACTED`` with the open and close char, literally (e.g. ``[REDACTED]``).
    """

    def __init__(self, open_char: str = "[", close_char: str = "]") -> None:
        self.open_char = open_char
        self.close_char = close_char

    def redact(self, text: str, annotations: AnnotationSet) -> str:

        return f"{self.open_char}REDACTED{self.close_char}"


class SimpleRedactor(Redactor):
    """
    Basic redactor, that replaces each entity in text with its tag. If the same entity occurs multiple times (with the
    same tag), it is replaced with ``tag-n``. Requires the set of annotationst o be non-overlapping.

    Args:
        open_char: The open char to use for the replacment tag.
        close_char: The close char to use for the replacment tag.
        check_overlap: Whether to check whether annotations overlap. If set to ``False`` but annotations are
            overlapping, will not give correct results.

    Returns:
        The redacted text, with each entity recognized in the set of annotations replaced with the proper tag.
    """

    def __init__(self, open_char: str = "[", close_char: str = "]", check_overlap: bool = True) -> None:
        self.open_char = open_char
        self.close_char = close_char
        self.check_overlap = check_overlap

    @staticmethod
    def _group_annotations_by_tag(annotations: AnnotationSet) -> dict[str, list[Annotation]]:
        """
        Group annotations by tag.

        Args:
            annotations: A set of annotations.

        Returns:
            A dict mapping each tag in the :class:`.AnnotationSet` to the Annotations.
        """

        groups = defaultdict(list)

        for annotation in annotations:
            groups[annotation.tag].append(annotation)

        return groups

    @staticmethod
    def _replace_annotations_in_text(text: str, annotations: AnnotationSet, replacement: dict[Annotation, str]) -> str:
        """
        Replaces each annotation in the text with the string defined in ``replacement`` mapping.

        Args:
            text: The original input text.
            annotations: The original set of input annotations.
            replacement: A mapping from :class:`.Annotation` to its string replacment.

        Returns:
            The text, with each annotation replaced by its defined replacement.
        """

        sorted_annotations = annotations.sorted(by=["end_char"], callbacks={"end_char": lambda x: -x})

        for annotation in sorted_annotations:

            text = text[: annotation.start_char] + replacement[annotation] + text[annotation.end_char :]

        return text

    def redact(self, text: str, annotations: AnnotationSet) -> str:

        if self.check_overlap and annotations.has_overlap():
            raise ValueError(f"{self.__class__} received input with overlapping annotations.")

        annotation_text_to_counter: dict[str, int] = {}

        for tag, annotation_group in self._group_annotations_by_tag(annotations).items():

            annotation_text_to_counter_group: dict[str, int] = {}

            annotation_group = sorted(annotation_group, key=lambda a: a.get_sort_key(by=["end_char"]))

            for annotation in annotation_group:

                if annotation.text not in annotation_text_to_counter_group:
                    annotation_text_to_counter_group[annotation.text] = len(annotation_text_to_counter_group) + 1

            annotation_text_to_counter |= annotation_text_to_counter_group

        annotation_replacement = {}

        for annotation in annotations:

            annotation_replacement[annotation] = (
                f"{self.open_char}"
                f"{annotation.tag.upper()}"
                f"-"
                f"{annotation_text_to_counter[annotation.text]}"
                f"{self.close_char}"
            )

        return self._replace_annotations_in_text(text, annotations, annotation_replacement)
