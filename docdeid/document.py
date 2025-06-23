from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Optional

from frozendict import frozendict

from docdeid.annotation import Annotation, AnnotationSet
from docdeid.tokenizer import Token, Tokenizer, TokenList


class MetaData:
    """
    Contains additional information on a text that is provided by the user on input. A
    :class:`.MetaData` object is kept with the text in a :class:`.Document`, where it
    can be accessed by document processors. Note that a :class:`.MetaData` object does
    not allow overwriting keys. This is done to prevent document processors accidentally
    interfering with each other.

    Args:
        items: A ``dict`` of items to initialize with.
    """

    def __init__(self, items: Optional[dict] = None) -> None:
        self._items = items or {}

    def __getitem__(self, key: str) -> Optional[Any]:
        """
        Get an item.

        Args:
            key: The key.

        Returns:
            The item, with ``None`` as default.
        """
        return self._items.get(key, None)

    def __setitem__(self, key: str, value: Any) -> None:
        """
        Add an item.

        Args:
            key: The key.
            value: The value.

        Raises:
            RuntimeError: When the key is already present.
        """

        if key in self._items:
            raise RuntimeError(
                f"Key {key} already present in {self.__class__}, cannot overwrite "
                f"(read only)"
            )

        self._items[key] = value


class Document:
    """
    Contains the text, its tokens, and other derived info after document processors have
    been applied to it.

    Args:
        text: The input text
        tokenizers: A mapping of tokenizer names to :class:`.Tokenizer`. If only one
            tokenizer is used, ``default`` may be used as name to allow
            :meth:`Document.get_tokens` to be called without a tokenizer name.
        metadata: A dict with items, that can be accessed by document processors.
            Will be stored in a :class:`.MetaData` object.
    """

    @dataclass
    class AnnosByToken:
        """A cache entry associating an `AnnotationSet` with a token->annos map."""
        anno_set: AnnotationSet
        value: defaultdict[Token, set[Annotation]]

    def __init__(
        self,
        text: str,
        tokenizers: Optional[dict[str, Tokenizer]] = None,
        metadata: Optional[dict] = None,
    ) -> None:

        self._text = text
        self._tokenizers = None if tokenizers is None else frozendict(tokenizers)
        self._default_annos_by_token = Document.AnnosByToken(None, None)
        self._tmp_annos_by_token = Document.AnnosByToken(None, None)

        self.metadata = MetaData(metadata)
        """The :class:`.MetaData` of this :class:`.Document`, that can be interacted
        with directly."""

        self._token_lists: dict[str, TokenList] = {}
        self._annotations = AnnotationSet()
        self._deidentified_text: Optional[str] = None

    @property
    def text(self) -> str:
        """
        The document text.

        Returns:
            The original and unmodified text.
        """
        return self._text

    @property
    def tokenizers(self) -> Mapping[str, Tokenizer]:
        """Available tokenizers indexed by their name."""
        if self._tokenizers is None:
            raise RuntimeError("No tokenizers initialized.")
        return self._tokenizers

    def get_tokens(self, tokenizer_name: str = "default") -> TokenList:
        """
        Get the tokens corresponding to the input text, for a specific tokenizer.

        Args:
            tokenizer_name: The name of the tokenizer, that should be one of the
            tokenizers passed when initializing the :class:`.Document`.

        Returns:
            A :class:`.TokenList` containing the requested tokens.

        Raises:
            RuntimeError: If no tokenizers are initialized.
            ValueError: If the requested tokenizer is unknown.
        """

        if self._tokenizers is None:
            raise RuntimeError("No tokenizers initialized.")

        if tokenizer_name not in self._tokenizers:
            raise ValueError(
                f"Cannot get tokens from unknown tokenizer {tokenizer_name}."
            )

        if tokenizer_name not in self._token_lists:
            self._token_lists[tokenizer_name] = self._tokenizers[
                tokenizer_name
            ].tokenize(self._text)

        return self._token_lists[tokenizer_name]

    @property
    def annotations(self) -> AnnotationSet:
        """
        Get the annotations.

        Returns:
            An :class:`.AnnotationSet` containing the annotations belonging to
            this document.
        """
        return self._annotations

    @annotations.setter
    def annotations(self, annotations: AnnotationSet) -> None:
        """
        Set annotations.

        Args:
            annotations: The new annotations.
        """
        self._annotations = annotations

    def annos_by_token(
            self,
            annos: AnnotationSet = None,
    ) -> defaultdict[Token, set[Annotation]]:
        """
        Returns a mapping from document tokens to annotations.

        Args:
            annos: annotations for this document to index by token (default: current
                   annotations of this `Document`)
        """

        # Fill the default arg value.
        if annos is None:
            eff_annos = self._annotations
            cache = self._default_annos_by_token
        else:
            eff_annos = annos
            cache = self._tmp_annos_by_token

        # Try to use a cached response.
        if eff_annos == cache.anno_set:
            return cache.value

        # Compute the return value.
        annos_by_token = defaultdict(set)
        for tokenizer in self.tokenizers:
            token_list = self.get_tokens(tokenizer)
            if not token_list:
                continue
            cur_tok_idx = 0
            tok = token_list[cur_tok_idx]
            for anno in eff_annos.sorted(by=("start_char",)):
                try:
                    # Iterate over tokens till we reach the annotation.
                    while tok.end_char < anno.start_char:
                        cur_tok_idx += 1
                        tok = token_list[cur_tok_idx]
                except IndexError:
                    break
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

        # Cache the value before returning.
        cache.anno_set = eff_annos
        cache.value = annos_by_token
        return annos_by_token

    @property
    def deidentified_text(self) -> Optional[str]:
        """
        Get the deidentified text.

        Returns:
            The deidentified text, if set by a document processor (else ``None``).
        """

        return self._deidentified_text

    def set_deidentified_text(self, deidentified_text: str) -> None:
        """
        Set the deidentified text.

        Args:
            deidentified_text: The deidentified text.
        """

        self._deidentified_text = deidentified_text
