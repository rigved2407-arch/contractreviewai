from pathlib import Path
from docx import Document
from docx.shared import RGBColor, Pt
from docx.oxml.ns import qn

RED = RGBColor(0xFF, 0x00, 0x00)
GREEN = RGBColor(0x00, 0x80, 0x00)


def _add_redline_tracking(doc: Document):
    """Enable Track Changes in the document."""
    body = doc.element.body
    body.insert(0, _make_revision_marker())


def _make_revision_marker():
    from lxml import etree
    p = etree.SubElement(
        etree.Element(qn("w:p")),
        qn("w:pPr"),
    )
    rsid = etree.SubElement(p, qn("w:rsid"))
    rsid.set(qn("w:val"), "00000001")
    return p


def generate_redlined_docx(
    original_path: str,
    clauses: list[dict],
    output_path: str,
) -> str:
    doc = Document(original_path)
    _add_redline_tracking(doc)

    for clause in clauses:
        if not clause.get("suggested_redline"):
            continue
        _apply_redline(doc, clause)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_path)
    return output_path


def _apply_redline(doc: Document, clause: dict):
    orig_text = clause.get("clause_text", "")
    suggested = clause.get("suggested_redline", "")
    if not orig_text or not suggested:
        return

    for para in doc.paragraphs:
        if orig_text.strip() in para.text.strip():
            _strikethrough_run(para, orig_text)
            _insert_suggestion_after(para, suggested)
            break


def _strikethrough_run(para, text_to_remove):
    for run in para.runs:
        if text_to_remove in run.text:
            run.font.color.rgb = RED
            run.font.strike = True
            run.font.size = Pt(10)


def _insert_suggestion_after(para, suggested_text):
    from docx.oxml.ns import qn
    from lxml import etree

    new_run = para.add_run(f"\n\n[SUGGESTED]: {suggested_text}")
    new_run.font.color.rgb = GREEN
    new_run.font.size = Pt(10)
    rpr = new_run._element.get_or_add_rPr()
    rpr.append(etree.SubElement(rpr, qn("w:rPr")))
