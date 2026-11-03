"""web_api.py — lớp mỏng để trang web gọi dich_pdf.py (chạy trong trình duyệt bằng Pyodide).

Mỗi hàm nhận/trả chuỗi JSON để JavaScript dùng thẳng. Mọi việc diễn ra trong bộ nhớ của trình duyệt:
tài liệu không được gửi đi đâu. Logic tách đoạn, chia lô, nạp bản dịch, dựng PDF, kiểm định dùng nguyên
dich_pdf.py, nên kết quả giống hệt bản chạy trong Claude, ChatGPT, Antigravity.
"""
from __future__ import annotations

import contextlib
import io
import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, "/app/scripts")
import dich_pdf as D  # noqa: E402

WORK = "/tmp/work"
OUT = "/tmp/out"


def _ns(**kw):
    base = dict(thu_muc=WORK, viec=None)
    base.update(kw)
    return SimpleNamespace(**base)


def _run(fn, **kw):
    buf = io.StringIO()
    code = 0
    with contextlib.redirect_stdout(buf):
        try:
            code = fn(_ns(**kw)) or 0
        except SystemExit as e:  # dich_pdf báo lỗi bằng sys.exit("thông điệp")
            if isinstance(e.code, str):
                print(e.code)
                code = 1
            else:
                code = e.code or 0
    return code, buf.getvalue().strip()


def _job():
    return D._job_dir(_ns())


def _progress() -> dict:
    job = _job()
    batches = D._load(job / "lo.json", [])
    trans = D._load(job / "ban_dich.json", {})
    total = sum(len(b["ids"]) for b in batches)
    done = sum(1 for b in batches for i in b["ids"] if trans.get(i))
    return {"done": done, "total": total, "batches_done": sum(b["xong"] for b in batches),
            "batches_total": len(batches)}


def prepare(pdf_path: str, lo: int = 15, trang: str = "", huong: str = "tu-dong") -> str:
    """huong: "tu-dong" (nhận theo ngôn ngữ tài liệu), "en-vi" hoặc "vi-en"."""
    shutil.rmtree(WORK, ignore_errors=True)
    shutil.rmtree(OUT, ignore_errors=True)
    code, out = _run(D.cmd_chuan_bi, pdf=pdf_path, lo=lo, lam_lai=True, trang=trang or None, huong=huong or "tu-dong")
    if code:
        return json.dumps({"ok": False, "error": out})
    job = _job()
    meta = D._load(job / "meta.json")
    pages = D._load(job / "trang.json")
    families = sorted({s.get("family", "sans") for p in pages for s in p["segments"]} | {"sans"})
    words = sum(len(s["text"].split()) for p in pages for s in p["segments"] if s["translate"])
    chars = sum(len(t) for t in {s["text"] for p in pages for s in p["segments"] if s["translate"]})  # bỏ trùng
    h = meta.get("huong", "en-vi")
    return json.dumps({"ok": True, "message": out, "name": meta["ten"], "pages": meta["so_trang"],
                       "scanned": meta.get("trang_scan", []), "families": families, "words": words,
                       "chars": chars, "huong": h, "rules": D.QUY_TAC[h], "rules_end": D.DONG_KET[h],
                       "clean": meta.get("lam_sach", {}), **_progress()}, ensure_ascii=False)


def next_items(max_chars: int = 6000) -> str:
    """Các đoạn chưa dịch của lô kế tiếp (đã bỏ trùng), tối đa max_chars ký tự."""
    code, out = _run(D.cmd_lay_lo, lo=0, toi_da=max_chars)
    if code:
        return json.dumps({"ok": False, "error": out}, ensure_ascii=False)
    items = []
    if "---BẮT ĐẦU---" in out:
        body = out.split("---BẮT ĐẦU---", 1)[1].split("---HẾT---", 1)[0]
        items = [json.loads(line) for line in body.splitlines() if line.strip()]
    head = out.splitlines()[0] if out else ""
    return json.dumps({"ok": True, "items": items, "header": head, **_progress()}, ensure_ascii=False)


