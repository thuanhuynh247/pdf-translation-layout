#!/usr/bin/env python3
"""Chạy trọn quy trình trên PDF mẫu với bản dịch tham chiếu (thay cho AI), rồi chấm điểm.

Dùng để tái lập số liệu trong KET_QUA.md, và để thử nhanh sau khi sửa mã:
    python benchmark/chay_mau.py benchmark/mau/mau_6trang.pdf --xuat ket_qua_do
Bản dịch tham chiếu (benchmark/mau/ban_dich_tham_chieu.json) do tác giả dịch tay, khóa theo câu gốc.
"""
import argparse, json, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
S = HERE.parent / "skills" / "pdf-translation-layout" / "scripts" / "dich_pdf.py"


def run(work, *args):
    r = subprocess.run([sys.executable, str(S), "--thu-muc", work, *args], capture_output=True, text=True)
    if r.returncode not in (0, 2):
        sys.exit(r.stdout + r.stderr)
    return r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--xuat", default="ket_qua_do")
    ap.add_argument("--ban-dich", default=str(HERE / "mau" / "ban_dich_tham_chieu.json"))
    ap.add_argument("--csv", default="")
    a = ap.parse_args()
    td = json.loads(Path(a.ban_dich).read_text(encoding="utf-8"))
    work = tempfile.mkdtemp(prefix="dich_pdf_")
    run(work, "chuan-bi", a.pdf, "--lo", "15")
    thieu = set()
    for _ in range(500):
        out = run(work, "lay-lo")
        if "---BẮT ĐẦU---" not in out:
            break
        body = out.split("---BẮT ĐẦU---")[1].split("---HẾT---")[0].strip()
        items = [json.loads(l) for l in body.splitlines() if l.strip()]
        tr = {}
        for it in items:
            if it["text"] in td:
                tr[it["id"]] = td[it["text"]]
            else:
                thieu.add(it["text"][:60])
                tr[it["id"]] = it["text"]
        f = Path(work) / "lo_tam.json"
        f.write_text(json.dumps(tr, ensure_ascii=False), encoding="utf-8")
        run(work, "nap-lo", str(f))
    if thieu:
        print("Câu chưa có trong bản dịch tham chiếu:", *sorted(thieu), sep="\n  ")
    print(run(work, "dung", "--che-do", "tat-ca", "--xuat", a.xuat).strip().splitlines()[-2])
    kd = run(work, "kiem-dinh", "--xuat", a.xuat)
    print(next(l for l in kd.splitlines() if "Kết luận" in l))
    stem = Path(a.pdf).stem
    args = ["cham-diem", "--goc", a.pdf, "--dich", str(Path(a.xuat) / f"{stem}_VI.pdf"), "--ten", "pdf-translation-layout 3.1"]
    if a.csv:
        args += ["--csv", a.csv]
    print(run(work, *args))


if __name__ == "__main__":
    main()
