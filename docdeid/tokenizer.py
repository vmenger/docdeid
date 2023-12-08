from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterator, Literal, Optional

from docdeid.str import StringModifier


@dataclass(frozen=True)
class Token:
    """A token is an atomic part of a text, as determined by a tokenizer."""

    text: str
    """The text."""

    start_char: int
    """The start char."""

    end_char: int
    """The end char."""

    _previous_token: Optional[Token] = field(default=None, repr=False, compare=False)
    """
    The previous token.

    Note that this does not have to be the literal next token in the text, the logic
    is dictated by :meth:`.Tokenizer._previous_token`, which could for example take
    the previous alpha token.
    """

    _next_token: Optional[Token] = field(default=None, repr=False, compare=False)
    """
    The next token.

    Note that this does not have to be the literal next token in the text, the logic
    is dictated by :meth:`.Tokenizer._next_token`, which could for example take
    the next alpha token.
    """

    def __post_init__(self) -> None:
        if len(self.text) != (self.end_char - self.start_char):
            raise ValueError("The span does not match the length of the text.")

    def __getstate__(self) -> dict:
        return {
            "text": self.text,
            "start_char": self.start_char,
            "end_char": self.end_char,
        }

    def set_previous_token(self, token: Optional[Token]) -> None:
        """
        Set the previous token, in a linked list fashion.

        Args:
            token: The previous :class:`.Token`.
        """
        object.__setattr__(self, "_previous_token", token)

    def set_next_token(self, token: Optional[Token]) -> None:
        """
        Set the next token, in a linked list fashion.

        Args:
            token: The next :class:`.Token`.
        """
        object.__setattr__(self, "_next_token", token)

    def _get_linked_token(
        self, num: int, attr: Literal["_previous_token", "_next_token"]
    ) -> Optional[Token]:
        """
        Helper method for getting previous/next tokens, possibly more than one
        neighbour.

        Args:
            num: Searches the ``num``-th token to the left/right.
            attr: Either ``_previous_token`` or ``_next_token``, depending on which
                to look for.

        Returns:
            The token ``num`` positions to the left/right, if any, or ``None``
            otherwise.
        """

        token = self

        for _ in range(num):
            token = getattr(token, attr)

            if token is None:
                return None

        return token

    def previous(self, num: int = 1) -> Optional[Token]:
        """
        Get the previous :class:`.Token`, if any.

        Args:
            num: Searches the ``num``-th token to the left.

        Returns:
            The token ``num`` positions to the left, if any, or ``None`` otherwise.
        """
        return self._get_linked_token(num=num, attr="_previous_token")

    def next(self, num: int = 1) -> Optional[Token]:
        """
        Get the next :class:`.Token`, if any.

        Args:
            num: Searches the ``num``-th token to the right.

        Returns:
            The token ``num`` positions to the right, if any, or ``None`` otherwise.
        """
        return self._get_linked_token(num=num, attr="_next_token")

    def __len__(self) -> int:
        """
        The length of the text.

        Returns:
            The length of the text.
        """
        return len(self.text)


