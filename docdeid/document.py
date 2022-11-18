from typing import Any, Optional

from docdeid.annotation import AnnotationSet
from docdeid.tokenize import Tokenizer, TokenList


class MetaData:
    """
    Contains additional information on a text that is provided by the user on input. A :class:`.MetaData` object is
    kept with the text in a :class:`.Document`, where it can be accessed by document processors. Note that a
    :class:`.MetaData` object does not allow overwriting keys. This is done to prevent document processors
    accidentally interfering with each other.

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
            raise RuntimeError(f"Key {key} already present in {self.__class__}, cannot overwrite (read only)")

        self._items[key] = value


class Document:
    """
    Contains the text, its tokens, and other derived info after document processors have been applied to it.

    Args:
        text: The input text
        tokenizers: A mapping of tokenizer names to :class:`.Tokenizer`. If only one tokenizer is used,
            ``default`` may be used as name to allow :meth:`Document.get_tokens` to be called without a tokenizer name.
        metadata: A dict with items, that can be accessed by document processors. Will be stored in a
            :class:`.MetaData` object.
    """

    def __init__(
        self,
        text: str,
        tokenizers: Optional[dict[str, Tokenizer]] = None,
        metadata: Optional[dict] = None,
    ) -> None:

        self._text = text
        self._tokenizers = tokenizers

        self.metadata = MetaData(metadata)
        """ The :class:`.MetaData` of this :class:`.Document`, that can be interacted with directly. """

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

    def get_tokens(self, tokenizer_name: str = "default") -> TokenList:
        """
        Get the tokens corresponding to the input text, for a specific tokenizer.

        Args:
            tokenizer_name: The name of the tokenizer, that should be one of the tokenizers passed when initializing
                the :class:`.Document`.

        Returns:
            A :class:`.TokenList` containing the requested tokens.

        Raises:
            RuntimeError: If no tokenizers are initialized.
            ValueError: If the requested tokenizer is unknown.
        """

        if self._tokenizers is None:
            raise RuntimeError("No tokenizers initialized.")

        if tokenizer_name not in self._tokenizers:
            raise ValueError(f"Cannot get tokens from unknown tokenizer {tokenizer_name}.")

        if tokenizer_name not in self._token_lists:
            self._token_lists[tokenizer_name] = self._tokenizers[tokenizer_name].tokenize(self._text)

        return self._token_lists[tokenizer_name]

    @property
    def annotations(self) -> AnnotationSet:
        """
        Get the annotations.

        Returns:
            An :class:`.AnnotationSet` containing the annotations belonging to this document.
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
