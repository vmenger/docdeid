from docdeid import Annotation, Document
from docdeid.utils import annotate_intext


class TestAnnotateIntext:
    def test_annotate_intext(self):
        text = "My name is John and I live in Japan"
        doc = Document(text=text)
        doc.annotations.add(
            Annotation(text="John", start_char=11, end_char=15, tag="name")
        )
        doc.annotations.add(
            Annotation(text="Japan", start_char=30, end_char=35, tag="location")
        )

        expected_text = (
            "My name is <NAME>John</NAME> and I live in <LOCATION>Japan</LOCATION>"
        )

        assert annotate_intext(doc) == expected_text
