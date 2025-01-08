from __future__ import annotations

import re
import warnings
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Literal, Optional, Union

import docdeid.str
from docdeid.annotation import Annotation
from docdeid.direction import Direction
from docdeid.document import Document
from docdeid.ds import DsCollection
from docdeid.ds.lookup import LookupSet, LookupTrie
from docdeid.pattern import TokenPattern
from docdeid.process.doc_processor import DocProcessor
from docdeid.str.processor import StringModifier
from docdeid.tokenizer import Token


@dataclass
class SimpleTokenPattern:
    """A pattern for a token (and possibly its annotation, too)."""

    func: Literal[
        "equal",
        "re_match",
        "is_initial",
        "is_initials",
        "like_name",
        "lookup",
        "neg_lookup",
        "tag",
    ]
    pattern: str


@dataclass
class NestedTokenPattern:
    """Coordination of token patterns."""

    func: Literal["and", "or"]
    pattern: list[TokenPatternFromCfg]


TokenPatternFromCfg = Union[SimpleTokenPattern, NestedTokenPattern]


@dataclass
class SequencePattern:
    """Pattern for matching a sequence of tokens."""

    direction: Direction
    skip: set[str]
    pattern: list[TokenPatternFromCfg]


class Annotator(DocProcessor, ABC):
    """
    Abstract class for annotators, which are responsible for generating annotations from
    a given document. Instantiations should implement the annotate method.

    Args:
        tag: The tag to use in the annotations.
    """

    def __init__(self, tag: str, priority: int = 0) -> None:
        self.tag = tag
        self.priority = priority

    def process(self, doc: Document, **kwargs) -> None:
        """
        Process a document, by adding annotations to its :class:`.AnnotationSet`.

        Args:
            doc: The document to be processed.
        """
        doc.annotations.update(self.annotate(doc))

    @abstractmethod
    def annotate(self, doc: Document) -> list[Annotation]:
        """
        Generate annotations for a document.

        Args:
            doc: The document that should be annotated.

        Returns:
            A list of annotations.
        """

    def _match_sequence(
        self,
        doc: Document,
        seq_pattern: SequencePattern,
        start_token: Token,
        annos_by_token: defaultdict[Token, Iterable[Annotation]],
        dicts: Optional[DsCollection],
    ) -> Optional[Annotation]:
        """
        Matches a token sequence pattern at `start_token`.

        Args:
            doc: The document.
            seq_pattern: The pattern to match.
            start_token: The start token to match.
            annos_by_token: Map from tokens to annotations covering it.
            dicts: Lookup dictionaries available.

        Returns:
              An Annotation if matching is possible, None otherwise.
        """

        dir_ = seq_pattern.direction

        tokens = (
            token
            for token in start_token.iter_to(dir_)
            if token.text not in seq_pattern.skip
        )
        # Iterate the token patterns in the direction corresponding to the surface
        # order it's supposed to match (i.e. "left" means "iterate patterns from the
        # end").
        tok_patterns = dir_.iter(seq_pattern.pattern)

        num_matched = 0
        end_token = start_token
        for tok_pattern, end_token in zip(tok_patterns, tokens):
            if _PatternPositionMatcher.match(
                token_pattern=tok_pattern,
                token=end_token,
                annos=annos_by_token[end_token],
                ds=dicts,
                metadata=doc.metadata,
            ):
                num_matched += 1
            else:
                break

        if num_matched != len(seq_pattern.pattern):
            return None

        left_token, right_token = dir_.iter((start_token, end_token))

        return Annotation(
            text=doc.text[left_token.start_char : right_token.end_char],
            start_char=left_token.start_char,
            end_char=right_token.end_char,
            tag=self.tag,
            priority=self.priority,
            start_token=left_token,
            end_token=right_token,
        )


