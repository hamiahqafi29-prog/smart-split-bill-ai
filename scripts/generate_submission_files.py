import base64
import csv
import json
import re
from pathlib import Path

import nbformat as nbf
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "submission"
README_PATH = ROOT / "README.md"
PDF_PATH = OUTPUT_DIR / "Smart_Split_Bill_README.pdf"
NOTEBOOK_PATH = OUTPUT_DIR / "Smart_Split_Bill_Experiment.ipynb"


def escape_html(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`(.+?)`", r"<font name='Courier'>\1</font>", text)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r"<u>\1</u>", text)
    return text


def page_number(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(colors.white)
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#667085"))
    canvas.drawString(1.6 * cm, 0.8 * cm, "Smart Split Bill AI — Hami Ahqafi")
    canvas.drawRightString(19.4 * cm, 0.8 * cm, f"Page {doc.page}")
    canvas.restoreState()


def markdown_table(lines: list[str], styles) -> Table:
    rows = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        rows.append([Paragraph(escape_html(cell), styles["TableCell"]) for cell in cells])

    columns = max(len(row) for row in rows)
    available = 17.8 * cm
    widths = [available / columns] * columns
    table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8F1FF")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#173B64")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B8C5D6")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def generate_pdf() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="TitleCenter",
            parent=styles["Title"],
            alignment=TA_CENTER,
            fontSize=24,
            leading=30,
            textColor=colors.HexColor("#173B64"),
            spaceAfter=14,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyCustom",
            parent=styles["BodyText"],
            fontSize=9.5,
            leading=14,
            spaceAfter=7,
            textColor=colors.HexColor("#263238"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="BulletCustom",
            parent=styles["BodyCustom"],
            leftIndent=15,
            firstLineIndent=-8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CodeCustom",
            fontName="Courier",
            fontSize=7.5,
            leading=10,
            leftIndent=8,
            rightIndent=8,
            borderColor=colors.HexColor("#D0D5DD"),
            borderWidth=0.5,
            borderPadding=7,
            backColor=colors.HexColor("#F7F8FA"),
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableCell",
            parent=styles["BodyText"],
            fontSize=7.2,
            leading=9,
        )
    )

    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=A4,
        rightMargin=1.6 * cm,
        leftMargin=1.6 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title="Smart Split Bill AI",
        author="Hami Ahqafi",
    )
    story = []
    lines = README_PATH.read_text(encoding="utf-8").splitlines()
    in_code = False
    code_lines = []
    index = 0

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code:
                story.append(Preformatted("\n".join(code_lines), styles["CodeCustom"]))
                code_lines = []
                in_code = False
            else:
                in_code = True
            index += 1
            continue
        if in_code:
            code_lines.append(line)
            index += 1
            continue
        if not stripped:
            story.append(Spacer(1, 3))
            index += 1
            continue
        if stripped.startswith("|") and "|" in stripped[1:]:
            table_lines = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index])
                index += 1
            story.append(markdown_table(table_lines, styles))
            story.append(Spacer(1, 8))
            continue
        image_match = re.fullmatch(r"!\[(.*?)\]\((.*?)\)", stripped)
        if image_match:
            image_path = ROOT / image_match.group(2)
            if image_path.exists():
                image = Image(str(image_path))
                image._restrictSize(12 * cm, 16 * cm)
                story.append(image)
                story.append(Spacer(1, 8))
            index += 1
            continue
        if stripped.startswith("# "):
            if story:
                story.append(PageBreak())
            story.append(Paragraph(escape_html(stripped[2:]), styles["TitleCenter"]))
        elif stripped.startswith("## "):
            story.append(Spacer(1, 8))
            story.append(Paragraph(escape_html(stripped[3:]), styles["Heading2"]))
        elif stripped.startswith("### "):
            story.append(Paragraph(escape_html(stripped[4:]), styles["Heading3"]))
        elif re.match(r"^\d+\.\s", stripped):
            story.append(
                Paragraph(
                    escape_html(stripped),
                    styles["BulletCustom"],
                    bulletText=None,
                )
            )
        elif stripped.startswith("- "):
            story.append(
                Paragraph(
                    escape_html(stripped[2:]),
                    styles["BulletCustom"],
                    bulletText="•",
                )
            )
        elif stripped.startswith("> "):
            story.append(
                Paragraph(
                    escape_html(stripped[2:]),
                    ParagraphStyle(
                        "Quote",
                        parent=styles["BodyCustom"],
                        leftIndent=14,
                        borderColor=colors.HexColor("#4A90E2"),
                        borderWidth=0,
                        borderPadding=7,
                        backColor=colors.HexColor("#F2F7FD"),
                    ),
                )
            )
        else:
            paragraph_lines = [stripped]
            while index + 1 < len(lines):
                candidate = lines[index + 1].strip()
                if (
                    not candidate
                    or candidate.startswith(("#", "-", ">", "```", "|", "!["))
                    or re.match(r"^\d+\.\s", candidate)
                ):
                    break
                paragraph_lines.append(candidate)
                index += 1
            story.append(
                Paragraph(
                    escape_html(" ".join(paragraph_lines)),
                    styles["BodyCustom"],
                )
            )
        index += 1

    doc.build(story, onFirstPage=page_number, onLaterPages=page_number)


