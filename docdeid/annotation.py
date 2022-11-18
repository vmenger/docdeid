from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from docdeid.tokenize import Token

UNKNOWN_ATTR_DEFAULT: Any = 0


@dataclass(frozen=True)
class Annotation:
    """An annotation contains information on a specific span of text that is tagged."""

    text: str
    """ The exact text."""

    start_char: int
    """ The start character. """

    end_char: int
    """ The end character. """

    tag: str
    """ The tag (e.g. name, location). """

    start_token: Optional[Token] = field(default=None, repr=False, compare=False)
    """ Optionally, the first :class:`.Token` in the sequence of tokens corresponding to this annotation. Should only
    be used when the annotation starts on a token boundary. """

    end_token: Optional[Token] = field(default=None, repr=False, compare=False)
    """ Optionally, the last :class:`.Token` in the sequence of tokens corresponding to this annotation. Should only
    be used when the annotation ends on a token boundary. """

    length: int = field(init=False)
    """ The number of characters of the annotation text. """

    def __post_init__(self) -> None:

        if len(self.text) != (self.end_char - self.start_char):
            raise ValueError("The span does not match the length of the text.")

        object.__setattr__(self, "length", len(self.text))

    def get_sort_key(
        self,
        by: list[str],
        callbacks: Optional[dict[str, Callable]] = None,
        deterministic: bool = True,
    ) -> tuple:
        """
        The sort key of an :class:`.Annotation` is used to order annotations by one or more of its attributes.

        Args:
            by: A list of attributes, used for sorting.
            callbacks: A map of attributes to a callable function, to modify the value on which is sorted
                (for example ``lambda x: -x`` for reversing).
            deterministic: Include all attributes in the sort key, so that ties are not broken randomly but
                deterministically.

        Returns:
            A tuple of the attributes specified, that can be passed to the key argument of the sorted function
            of (e.g.) ``list``.
        """

        key = []

        for attr in by:

            val = getattr(self, attr, UNKNOWN_ATTR_DEFAULT)

            if callbacks is not None and (attr in callbacks):
                val = callbacks[attr](val)

            key.append(val)

        if deterministic:

            extra_attrs = sorted(set(self.__dict__.keys()) - set(by))

            for attr in extra_attrs:
                key.append(getattr(self, attr, UNKNOWN_ATTR_DEFAULT))

        return tuple(key)


class AnnotationSet(set[Annotation]):
    """
    Stores any number of annotations in a set.

    It extends the builtin ``set``.
    """

    def sorted(
        self,
        by: list[str],
        callbacks: Optional[dict[str, Callable]] = None,
        deterministic: bool = True,
    ) -> list[Annotation]:
        """
        Get the annotations in sorted order.

        Args:
            by: A list of :class:`.Annotation` attributes, used for sorting.
            callbacks: A map of :class:`.Annotation` attributes to a callable function, to modify the value on which
                is sorted (for example ``lambda x: -x`` for reversing).
            deterministic: Include all attributes in the sort key, so that ties are not broken randomly but
                deterministically.

        Returns:
            A list with the annotations, sorted as specified.
        """

        return sorted(
            list(self),
            key=lambda x: x.get_sort_key(by=by, callbacks=callbacks, deterministic=deterministic),
        )

    def has_overlap(self) -> bool:
        """
        Check if the set of annotations has any overlapping annotations.

        Returns:
            ``True`` if overlapping annotations are found, ``False`` otherwise.
        """

        annotations = self.sorted(by=["start_char"])

        for annotation, next_annotation in zip(annotations, annotations[1:]):

            if annotation.end_char > next_annotation.start_char:
                return True

        return False
