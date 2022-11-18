from docdeid.annotation import Annotation, AnnotationSet
from docdeid.process.redactor import RedactAllText, SimpleRedactor


class TestRedactAllText:
    def test_redact_all_text(self):

        redactor = RedactAllText()

        deidentified_text = redactor.redact(text="some text", annotations=AnnotationSet([]))

        assert deidentified_text == "[REDACTED]"


class TestSimpleRedactor:
    def test_redact_one_annotation(self):

        text = "Hello I'm Bob"
        annotations = AnnotationSet([Annotation(text="Bob", start_char=10, end_char=13, tag="name")])
        redactor = SimpleRedactor()

        deidentified_text = redactor.redact(text, annotations)

        assert deidentified_text == "Hello I'm [NAME-1]"

    def test_redact_multiple_annotations_different(self):

        text = "Hello I'm Bob, and this is Rita"
        annotations = AnnotationSet(
            [
                Annotation(text="Bob", start_char=10, end_char=13, tag="name"),
                Annotation(text="Rita", start_char=27, end_char=31, tag="name"),
            ]
        )
        redactor = SimpleRedactor()

        deidentified_text = redactor.redact(text, annotations)

        assert deidentified_text == "Hello I'm [NAME-1], and this is [NAME-2]"

    def test_redact_multiple_annotations_same(self):

        text = "Hello I'm Bob, and Bob is my name"

        annotations = AnnotationSet(
            [
                Annotation(text="Bob", start_char=10, end_char=13, tag="name"),
                Annotation(text="Bob", start_char=19, end_char=22, tag="name"),
            ]
        )
        redactor = SimpleRedactor()

        deidentified_text = redactor.redact(text, annotations)

        assert deidentified_text == "Hello I'm [NAME-1], and [NAME-1] is my name"

    def test_redact_multiple_annotations_different_tag(self):

        text = "Hello I'm Bob, and I live in London"
        annotations = AnnotationSet(
            [
                Annotation(text="Bob", start_char=10, end_char=13, tag="name"),
                Annotation(text="London", start_char=29, end_char=35, tag="location"),
            ]
        )
        redactor = SimpleRedactor()

        deidentified_text = redactor.redact(text, annotations)

        assert deidentified_text == "Hello I'm [NAME-1], and I live in [LOCATION-1]"