class TokenList:
    """
    Contains a sequence of tokens, along with some lookup logic.

    Args:
        tokens: The input tokens (must be final).
    """

    def __init__(self, tokens: list[Token], link_tokens: bool = True) -> None:
        self._tokens = tokens
        self._token_index = {token: i for i, token in enumerate(tokens)}

        if link_tokens:
            self._link_tokens()

        self._words: dict[str, set[str]] = {}
        self._text_to_tokens: dict[str, defaultdict[str, list[Token]]] = {}

    def _link_tokens(self) -> None:

        for i in range(len(self._tokens) - 1):
            self._tokens[i].set_next_token(self._tokens[i + 1])
            self._tokens[i + 1].set_previous_token(self._tokens[i])

    def token_index(self, token: Token) -> int:
        """
        Find the token index in this list, i.e. its nominal position in the list.

        Args:
            token: The input token.

        Returns: The index in this tokenlist.
        """
        return self._token_index[token]

    def _init_token_lookup(
        self, matching_pipeline: Optional[list[StringModifier]] = None
    ) -> None:

        matching_pipeline = matching_pipeline or []
        pipe_key = str(matching_pipeline)

        words = set()
        text_to_tokens = defaultdict(list)

        for token in self._tokens:

            text = token.text

            for string_modifier in matching_pipeline:
                text = string_modifier.process(text)

            words.add(text)
            text_to_tokens[text].append(token)

        self._words[pipe_key] = words
        self._text_to_tokens[pipe_key] = text_to_tokens

    def get_words(
        self, matching_pipeline: Optional[list[StringModifier]] = None
    ) -> set[str]:
        """
        Get all unique words (i.e. token texts) in this ``TokenList``. Evaluates lazily.

        Args:
            matching_pipeline: The matching pipeline to apply.

        Returns:
            All the words in this ``TokenList`` as a set of strings.
        """

        matching_pipeline = matching_pipeline or []
        pipe_key = str(matching_pipeline)

        if pipe_key not in self._words:
            self._init_token_lookup(matching_pipeline)

        return self._words[pipe_key]

    def token_lookup(
        self,
        lookup_values: set[str],
        matching_pipeline: Optional[list[StringModifier]] = None,
    ) -> set[Token]:
        """
        Lookup all tokens of which the text matches a certain set of lookup values.
        Evaluates lazily.

        Args:
            lookup_values: The set of lookup values to match the token text against.
            matching_pipeline: The matching pipeline.

        Returns:
            A set of ``Token``, of which the text matches one of the lookup values.
        """

        matching_pipeline = matching_pipeline or []
        pipe_key = str(matching_pipeline)

        if pipe_key not in self._text_to_tokens:
            self._init_token_lookup(matching_pipeline)

        tokens = set()
        words = self.get_words(matching_pipeline)

        for word in words.intersection(lookup_values):
            tokens.update(self._text_to_tokens[pipe_key][word])

        return tokens

    def __iter__(self) -> Iterator[Token]:

        return iter(self._tokens)

    def __len__(self) -> int:

        return len(self._tokens)

    def __getitem__(self, index: int) -> Token:

        return self._tokens[index]

    def __eq__(self, other: object) -> bool:
        """
        Check if two :class:`.TokenList` are equal, by matching the tokens.

        Args:
            other: The other :class:`.TokenList`.

        Returns:
            ``True`` if the tokens exactly match, ``False`` otherwise. Does not check
            text equality but
                :class:`.Token` equality.

        Raises:
            ValueError: When trying to check equality of something different from a
            :class:`.TokenList`.
        """

        if not isinstance(other, TokenList):
            raise ValueError(f"Cannot compare {self.__class__} to {other.__class__}")

        return self._tokens == other._tokens


class Tokenizer(ABC):  # pylint: disable=R0903
    """
    Abstract class for tokenizers, which split a text up in its smallest parts called
    tokens. Implementations should implement :meth:`.Tokenizer._split_text`.

    Args:
        link_tokens: Whether the produced :class:`TokenList` should link the tokens.
    """

    def __init__(self, link_tokens: bool = True) -> None:
        self.link_tokens = link_tokens

    @abstractmethod
    def _split_text(self, text: str) -> list[Token]:
        """
        Abstract method for splitting the text. Instantiations of :class:`.Tokenizer`
        should implement this.

        Args:
            text: The input text.

        Returns:
            A list of tokens, as determined by the tokenizer logic.
        """

    def tokenize(self, text: str) -> TokenList:
        """
        Tokenize a text, based on the logic implemented in
        :meth:`.Tokenizer._split_text`.

        Args:
            text: The input text.

        Returns:
            A :class:`.TokenList`, containing the created tokens.
        """

        tokens = self._split_text(text)

        return TokenList(tokens, link_tokens=self.link_tokens)


class SpaceSplitTokenizer(Tokenizer):  # pylint: disable=R0903
    """
    Tokenizes based on splitting on whitespaces.

    Whitespaces themselves are not included as tokens.
    """

    def _split_text(self, text: str) -> list[Token]:
        return [
            Token(text=match.group(0), start_char=match.start(), end_char=match.end())
            for match in re.finditer(r"\S+", text)
        ]


class WordBoundaryTokenizer(Tokenizer):  # pylint: disable=R0903
    """
    Tokenizes based on word boundary.

    Whitespaces and similar characters are included as tokens.
    """

    def _split_text(self, text: str) -> list[Token]:
        tokens = []
        matches = [*re.finditer(r"\b", text)]

        for start_match, end_match in zip(matches, matches[1:]):

            start_char = start_match.span(0)[0]
            end_char = end_match.span(0)[0]

            tokens.append(
                Token(
                    text=text[start_char:end_char],
                    start_char=start_char,
                    end_char=end_char,
                )
            )

        return tokens
