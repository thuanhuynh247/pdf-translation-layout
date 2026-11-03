#!/usr/bin/env python3
"""Đường cơ sở để đối chiếu: cách "thay chữ thô" mà nhiều script dịch PDF nhanh hay dùng.

Cùng bản dịch tham chiếu, cùng vị trí đoạn, nhưng ghi chữ bằng phông Helvetica có sẵn trong chuẩn PDF
(không có dấu tiếng Việt), không tính lại khung chữ, chỉ giảm cỡ chữ khi không vừa. Dùng để cho thấy bộ chấm bắt được lỗi gì;
đây KHÔNG phải sản phẩm của bên nào.
    python benchmark/duong_co_so.py benchmark/mau/mau_6trang.pdf --xuat ket_qua_do
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "skills" / "pdf-translation-layout" / "scripts"))
import dich_pdf  # noqa: E402

fz = dich_pdf._import_pymupdf()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--xuat", default="ket_qua_do")
    ap.add_argument("--ban-dich", default=str(HERE / "mau" / "ban_dich_tham_chieu.json"))
    a = ap.parse_args()
    td = json.loads(Path(a.ban_dich).read_text(encoding="utf-8"))
    doc = fz.open(a.pdf)
    pages = dich_pdf.extract_segments(doc)
    for pinfo in pages:
        page = doc[pinfo["page"] - 1]
        todo = [s for s in pinfo["segments"] if s["translate"] and s["text"] in td]
        for s in todo:
            page.add_redact_annot(fz.Rect(s["rect"]), fill=(1, 1, 1))
        page.apply_redactions(images=0, graphics=0)
        for s in todo:  # chữ không vừa khung thì giảm cỡ dần, như các script thông thường
            size = s["size"]
            while page.insert_textbox(fz.Rect(s["rect"]), td[s["text"]], fontname="helv", fontsize=size) < 0 and size > 4:
                size -= 0.5
    out = Path(a.xuat) / f"{Path(a.pdf).stem}_duong-co-so.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out, garbage=4, deflate=True)
    print(out)


if __name__ == "__main__":
    main()