def load(text: str) -> str:
    """Nạp bản dịch dạng JSON {id: bản dịch} (hoặc văn bản có chứa JSON đó, như câu trả lời của AI)."""
    job = _job()
    idx = D._seg_index(job)
    tmp = Path("/tmp/nap_lo.json")
    tmp.write_text(text, encoding="utf-8")  # đưa qua file: chuỗi dài không dùng làm đường dẫn được
    code, out = _run(D.cmd_nap_lo, file=str(tmp))
    if code:
        return json.dumps({"ok": False, "error": out or "Không đọc được JSON bản dịch."}, ensure_ascii=False)
    warn = {}
    huong = D._huong(job)
    try:
        import re
        data = json.loads(re.search(r"\{.*\}|\[.*\]", text, flags=re.S).group(0))
        if isinstance(data, dict):
            for k, v in data.items():
                if k in idx and v:
                    w = D._check_translation(idx[k]["text"], str(v), huong)
                    if w:
                        warn[k] = {"warning": w, "source": idx[k]["text"], "vi": str(v)}
    except Exception:
        pass
    return json.dumps({"ok": True, "message": out, "warnings": warn, **_progress()}, ensure_ascii=False)


def missing_ids(ids_json: str) -> str:
    """Trong danh sách id vừa gửi đi, id nào vẫn chưa có bản dịch (AI bỏ sót)."""
    trans = D._load(_job() / "ban_dich.json", {})
    return json.dumps([i for i in json.loads(ids_json) if not trans.get(i)])


def translations() -> str:
    """Toàn bộ bản dịch hiện có, để trình duyệt lưu lại phòng khi tải lại trang."""
    return json.dumps(D._load(_job() / "ban_dich.json", {}), ensure_ascii=False)


def items_for(ids_json: str) -> str:
    """Các đoạn theo danh sách id (để dịch lại đoạn nghi vấn)."""
    idx = D._seg_index(_job())
    out = []
    for i in json.loads(ids_json):
        if i in idx:
            out.append({"id": i, "text": idx[i]["text"], **({"loai": "tieu-de"} if idx[i].get("kind") == "tieu-de" else {})})
    return json.dumps(out, ensure_ascii=False)


def zip_all() -> str:
    """Gói mọi file kết quả vào một file zip."""
    import zipfile
    files = sorted(p for p in Path(OUT).iterdir() if p.suffix in (".pdf", ".md"))
    if not files:
        return json.dumps({"ok": False})
    stem = Path(D._load(_job() / "meta.json")["ten"]).stem
    zp = Path(OUT) / f"{stem}_ban-dich.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(f, f.name)
    return json.dumps({"ok": True, "name": zp.name, "path": str(zp), "size": zp.stat().st_size})


def progress() -> str:
    return json.dumps(_progress())


def build(che_do: str = "tat-ca", footer: bool = True) -> str:
    code, out = _run(D.cmd_dung, che_do=che_do, xuat=OUT, khong_chan_trang=not footer)
    if code:
        return json.dumps({"ok": False, "error": out}, ensure_ascii=False)
    files = [{"name": p.name, "path": str(p), "size": p.stat().st_size}
             for p in sorted(Path(OUT).glob("*.pdf"))]
    return json.dumps({"ok": True, "message": out, "files": files}, ensure_ascii=False)


def qa() -> str:
    code, out = _run(D.cmd_kiem_dinh, xuat=OUT)
    job = _job()
    report = D._load(job / "kiem_dinh.json", {})
    md = next(Path(OUT).glob("*_phieu-kiem-dinh.md"), None)
    return json.dumps({"ok": code in (0, 2), "pass": bool(report.get("dat")), "checks": report.get("checks", []),
                       "huong": report.get("huong", "en-vi"),
                       "report_name": md.name if md else "", "report_path": str(md) if md else "",
                       "report_md": md.read_text(encoding="utf-8") if md else out,
                       "nghi_van": report.get("nghi_van", {}), "tran": report.get("tran", []),
                       "chua_dich": report.get("chua_dich", [])}, ensure_ascii=False)


def score(goc_path: str, dich_path: str, ten: str = "") -> str:
    """Chấm một PDF đã dịch (của bất kỳ công cụ nào) so với bản gốc: 7 chỉ số của bộ đo."""
    code, out = _run(D.cmd_cham_diem, goc=goc_path, dich=dich_path, ten=ten, csv="")
    if code:
        return json.dumps({"ok": False, "error": out}, ensure_ascii=False)
    try:
        start = out.index("{")
        return json.dumps({"ok": True, **json.loads(out[start:])}, ensure_ascii=False)
    except Exception:
        return json.dumps({"ok": False, "error": out}, ensure_ascii=False)
