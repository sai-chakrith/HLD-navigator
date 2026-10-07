import io
from pathlib import Path

import pytest
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table

from archlens.extraction import extract


def test_text_pdf_actual_page_evidence():
    stream = io.BytesIO()
    pdf = canvas.Canvas(stream)
    pdf.drawString(50, 750, "Component: Engine | description=Computes torque")
    pdf.showPage()
    pdf.drawString(50, 750, "Signal: Torque | type=uint16 | unit=Nm")
    pdf.save()
    blocks, entities, warnings = extract("fixture.pdf", stream.getvalue())
    assert len(entities) == 2 and not warnings
    assert [(e.name, e.location.page) for e in entities] == [("Engine", 1), ("Torque", 2)]
    assert all(b.location.page in {1, 2} for b in blocks)


def test_scanned_or_empty_pdf_requires_ocr():
    stream = io.BytesIO()
    pdf = canvas.Canvas(stream)
    pdf.rect(50, 50, 100, 100)
    pdf.showPage()
    pdf.save()
    with pytest.raises(ValueError, match="OCR"):
        extract("scan.pdf", stream.getvalue())


def test_pdf_table_actual_row_evidence():
    stream = io.BytesIO()
    doc = SimpleDocTemplate(stream)
    table = Table([["Kind", "Name", "description"], ["Component", "Engine", "Torque computation"]])
    table.setStyle([("GRID", (0, 0), (-1, -1), 1, "black")])
    doc.build([table])
    _, entities, warnings = extract("table.pdf", stream.getvalue())
    assert len(entities) == 1 and not warnings
    assert entities[0].location.page == 1
    assert entities[0].location.table == 1
    assert entities[0].location.row == 2


def test_ui_initial_load():
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(str(Path(__file__).parents[1] / "src/archlens/ui.py")).run()
    assert not app.exception
    assert "ArchLens" in app.title[0].value
    assert "Provision" in app.info[0].value