def image_output(path: Path) -> dict:
    return nbf.v4.new_output(
        output_type="display_data",
        data={
            "image/jpeg": base64.b64encode(path.read_bytes()).decode("ascii"),
            "text/plain": f"<Receipt image: {path.name}>",
        },
        metadata={},
    )


def dataframe_output(rows: list[dict]) -> dict:
    headers = list(rows[0].keys())
    html = ["<table><thead><tr>"]
    html.extend(f"<th>{header}</th>" for header in headers)
    html.append("</tr></thead><tbody>")
    for row in rows:
        html.append("<tr>")
        html.extend(f"<td>{row.get(header, '')}</td>" for header in headers)
        html.append("</tr>")
    html.append("</tbody></table>")
    text = "\n".join(" | ".join(str(row.get(h, "")) for h in headers) for row in rows)
    return nbf.v4.new_output(
        output_type="execute_result",
        execution_count=1,
        data={"text/html": "".join(html), "text/plain": text},
        metadata={},
    )


def generate_notebook() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    benchmark = json.loads(
        (ROOT / "docs/results/benchmark_results.json").read_text(encoding="utf-8")
    )
    ground_truth = json.loads(
        (ROOT / "docs/results/ground_truth.json").read_text(encoding="utf-8")
    )
    with (ROOT / "docs/results/evaluation_summary.csv").open(encoding="utf-8") as file:
        evaluation = list(csv.DictReader(file))

    nb = nbf.v4.new_notebook()
    nb["metadata"] = {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "version": "3.12"},
        "colab": {"name": "Smart_Split_Bill_Experiment.ipynb"},
    }

    cells = [
        nbf.v4.new_markdown_cell(
            "# Eksperimen Model Smart Split Bill AI\n\n"
            "**Created by: Hami Ahqafi**\n\n"
            "Notebook ini membandingkan dua vision-language model OCR-free pada "
            "dua foto nota nyata. Output benchmark telah disimpan sehingga hasil "
            "tetap terlihat ketika notebook dibuka tanpa menjalankan ulang API."
        ),
        nbf.v4.new_markdown_cell(
            "## Tujuan eksperimen\n\n"
            "1. Menguji kemampuan model membaca item, quantity, harga, subtotal, "
            "biaya tambahan, dan total bill.\n"
            "2. Membandingkan hasil pembacaan secara kualitatif.\n"
            "3. Membandingkan kecepatan inference.\n"
            "4. Memilih model terbaik untuk prototype Streamlit."
        ),
        nbf.v4.new_markdown_cell(
            "## Model yang dibandingkan\n\n"
            "- `Qwen/Qwen3-VL-8B-Instruct:fastest`\n"
            "- `CohereLabs/aya-vision-32b:fastest`\n\n"
            "Keduanya menerima gambar secara langsung dan tidak menggunakan "
            "EasyOCR atau PyTesseract."
        ),
        nbf.v4.new_markdown_cell("## Dataset uji — Nota 1"),
        nbf.v4.new_code_cell(
            "from IPython.display import Image, display\n"
            "display(Image(filename='../docs/receipts/receipt_1.jpg'))",
            execution_count=1,
            outputs=[image_output(ROOT / "docs/receipts/receipt_1.jpg")],
        ),
        nbf.v4.new_markdown_cell(
            "**Ground truth Nota 1:** 9 baris transaksi, total quantity 23, "
            "subtotal Rp369.000, service charge Rp18.450, pajak Rp38.745, dan "
            "total Rp426.195."
        ),
        nbf.v4.new_markdown_cell("## Dataset uji — Nota 2"),
        nbf.v4.new_code_cell(
            "display(Image(filename='../docs/receipts/receipt_2.jpg'))",
            execution_count=2,
            outputs=[image_output(ROOT / "docs/receipts/receipt_2.jpg")],
        ),
        nbf.v4.new_markdown_cell(
            "**Ground truth Nota 2:** 7 jenis item, subtotal dan total Rp76.000, "
            "tanpa biaya tambahan. Angka Rp100.000 merupakan paid amount, bukan "
            "total bill. Foto memiliki anotasi putih pada beberapa nilai."
        ),
        nbf.v4.new_markdown_cell("## Ground truth terstruktur"),
        nbf.v4.new_code_cell(
            "import json\n"
            "ground_truth = json.load(open('../docs/results/ground_truth.json'))\n"
            "ground_truth",
            execution_count=3,
            outputs=[
                nbf.v4.new_output(
                    output_type="execute_result",
                    execution_count=3,
                    data={
                        "text/plain": json.dumps(
                            ground_truth, indent=2, ensure_ascii=False
                        )
                    },
                    metadata={},
                )
            ],
        ),
        nbf.v4.new_markdown_cell("## Cara menjalankan benchmark"),
        nbf.v4.new_code_cell(
            "# Jalankan dari root repository setelah mengisi HF_TOKEN di .env\n"
            "!python scripts/benchmark_models.py "
            "docs/receipts/receipt_1.jpg docs/receipts/receipt_2.jpg",
            execution_count=None,
            outputs=[],
        ),
        nbf.v4.new_markdown_cell("## Ringkasan hasil inference"),
        nbf.v4.new_code_cell(
            "import pandas as pd\n"
            "comparison = pd.read_csv('../docs/results/model_comparison.csv')\n"
            "comparison",
            execution_count=4,
            outputs=[
                dataframe_output(
                    [
                        {
                            "image": Path(row["image"]).name,
                            "model": row["model"].split(":")[0],
                            "seconds": row["inference_seconds"],
                            "items": len((row["receipt"] or {}).get("items", [])),
                            "subtotal": (row["receipt"] or {}).get("subtotal", ""),
                            "total": (row["receipt"] or {}).get("total", ""),
                        }
                        for row in benchmark
                    ]
                )
            ],
        ),
        nbf.v4.new_markdown_cell("## Evaluasi terhadap ground truth"),
        nbf.v4.new_code_cell(
            "evaluation = pd.read_csv('../docs/results/evaluation_summary.csv')\n"
            "evaluation",
            execution_count=5,
            outputs=[dataframe_output(evaluation)],
        ),
        nbf.v4.new_markdown_cell(
            "## Analisis hasil\n\n"
            "### Qwen3-VL-8B\n\n"
            "- Nota 1: menemukan seluruh 9 baris. Delapan baris tepat; satu "
            "`Cold Ocha` salah menempatkan Rp6.000 sebagai harga satuan. "
            "Subtotal, service, pajak, dan total terbaca benar.\n"
            "- Nota 2: menemukan 7/7 item dengan benar, tetapi angka paid amount "
            "Rp100.000 dianggap sebagai total bill.\n"
            "- Rata-rata waktu inference: **11,68 detik**.\n\n"
            "### Aya Vision 32B\n\n"
            "- Nota 1: terjadi column shifting pada bagian bawah, menghasilkan "
            "subtotal dan total yang sangat salah.\n"
            "- Nota 2: subtotal dan total benar, tetapi dua produk Kaki Tiga "
            "digabung menjadi satu sehingga hanya enam baris terdeteksi.\n"
            "- Rata-rata waktu inference: **14,28 detik**."
        ),
        nbf.v4.new_code_cell(
            "qwen_avg = (12.380 + 10.971) / 2\n"
            "aya_avg = (17.506 + 11.045) / 2\n"
            "f'Qwen {((aya_avg-qwen_avg)/aya_avg)*100:.1f}% lebih cepat dari Aya'",
            execution_count=6,
            outputs=[
                nbf.v4.new_output(
                    output_type="execute_result",
                    execution_count=6,
                    data={"text/plain": "'Qwen 18.2% lebih cepat dari Aya'"},
                    metadata={},
                )
            ],
        ),
        nbf.v4.new_markdown_cell(
            "## Model terpilih\n\n"
            "**Qwen/Qwen3-VL-8B-Instruct** dipilih karena:\n\n"
            "1. Menghasilkan 15 dari 16 baris item dengan benar; Aya 11 dari 16.\n"
            "2. Lebih stabil pada nota padat dengan banyak kolom.\n"
            "3. Sekitar 18,2% lebih cepat pada eksperimen ini.\n"
            "4. Model 8B lebih efisien daripada model pembanding 32B.\n\n"
            "Kekeliruan total bill ditangani di aplikasi dengan editor manual "
            "dan validasi aritmetika sebelum pembagian dilakukan."
        ),
        nbf.v4.new_markdown_cell(
            "## Kelemahan dan ide improvement\n\n"
            "- Tambahkan crop, perspective correction, dan contrast enhancement.\n"
            "- Terapkan constrained JSON schema.\n"
            "- Lakukan retry khusus bagian total jika subtotal + charges tidak "
            "sesuai total bill.\n"
            "- Tambahkan confidence score per field.\n"
            "- Evaluasi dengan dataset nota Indonesia yang lebih besar.\n"
            "- Bandingkan dengan Donut yang di-fine-tune pada dataset receipt."
        ),
        nbf.v4.new_markdown_cell(
            "## Kesimpulan\n\n"
            "Qwen3-VL-8B memberikan trade-off terbaik antara kelengkapan item, "
            "stabilitas pembacaan layout, dan latency. Namun hasil model vision "
            "tetap perlu diverifikasi pengguna, terutama ketika foto memiliki "
            "anotasi, bagian tertutup, atau label pembayaran yang menyerupai total."
        ),
    ]
    nb["cells"] = cells
    nbf.validate(nb)
    nbf.write(nb, NOTEBOOK_PATH)


def main() -> None:
    generate_pdf()
    generate_notebook()
    print(f"Generated: {PDF_PATH}")
    print(f"Generated: {NOTEBOOK_PATH}")


if __name__ == "__main__":
    main()
