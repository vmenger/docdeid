from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from frozendict import frozendict

from docdeid.tokenizer import Token

UNKNOWN_ATTR_DEFAULT: Any = 0

_OPTIONAL_FIELDS = {"start_token", "end_token", "_key_cache"}


@dataclass(frozen=True)
class Annotation:  # pylint: disable=R0902
    """An annotation contains information on a specific span of text that is tagged."""

    text: str
    """The exact text."""

    start_char: int
    """The start character."""

    end_char: int
    """The end character."""

    tag: str
    """The tag (e.g. name, location)."""

    priority: int = field(default=0, repr=True, compare=False)
    """An additional priority attribute, that can be used for resolving
    overlap/merges."""

    start_token: Optional[Token] = field(default=None, repr=False, compare=False)
    """
    Optionally, the first :class:`.Token` in the sequence of tokens corresponding to
    this annotation.

    Should only be used when the annotation starts on a token boundary.
    """

    end_token: Optional[Token] = field(default=None, repr=False, compare=False)
    """
    Optionally, the last :class:`.Token` in the sequence of tokens corresponding to this
    annotation.

    Should only be used when the annotation ends on a token boundary.
    """

    length: int = field(init=False, compare=False)
    """The number of characters of the annotation text."""

    _key_cache: dict = field(default_factory=dict, repr=False, compare=False)

    def __post_init__(self) -> None:
        if len(self.text) != (self.end_char - self.start_char):
            raise ValueError("The span does not match the length of the text.")

        object.__setattr__(self, "length", len(self.text))

    def __getstate__(self) -> dict:
        return {
            "text": self.text,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "tag": self.tag,
            "priority": self.priority,
            "length": self.length,
        }

    def get_sort_key(
        self,
        by: tuple,  # pylint: disable=C0103
        callbacks: Optional[frozendict[str, Callable]] = None,
        deterministic: bool = True,
    ) -> tuple:
        """
        The sort key of an :class:`.Annotation` is used to order annotations by one or
        more of its attributes.

        Args:
            by: A list of attributes, used for sorting.
            callbacks: A map of attributes to a callable function, to modify the value
                on which is sorted (for example ``lambda x: -x`` for reversing).
            deterministic: Include all attributes in the sort key, so that ties are
                not broken randomly but deterministically.

        Returns:
            A tuple of the attributes specified, that can be passed to the key
            argument of the sorted function of (e.g.) ``list``.
        """

        cache_key = hash((self, by, callbacks, deterministic))

        if cache_key in self._key_cache:
            return self._key_cache[cache_key]

        sort_key = []

        for attr in by:

            val = getattr(self, attr, UNKNOWN_ATTR_DEFAULT)

            if callbacks is not None and attr in callbacks:
                val = callbacks[attr](val)

            sort_key.append(val)

        if deterministic:

            extra_attrs = sorted(set(self.__dict__.keys()) - set(by) - _OPTIONAL_FIELDS)

            for attr in extra_attrs:
                sort_key.append(getattr(self, attr, UNKNOWN_ATTR_DEFAULT))

        ret = tuple(sort_key)

        self._key_cache[cache_key] = ret

        return ret


class AnnotationSet(set[Annotation]):
    """
    Stores any number of annotations in a set.

    It extends the builtin ``set``.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._annos_by_tokenizers_by_token = {}

    def sorted(
        self,
        by: tuple,  # pylint: disable=C0103
        callbacks: Optional[frozendict[str, Callable]] = None,
        deterministic: bool = True,
    ) -> list[Annotation]:
        """
        Get the annotations in sorted order.

        Args:
            by: A list of :class:`.Annotation` attributes, used for sorting.
            callbacks: A map of :class:`.Annotation` attributes to a callable
                function, to modify the value on which is sorted (for example
                ``lambda x: -x`` for reversing).
            deterministic: Include all attributes in the sort key, so that ties are
                not broken randomly but deterministically.

        Returns:
            A list with the annotations, sorted as specified.

        Raises:
            A RunTimeError, if the callbacks are not provided as a frozen dict.
        """

        # Not liked by Mypy, even though
        # https://docs.python.org/3/library/stdtypes.html#types-union
        # says the "X | Y" notation is equivalent to `typing.Union[X, Y]` and the
        # docstring of `typing.Optional` says it's equivalent to
        # `typing.Union[None, _]`:
        #     if not isinstance(callbacks, Optional[frozendict]):
        if not isinstance(callbacks, frozendict | None):
            raise RuntimeError(
                "Please provide the callbacks as a frozen dict, e.g. "
                "frozendict.frozendict(end_char=lambda x: -x)"
            )

        return sorted(
            self,
            key=lambda x: x.get_sort_key(
                by=by, callbacks=callbacks, deterministic=deterministic
            ),
        )

    def has_overlap(self) -> bool:
        """
        Check if the set of annotations has any overlapping annotations.

        Returns:
            ``True`` if overlapping annotations are found, ``False`` otherwise.
        """

        annotations = self.sorted(by=("start_char",))

        for annotation, next_annotation in zip(annotations, annotations[1:]):

            if annotation.end_char > next_annotation.start_char:
                return True

        return False

    def annos_by_token(self, doc: "Document") -> defaultdict[Token, set[Annotation]]:
        """
        Returns a mapping from document tokens to annotations.

        Args:
            doc: document whose tokens are to be linked
        """
        # We key the token->annotations cache only by the set of tokenizers where it
        # actually (obviously) depends also on the document. However, it's assumed
        # that an AnnotationSet is always bound only to one document.
        tokenizers = frozenset(doc.token_lists)
        if tokenizers not in self._annos_by_tokenizers_by_token:
            annos_by_token = defaultdict(set)
            for token_list in doc.token_lists.values():
                if not token_list:
                    continue
                cur_tok_idx = 0
                tok = token_list[cur_tok_idx]
                for anno in self.sorted(by=("start_char",)):
                    try:
                        # Iterate over tokens till we reach the annotation.
                        while tok.end_char < anno.start_char:
                            cur_tok_idx += 1
                            tok = token_list[cur_tok_idx]
                    except IndexError:
                        break
                    else:
                        # Iterate over tokens in the annotation till we reach the end
                        # of it or the end of the tokens.
                        anno_tok_idx = cur_tok_idx
                        anno_tok = tok
                        while anno_tok.start_char < anno.end_char:
                            annos_by_token[anno_tok].add(anno)
                            if anno_tok_idx == len(token_list) - 1:
                                break
                            anno_tok_idx += 1
                            anno_tok = token_list[anno_tok_idx]
            self._annos_by_tokenizers_by_token[tokenizers] = annos_by_token
        return self._annos_by_tokenizers_by_token[tokenizers]
