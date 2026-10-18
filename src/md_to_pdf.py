"""Convert a policy .md file into a text-based PDF.

The PDF keeps real text (not pictures), so pypdf can read the headings back.
Run from the project root:  python -m src.md_to_pdf
"""
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer

ROOT = Path(__file__).resolve().parent.parent
SOURCE_MD = ROOT / "docs" / "policy_sources" / "performance_review_policy.md"
OUTPUT_PDF = ROOT / "data" / "policies" / "performance_review_policy.pdf"


def read_policy(path: Path) -> tuple[dict[str, str], str]:
    """Split a policy file into its YAML header (as a dict) and its body text."""
    lines = path.read_text(encoding="utf-8").splitlines()
    meta: dict[str, str] = {}
    body_start = 0
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                body_start = i + 1
                break
            key, _, value = lines[i].partition(":")
            meta[key.strip()] = value.strip()
    return meta, "\n".join(lines[body_start:])


def build_story(meta: dict[str, str], body: str) -> list[Flowable]:
    """Turn the markdown body into a list of PDF blocks (headings, text, bullets)."""
    styles = getSampleStyleSheet()
    bullet_style = ParagraphStyle("Bullet", parent=styles["BodyText"],
                                  leftIndent=18, bulletIndent=6)
    story: list[Flowable] = []

    for line in body.splitlines():
        text = line.strip()
        if not text:
            continue
        if text.startswith("## "):
            story.append(Paragraph(escape(text[3:]), styles["Heading2"]))
        elif text.startswith("# "):
            story.append(Paragraph(escape(text[2:]), styles["Title"]))
            date = meta.get("effective_date", "unknown")
            story.append(Paragraph(f"Effective date: {escape(date)}", styles["BodyText"]))
            story.append(Spacer(1, 0.3 * cm))
        elif text.startswith("- "):
            story.append(Paragraph(escape(text[2:]), bullet_style, bulletText="-"))
        else:
            story.append(Paragraph(escape(text), styles["BodyText"]))
    return story


def convert(source: Path, target: Path) -> None:
    """Read one markdown policy and write it as a PDF."""
    meta, body = read_policy(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(target),
        pagesize=A4,
        title=meta.get("title", source.stem),
        author="HR Policy Copilot (fictional company)",
    )
    doc.build(build_story(meta, body))


def main() -> None:
    """Convert the performance review policy and say where the PDF went."""
    convert(SOURCE_MD, OUTPUT_PDF)
    print(f"Created {OUTPUT_PDF}")


if __name__ == "__main__":
    main()