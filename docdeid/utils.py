from collections import defaultdict

from frozendict import frozendict

from docdeid.document import Document


def annotate_intext(doc: Document) -> str:
    """
    Annotate intext, which can be useful to compare the annotations of two different
    runs. This function replaces each piece of annotated text of a document with
    ``<TAG>text</TAG>``.

    Args:
        doc: The :class:`.Document` as input, containing a text and zero or more
        annotations.

    Returns:
        A string with each annotated span replaced with ``<TAG>text</TAG>``.
    """
    annotations = doc.annotations.sorted(
        by=("end_char",),
        callbacks=frozendict(end_char=lambda x: -x),
    )

    text = doc.text

    for annotation in annotations:

        text = (
            f"{text[:annotation.start_char]}"
            f"<{annotation.tag.upper()}>{annotation.text}</{annotation.tag.upper()}>"
            f"{text[annotation.end_char:]}"
        )

    return text


def annotate_doc(doc: Document) -> str:
    """
    Adds XML-like markup for annotations into the text of a document.

    Handles also nested mentions and in a way also overlapping mentions, even though
    this kind of markup cannot really represent them.
    """
    annos_from_shortest = sorted(
        doc.annotations, key=lambda anno: anno.end_char - anno.start_char
    )
    idx_to_anno_starts = defaultdict(list)
    idx_to_anno_ends = defaultdict(list)
    for anno in annos_from_shortest:
        idx_to_anno_starts[anno.start_char].append(anno)
        idx_to_anno_ends[anno.end_char].append(anno)
    markup_indices = sorted(set(idx_to_anno_starts).union(idx_to_anno_ends))
    chunks = list()
    last_idx = 0
    for idx in markup_indices:
        chunks.append(doc.text[last_idx:idx])
        for ending_anno in idx_to_anno_ends[idx]:
            chunks.append(f"</{ending_anno.tag.upper()}>")
        for starting_anno in reversed(idx_to_anno_starts[idx]):
            chunks.append(f"<{starting_anno.tag.upper()}>")
        last_idx = idx
    chunks.append(doc.text[last_idx:])
    return "".join(chunks)