class SingleTokenLookupAnnotator(Annotator):
    """
    Matches single tokens based on lookup values.

    Args:
        lookup_values: An iterable of strings that should be used for lookup.
        matching_pipeline: An optional pipeline that can be used for matching
            (e.g. lowercasing). Note that this degrades performance.
        tokenizer_name: If not taking tokens from the ``default`` tokenizer, specify
            which tokenizer to use. The tokenizer should be present in
            :attr:`.DocDeid.tokenizers`.
    """

    def __init__(
        self,
        lookup_values: Iterable[str],
        *args,
        matching_pipeline: Optional[list[StringModifier]] = None,
        tokenizer_name: str = "default",
        **kwargs,
    ) -> None:

        self.lookup_set = LookupSet(matching_pipeline=matching_pipeline)
        self.lookup_set.add_items_from_iterable(items=lookup_values)
        self._tokenizer_name = tokenizer_name
        super().__init__(*args, **kwargs)

    def _tokens_to_annotations(self, tokens: Iterable[Token]) -> list[Annotation]:

        return [
            Annotation(
                text=token.text,
                start_char=token.start_char,
                end_char=token.end_char,
                tag=self.tag,
                priority=self.priority,
                start_token=token,
                end_token=token,
            )
            for token in tokens
        ]

    def annotate(self, doc: Document) -> list[Annotation]:

        tokens = doc.get_tokens(tokenizer_name=self._tokenizer_name)

        annotate_tokens = tokens.token_lookup(
            self.lookup_set.items(), matching_pipeline=self.lookup_set.matching_pipeline
        )

        return self._tokens_to_annotations(annotate_tokens)


class MultiTokenLookupAnnotator(Annotator):
    """
    Annotates entity mentions by looking them up in a `LookupTrie`.

    Args:
        trie: The `LookupTrie` containing all entity mentions that should be annotated.
        overlapping: Whether overlapping phrases are to be returned.
        *args, **kwargs: Passed through to the `Annotator` constructor (which accepts
            the arguments `tag` and `priority`).
    """

    def __init__(
        self,
        *args,
        trie: LookupTrie,
        overlapping: bool = False,
        **kwargs,
    ) -> None:

        self._trie = trie
        self._overlapping = overlapping
        self._start_words = set(trie.children)

        super().__init__(*args, **kwargs)

    @property
    def start_words(self) -> set[str]:
        """First words of phrases detected by this annotator."""
        # If the trie has been modified (added to) since we computed
        # _start_words,
        if len(self._start_words) != len(self._trie.children):
            # Recompute _start_words.
            self._start_words = set(self._trie.children)
        return self._start_words

    def annotate(self, doc: Document) -> list[Annotation]:

        tokens = doc.get_tokens()

        start_tokens = sorted(
            tokens.token_lookup(
                self.start_words, matching_pipeline=self._trie.matching_pipeline
            ),
            key=lambda token: token.start_char,
        )

        start_indices = [tokens.token_index(token) for token in start_tokens]

        tokens_text = [token.text for token in tokens]
        annotations = []
        min_i = 0

        for i in start_indices:

            if i < min_i:
                continue

            longest_matching_prefix = self._trie.longest_matching_prefix(
                tokens_text, start_i=i
            )

            if longest_matching_prefix is None:
                continue

            start_token = tokens[i]
            end_token = tokens[i + len(longest_matching_prefix) - 1]

            annotations.append(
                Annotation(
                    text=doc.text[start_token.start_char : end_token.end_char],
                    start_char=start_token.start_char,
                    end_char=end_token.end_char,
                    start_token=start_token,
                    end_token=end_token,
                    tag=self.tag,
                    priority=self.priority,
                )
            )

            if not self._overlapping:
                min_i = i + len(longest_matching_prefix)  # skip ahead

        return annotations


