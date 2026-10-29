import json
from pathlib import Path
import pypdfium2 as pdfium
from app.config import ROOT
def test_every_clause_resolves_to_its_pdf_page():
 for clause in json.loads((ROOT/'corpus/clauses.json').read_text()):
  d=pdfium.PdfDocument(ROOT/'corpus'/clause['file'])
  text=' '.join(d[clause['page']-1].get_textpage().get_text_range().split())
  assert clause['text'] in text,clause['id']
