#!/usr/bin/env python3
"""Lắp bộ máy cho trang "Dịch PDF trên web" (web/dich.html) vào thư mục website.

    python tools/dung_web.py <thư mục website>

Chép dich.html, assets/js/dich-app.js, assets/js/dich-worker.js, và dựng thư mục engine/ gồm:
  pyodide/      lõi Pyodide 0.29.5 (tải bằng `npm pack pyodide@0.29.5`)
  pymupdf-1.28.2-cp313-abi3-pyemscripten_2025_0_wasm32.whl   (tải từ PyPI)
  fonts/        16 phông của skill + giấy phép
  dich_pdf.py, web_api.py, NOTICE.txt
Thư mục engine/ là bản dự phòng: mặc định (ENGINE_SOURCE "cdn" trong config.js) trình duyệt tải Pyodide từ
jsDelivr và PyMuPDF từ PyPI, kiểm mã SHA-256 từng file rồi chạy đúng các byte đã kiểm (qua blob:), chỉ khi lỗi
mới lấy từ website. Nhờ vậy website chỉ phát phông chữ và mã dịch (~1,5-3,4 MB mỗi người dùng mới thay vì ~34 MB).

Website cần CSP:
  script-src  'self' 'wasm-unsafe-eval' blob:
  worker-src  'self'
  connect-src 'self' https://openrouter.ai https://cdn.jsdelivr.net https://fastly.jsdelivr.net https://files.pythonhosted.org
Đổi phiên bản Pyodide hay PyMuPDF thì sửa PYODIDE_VER, CORE_SHA256, CORE_BYTES, WHEEL, WHEEL_SHA256 và đường dẫn
PyPI trong web/assets/js/dich-worker.js; script này dừng và báo nếu các mã đó không khớp với file vừa tải.
"""
import hashlib
import re
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "pdf-translation-layout"
WEB = ROOT / "web"
PYODIDE = "0.29.5"
PYMUPDF = "1.28.2"
CORE = ["pyodide.js", "pyodide.asm.js", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json"]


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    site = Path(sys.argv[1]).resolve()
    eng = site / "engine"
    (eng / "pyodide").mkdir(parents=True, exist_ok=True)
    (eng / "fonts").mkdir(exist_ok=True)
    (site / "assets" / "js").mkdir(parents=True, exist_ok=True)

    worker = (WEB / "assets" / "js" / "dich-worker.js").read_text(encoding="utf-8")
    loi = []
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["npm", "pack", f"pyodide@{PYODIDE}", "--silent"], cwd=td, check=True)
        with tarfile.open(next(Path(td).glob("pyodide-*.tgz"))) as t:
            tong = 0
            for name in CORE:
                data = t.extractfile(f"package/{name}").read()
                (eng / "pyodide" / name).write_bytes(data)
                tong += len(data)
                if f'"{name}": "{hashlib.sha256(data).hexdigest()}"' not in worker:
                    loi.append(f"CORE_SHA256 của {name}")
            if f"CORE_BYTES = {tong};" not in worker:
                loi.append(f"CORE_BYTES (đúng là {tong})")
    if f'PYODIDE_VER = "{PYODIDE}"' not in worker:
        loi.append("PYODIDE_VER")
    if loi:
        sys.exit("dich-worker.js chưa khớp gói pyodide@" + PYODIDE + ": sửa " + ", ".join(loi))

    info = json.load(urllib.request.urlopen(f"https://pypi.org/pypi/pymupdf/{PYMUPDF}/json", timeout=60))
    whl = next(u for u in info["urls"] if "emscripten" in u["filename"])
    m = re.search(r'WHEEL_SHA256 = "([0-9a-f]{64})"', worker)
    if not m or m.group(1) != whl["digests"]["sha256"] or whl["filename"] not in worker:
        sys.exit("dich-worker.js chưa khớp phiên bản/SHA-256 của PyPI: sửa PYODIDE_VER, WHEEL, WHEEL_SHA256 và đường dẫn PyPI.")
    if whl["url"].rsplit("/", 1)[0] not in worker:
        sys.exit("Đường dẫn PyPI của wheel trong dich-worker.js đã đổi: " + whl["url"])
    target = eng / whl["filename"]
    if not target.is_file() or target.stat().st_size != whl["size"]:
        urllib.request.urlretrieve(whl["url"], target)

    for f in (SKILL / "assets" / "fonts").iterdir():
        shutil.copy2(f, eng / "fonts" / f.name)
    shutil.copy2(SKILL / "scripts" / "dich_pdf.py", eng / "dich_pdf.py")
    for f in ("web_api.py", "NOTICE.txt"):
        shutil.copy2(WEB / "engine" / f, eng / f)
    shutil.copy2(WEB / "dich.html", site / "dich.html")
    for f in ("dich-app.js", "dich-worker.js"):
        shutil.copy2(WEB / "assets" / "js" / f, site / "assets" / "js" / f)
    total = sum(p.stat().st_size for p in eng.rglob("*") if p.is_file())
    print(f"Xong: {eng} ({total / 1e6:.1f} MB). Nhớ kiểm tra CSP của website (xem đầu file này).")


if __name__ == "__main__":
    main()
