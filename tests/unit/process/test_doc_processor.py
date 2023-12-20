from unittest.mock import patch

from docdeid import Document
from docdeid.process.doc_processor import DocProcessor, DocProcessorGroup


class TestDocProcessorGroup:
    @patch("docdeid.process.doc_processor.DocProcessor.__abstractmethods__", set())
    def test_create_doc_processor_group(self):
        proc_1 = DocProcessor()
        proc_2 = DocProcessor()

        dpg = DocProcessorGroup()
        dpg.add_processor("proc_1", proc_1)
        dpg.add_processor("proc_2", proc_2)

        with patch.object(proc_1, "process") as proc_1_process, patch.object(
            proc_2, "process"
        ) as proc_2_process:

            dpg.process(Document(text="test"))

            proc_1_process.assert_called_once()
            proc_2_process.assert_called_once()

    @patch("docdeid.process.doc_processor.DocProcessor.__abstractmethods__", set())
    def test_doc_processor_add_at_position(self):
        dpg = DocProcessorGroup()
        proc = DocProcessor()
        dpg.add_processor("proc_1", proc)
        dpg.add_processor("proc_2", proc)
        dpg.add_processor("proc_3", proc, position=1)

        assert dpg.get_names() == ["proc_1", "proc_3", "proc_2"]

    @patch("docdeid.process.doc_processor.DocProcessor.__abstractmethods__", set())
    def test_create_doc_processor_group_enabled(self):
        proc_1 = DocProcessor()
        proc_2 = DocProcessor()

        dpg = DocProcessorGroup()
        dpg.add_processor("proc_1", proc_1)
        dpg.add_processor("proc_2", proc_2)

        with patch.object(proc_1, "process") as proc_1_process, patch.object(
            proc_2, "process"
        ) as proc_2_process:

            dpg.process(Document(text="test"), enabled={"proc_2"})

            proc_1_process.assert_not_called()
            proc_2_process.assert_called_once()

    @patch("docdeid.process.doc_processor.DocProcessor.__abstractmethods__", set())
    def test_create_doc_processor_group_disabled(self):
        proc_1 = DocProcessor()
        proc_2 = DocProcessor()

        dpg = DocProcessorGroup()
        dpg.add_processor("proc_1", proc_1)
        dpg.add_processor("proc_2", proc_2)

        with patch.object(proc_1, "process") as proc_1_process, patch.object(
            proc_2, "process"
        ) as proc_2_process:

            dpg.process(Document(text="test"), disabled={"proc_1"})

            proc_1_process.assert_not_called()
            proc_2_process.assert_called_once()

    @patch("docdeid.process.doc_processor.DocProcessor.__abstractmethods__", set())
    def test_doc_processor_group_names(self):
        dpg = DocProcessorGroup()
        dpg.add_processor("proc_1", DocProcessor())
        dpg.add_processor("proc_2", DocProcessor())

        dpg_nested = DocProcessorGroup()
        dpg_nested.add_processor("nested_proc_1", DocProcessor())

        dpg.add_processor("nested_group", dpg_nested)

        assert dpg.get_names(recursive=False) == ["proc_1", "proc_2", "nested_group"]
        assert dpg.get_names(recursive=True) == [
            "proc_1",
            "proc_2",
            "nested_group",
            "nested_proc_1",
        ]

    @patch("docdeid.process.doc_processor.DocProcessor.__abstractmethods__", set())
    def test_remove_doc_processor(self):
        dpg = DocProcessorGroup()
        proc_1 = DocProcessor()
        dpg.add_processor("proc_1", proc_1)
        dpg.remove_processor("proc_1")

        with patch.object(proc_1, "process") as proc_1_process:
            dpg.process(doc=Document(text="test"))
            proc_1_process.assert_not_called()

    @patch("docdeid.process.doc_processor.DocProcessor.__abstractmethods__", set())
    def test_get_doc_processor(self):
        dpg = DocProcessorGroup()
        proc_1 = DocProcessor()
        dpg.add_processor("proc_1", proc_1)

        assert dpg["proc_1"] is proc_1
