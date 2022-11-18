from docdeid.document import Document


def annotate_intext(doc: Document) -> str:
    """
    Annotate intext, which can be useful to compare the annotations of two different runs. This function replaces each
    piece of annotated text of a document with ``<TAG>text</TAG>``.

    Args:
        doc: The :class:`.Document` as input, containing a text and zero or more annotations.

    Returns:
        A string with each annotated span replaced with ``<TAG>text</TAG>``.
    """
    annotations = doc.annotations.sorted(
        by=["end_char"],
        callbacks={"end_char": lambda x: -x},
    )

    text = doc.text

    for annotation in annotations:

        text = (
            f"{text[:annotation.start_char]}"
            f"<{annotation.tag.upper()}>{annotation.text}</{annotation.tag.upper()}>"
            f"{text[annotation.end_char:]}"
        )

    return text