class RegexpAnnotator(Annotator):
    """
    Create annotations based on regular expression patterns. Note that these patterns do
    not necessarily start/stop on token boundaries.

    Args:
        regexp_pattern: A pattern, either as a `str` or a ``re.Pattern``, that will
            be used for matching.
        capturing_group: The capturing group of the pattern that should be used to
            produce the annotation. By default, the entire match is used.
        pre_match_words: A list of words (lookup values), of which at least one must
            be present in the tokens for the annotator to start matching the regexp
            at all.
    """

    def __init__(
        self,
        regexp_pattern: Union[re.Pattern, str],
        *args,
        capturing_group: int = 0,
        pre_match_words: Optional[list[str]] = None,
        **kwargs,
    ) -> None:

        if isinstance(regexp_pattern, str):
            regexp_pattern = re.compile(regexp_pattern)

        self.regexp_pattern = regexp_pattern
        self.capturing_group = capturing_group

        self.pre_match_words: Optional[set[str]] = None
        self.matching_pipeline: Optional[list[StringModifier]] = None

        if pre_match_words is not None:
            self.pre_match_words = set(pre_match_words)
            self.matching_pipeline = [docdeid.str.LowercaseString()]

        super().__init__(*args, **kwargs)

    def _validate_match(
        self, match: re.Match, doc: Document  # pylint: disable=W0613
    ) -> bool:
        return True

    def annotate(self, doc: Document) -> list[Annotation]:

        if self.pre_match_words is not None:
            try:
                if (
                    doc.get_tokens()
                    .get_words(self.matching_pipeline)
                    .isdisjoint(self.pre_match_words)
                ):
                    return []
            except RuntimeError:
                pass

        annotations = []

        for match in self.regexp_pattern.finditer(doc.text):

            if not self._validate_match(match, doc):
                continue

            text = match.group(self.capturing_group)
            start_char, end_char = match.span(self.capturing_group)

            annotations.append(
                Annotation(
                    text=text,
                    start_char=start_char,
                    end_char=end_char,
                    tag=self.tag,
                    priority=self.priority,
                )
            )

        return annotations


class TokenPatternAnnotator(Annotator):
    """
    Annotate based on :class:`.TokenPattern`.

    Args:
        pattern: The token pattern that should be used.
    """

    def __init__(self, pattern: TokenPattern, *args, **kwargs) -> None:
        self.pattern = pattern
        kwargs["tag"] = pattern.tag
        super().__init__(*args, **kwargs)

    def annotate(self, doc: Document) -> list[Annotation]:
        annotations: list[Annotation] = []

        if not self.pattern.doc_precondition(doc):
            return annotations

        for token in doc.get_tokens():

            if not self.pattern.token_precondition(token):
                continue

            match = self.pattern.match(token, doc.metadata)

            if match is None:
                continue

            start_token, end_token = match

            annotations.append(
                Annotation(
                    text=doc.text[start_token.start_char : end_token.end_char],
                    start_char=start_token.start_char,
                    end_char=end_token.end_char,
                    tag=self.tag,
                    priority=self.priority,
                    start_token=start_token,
                    end_token=end_token,
                )
            )

        return annotations


class _PatternPositionMatcher:  # pylint: disable=R0903
    """Checks if a token matches against a single pattern."""

    @classmethod
    def match(cls, token_pattern: Union[dict, TokenPatternFromCfg], **kwargs) -> bool:
        # pylint: disable=R0911
        """
        Matches a pattern position (a dict with one key). Other information should be
        presented as kwargs.

        Args:
            token_pattern: A dictionary with a single key, e.g. {'is_initial': True}
            kwargs: Any other information, like the token or ds

        Returns:
            True if the pattern position matches, false otherwise.
        """

        if isinstance(token_pattern, dict):
            return cls.match(as_token_pattern(token_pattern), **kwargs)

        func = token_pattern.func
        value = token_pattern.pattern

        if func == "equal":
            return kwargs["token"].text == value
        if func == "re_match":
            return re.match(value, kwargs["token"].text) is not None
        if func == "is_initial":

            warnings.warn(
                "is_initial matcher pattern is deprecated and will be removed "
                "in a future version",
                DeprecationWarning,
            )

            return (
                (len(kwargs["token"].text) == 1 and kwargs["token"].text[0].isupper())
                or kwargs["token"].text in {"Ch", "Chr", "Ph", "Th"}
            ) == value
        if func == "is_initials":
            return (
                len(kwargs["token"].text) <= 4 and kwargs["token"].text.isupper()
            ) == value
        if func == "like_name":
            return (
                len(kwargs["token"].text) >= 3
                and kwargs["token"].text.istitle()
                and not any(ch.isdigit() for ch in kwargs["token"].text)
            ) == value
        if func == "lookup":
            return cls._lookup(value, **kwargs)
        if func == "neg_lookup":
            return not cls._lookup(value, **kwargs)
        if func == "tag":
            annos = kwargs.get("annos", ())
            return any(anno.tag == value for anno in annos)
        if func == "and":
            return all(cls.match(x, **kwargs) for x in value)
        if func == "or":
            return any(cls.match(x, **kwargs) for x in value)

        raise NotImplementedError(f"No known logic for pattern {func}")

    @classmethod
    def _lookup(cls, ent_type: str, **kwargs) -> bool:
        token = kwargs["token"].text
        if "." in ent_type:
            meta_key, meta_attr = ent_type.split(".", 1)
            try:
                meta_val = getattr(kwargs["metadata"][meta_key], meta_attr)
            except (TypeError, KeyError, AttributeError):
                return False
            return token == meta_val if isinstance(meta_val, str) else token in meta_val
        else:  # pylint: disable=R1705
            return token in kwargs["ds"][ent_type]


