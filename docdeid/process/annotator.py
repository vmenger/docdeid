import re
from abc import ABC, abstractmethod
from typing import Iterable, Optional, Union

import docdeid.str
from docdeid.annotation import Annotation
from docdeid.document import Document
from docdeid.ds.lookup import LookupSet, LookupTrie
from docdeid.pattern import TokenPattern
from docdeid.process.doc_processor import DocProcessor
from docdeid.str.processor import StringModifier
from docdeid.tokenizer import Token, Tokenizer


class Annotator(DocProcessor, ABC):
    """
    Abstract class for annotators, which are responsible for generating annotations from
    a given document. Instatiations should implement the annotate method.

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
    Matches lookup values against tokens, where the ``lookup_values`` may themselves be
    sequences.

    Args:
        lookup_values: An iterable of strings, that should be matched. These are
            tokenized internally.
        matching_pipeline: An optional pipeline that can be used for matching
            (e.g. lowercasing). This has no specific impact on matching performance,
            other than overhead for applying the pipeline to each string.
        tokenizer: A tokenizer that is used to create the sequence patterns from
            ``lookup_values``.
        trie: A trie that is used for matching, rather than a combination of
            `lookup_values` and a `matching_pipeline` (cannot be used simultaneously).
        overlapping: Whether the annotator should match overlapping sequences,
            or should process from left to right.

    Raises:
        RunTimeError, when an incorrect combination of `lookup_values`,
        `matching_pipeline` and `trie` is supplied.
    """

    def __init__(
        self,
        *args,
        lookup_values: Optional[Iterable[str]] = None,
        matching_pipeline: Optional[list[StringModifier]] = None,
        tokenizer: Optional[Tokenizer] = None,
        trie: Optional[LookupTrie] = None,
        overlapping: bool = False,
        **kwargs,
    ) -> None:

        self._start_words: set[str] = set()

        if (trie is not None) and (lookup_values is None) and (tokenizer is None):

            self._trie = trie
            self._matching_pipeline = trie.matching_pipeline or []
            self._start_words = set(trie.children.keys())

        elif (trie is None) and (lookup_values is not None) and (tokenizer is not None):
            self._matching_pipeline = matching_pipeline or []
            self._trie = LookupTrie(matching_pipeline=matching_pipeline)
            self._init_lookup_structures(lookup_values, tokenizer)

        else:
            raise RuntimeError(
                "Please provide either looup_values and a tokenizer, or a trie."
            )

        self.overlapping = overlapping

        super().__init__(*args, **kwargs)

    def _init_lookup_structures(
        self, lookup_values: Iterable[str], tokenizer: Tokenizer
    ) -> None:

        for val in lookup_values:

            texts = [token.text for token in tokenizer.tokenize(val)]

            if len(texts) > 0:
                self._trie.add_item(texts)

                start_token = texts[0]

                for string_modifier in self._matching_pipeline:
                    start_token = string_modifier.process(start_token)

                self._start_words.add(start_token)

    def annotate(self, doc: Document) -> list[Annotation]:

        tokens = doc.get_tokens()

        start_tokens = sorted(
            tokens.token_lookup(
                self._start_words, matching_pipeline=self._matching_pipeline
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

            if not self.overlapping:
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