def as_token_pattern(pat_dict: dict) -> TokenPatternFromCfg:
    """
    Converts the JSON dictionary representation of token patterns into a
    `TokenPatternFromCfg` instance.

    Args:
        pat_dict: the JSON representation of the pattern
    """
    if len(pat_dict) != 1:
        raise ValueError(
            f"Cannot parse a token pattern which doesn't have exactly 1 key: "
            f"{pat_dict}."
        )
    func, value = next(iter(pat_dict.items()))
    if func in ("and", "or"):
        return NestedTokenPattern(func, list(map(as_token_pattern, value)))
    return SimpleTokenPattern(func, value)


class SequenceAnnotator(Annotator):
    """
    Annotates based on token patterns, which should be provided as a list of dicts. Each
    position in the list denotes a token position, e.g.: [{'is_initial': True},
    {'like_name': True}] matches sequences of two tokens, where the first one is an
    initial, and the second one is like a name.

    Arguments:
        pattern: The pattern
        ds: Lookup dictionaries. Those referenced by the pattern should be LookupSets.
            (Don't ask why.)
        skip: Any string values that should be skipped in matching (e.g. periods)
    """

    def __init__(
        self,
        pattern: list[dict],
        *args,
        ds: Optional[DsCollection] = None,
        skip: Optional[list[str]] = None,
        **kwargs,
    ) -> None:
        self.pattern = pattern
        self.ds = ds
        self.skip = set(skip or [])

        self._start_words = None
        self._matching_pipeline = None

        if len(self.pattern) > 0 and "lookup" in self.pattern[0]:

            if self.ds is None:
                raise RuntimeError(
                    "Created pattern with lookup in TokenPatternAnnotator, but "
                    "no lookup structures provided."
                )

            lookup_list = self.ds[self.pattern[0]["lookup"]]

            # FIXME This doesn't work correctly for multiple ([{"lookup":"prefix"},
            #  {"lookup":"interfix"}]) and nested patterns ("or", "and").
            if not isinstance(lookup_list, LookupSet):
                raise ValueError(
                    f"Expected a LookupSet, but got a " f"{type(lookup_list)}."
                )

            # FIXME This doesn't work correctly for multiple ([{"lookup":"prefix"},
            #  {"lookup":"interfix"}]) and nested patterns ("or", "and").
            self._start_words = lookup_list.items()
            # FIXME This doesn't work correctly for multiple ([{"lookup":"prefix"},
            #  {"lookup":"interfix"}]) and nested patterns ("or", "and").
            self._matching_pipeline = lookup_list.matching_pipeline

        self._seq_pattern = SequencePattern(
            Direction.RIGHT, set(skip or ()), list(map(as_token_pattern, pattern))
        )

        super().__init__(*args, **kwargs)

    def annotate(self, doc: Document) -> list[Annotation]:
        """
        Annotate the document, by matching the pattern against all tokens.

        Args:
            doc: The document being processed.

        Returns:
            A list of Annotation.
        """

        annotations = []

        token_list = doc.get_tokens()

        if self._start_words is not None:
            tokens: Iterable[Token] = token_list.token_lookup(
                lookup_values=self._start_words,
                matching_pipeline=self._matching_pipeline,
            )
        else:
            tokens = token_list  # ...to make Mypy happy.

        annos_by_token = doc.annos_by_token()

        for token in tokens:

            annotation = self._match_sequence(
                doc, self._seq_pattern, token, annos_by_token, self.ds
            )

            if annotation is not None:
                annotations.append(annotation)

        return annotations
