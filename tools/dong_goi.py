#!/usr/bin/env python3
"""Đóng gói bản phát hành từ kho mã này (một nguồn, ba nền tảng).

    python tools/dong_goi.py                  # kiểm tra + đóng gói vào dist/
    python tools/dong_goi.py --wheel <file>   # dùng sẵn file wheel PyMuPDF cho bản ChatGPT

Tạo ra trong dist/:
    pdf-translation-layout.zip              Claude.ai / Claude Desktop: Customize → Skills → Upload a skill
    pdf-translation-layout-chatgpt.zip      Knowledge của GPT dựng sẵn (kèm wheel PyMuPDF vì GPT thường không ra mạng)
    pdf-translation-layout-antigravity.zip  Plugin Antigravity (giải nén rồi: agy plugin install <thư mục>)
    antigravity/pdf-translation-layout/     Thư mục plugin đã giải nén, để thử ngay
    INSTRUCTIONS_GPT.txt, HUONG_DAN_TAO_GPT.md
    SHA256SUMS.txt
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "pdf-translation-layout"
DIST = ROOT / "dist"
WHEEL_PIN = "pymupdf==1.26.0"  # wheel abi3 manylinux2014 x86_64, chạy được trên Python 3.9+
FIXED_TIME = (2026, 11, 1, 0, 0, 0)  # thời điểm cố định để file zip giống nhau giữa các lần đóng gói
BO_QUA = {"__pycache__", ".DS_Store", "Thumbs.db", "dich_pdf_work", "ket_qua"}

loi: list[str] = []
canh_bao: list[str] = []


def frontmatter(md: Path) -> dict:
    raw = md.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        loi.append(f"{md}: có BOM UTF-8")
    s = raw.decode("utf-8-sig")
    m = re.match(r"^---\n(.*?)\n---\n", s, re.S)
    if not m:
        loi.append(f"{md}: thiếu phần đầu YAML (---)")
        return {}
    out = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def kiem_skill(d: Path):
    md = d / "SKILL.md"
    if not md.is_file():
        loi.append(f"{d}: thiếu SKILL.md")
        return
    fm = frontmatter(md)
    name, desc = fm.get("name", ""), fm.get("description", "")
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) or len(name) > 64:
        loi.append(f"SKILL.md: name '{name}' phải là chữ thường-gạch-nối, ≤64 ký tự")
    if name != d.name:
        loi.append(f"SKILL.md: name '{name}' phải trùng tên thư mục '{d.name}'")
    if not (1 <= len(desc) <= 1024):
        loi.append(f"SKILL.md: description dài {len(desc)} ký tự (cần 1–1024)")
    if re.search(r"[<>]", desc):
        loi.append("SKILL.md: description không được chứa < hoặc >")
    for k in fm:
        if k not in {"name", "description", "license", "compatibility", "allowed-tools", "metadata"}:
            canh_bao.append(f"SKILL.md: khóa lạ '{k}' (Claude.ai có thể từ chối)")
    if not (d / "scripts" / "dich_pdf.py").is_file():
        loi.append("thiếu scripts/dich_pdf.py")
    fonts = list((d / "assets" / "fonts").glob("*.ttf"))
    if len(fonts) != 16:
        loi.append(f"assets/fonts: cần 16 file .ttf, đang có {len(fonts)}")


def kiem_plugin(d: Path):
    """Theo tài liệu Antigravity (antigravity.google/docs/build-plugins) — chưa thay được 'agy plugin validate --strict'."""
    pj = d / "plugin.json"
    raw = pj.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        loi.append("plugin.json: có BOM UTF-8")
    try:
        m = json.loads(raw)
    except Exception as e:  # noqa: BLE001
        loi.append(f"plugin.json: JSON lỗi: {e}")
        return
    hop_le = {"$schema", "name", "displayName", "description", "version", "logo", "suggestedPrompts", "author",
              "skills", "disabled", "homepage", "repository", "license", "keywords", "extensions"}
    for k in m:
        if k not in hop_le:
            loi.append(f"plugin.json: khóa '{k}' không có trong lược đồ")
    for k in ("name", "displayName", "description", "version", "logo", "author"):
        if not m.get(k):
            loi.append(f"plugin.json: thiếu '{k}' (Marketplace bắt buộc)")
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", m.get("name", "")):
        loi.append("plugin.json: name phải là chữ thường-gạch-nối")
    if m.get("name") != d.name:
        canh_bao.append(f"plugin.json: name khác tên thư mục '{d.name}'")
    if not re.fullmatch(r"\d+\.\d+\.\d+", m.get("version", "")):
        loi.append("plugin.json: version nên dạng x.y.z")
    n = len(m.get("description", ""))
    if not (120 <= n <= 160):
        canh_bao.append(f"plugin.json: description {n} ký tự (khuyên 120–160)")
    if len(m.get("suggestedPrompts", [])) > 3:
        loi.append("plugin.json: suggestedPrompts tối đa 3")
    a = m.get("author")
    if isinstance(a, dict) and a.get("url") and not a["url"].startswith("https://"):
        loi.append("plugin.json: author.url phải là https://")
    for k in ("homepage", "repository"):
        if m.get(k) and not m[k].startswith("https://"):
            loi.append(f"plugin.json: {k} phải là https://")
    if any(k != k.lower() for k in m.get("keywords", [])):
        loi.append("plugin.json: keywords phải viết thường")
    logo = d / m.get("logo", "")
    if not logo.is_file() or logo.suffix.lower() not in {".svg", ".png", ".jpg", ".jpeg", ".webp"}:
        loi.append(f"plugin.json: không thấy logo {m.get('logo')}")
    elif logo.suffix.lower() == ".svg":
        s = logo.read_text(encoding="utf-8")
        w = re.search(r'\bwidth="(\d+)"', s)
        if not w or int(w.group(1)) < 128:
            canh_bao.append("logo.svg: nên đặt width/height ≥ 128")
    if not (d / "README.md").is_file():
        loi.append("plugin: thiếu README.md (Marketplace bắt buộc)")
    sk = d / "skills"
    for s in sorted(p for p in sk.iterdir() if p.is_dir()):
        kiem_skill(s)


def _bo_qua(p: Path) -> bool:
    return any(part in BO_QUA for part in p.parts) or p.suffix == ".pyc"


def them_thu_muc(z: zipfile.ZipFile, src: Path, arc: str):
    for p in sorted(src.rglob("*")):
        if _bo_qua(p.relative_to(src)):
            continue
        name = f"{arc}/{p.relative_to(src).as_posix()}"
        if p.is_dir():
            zi = zipfile.ZipInfo(name + "/", FIXED_TIME)
            zi.external_attr = (0o40755 << 16) | 0x10
            z.writestr(zi, b"")
        else:
            them_file(z, p, name)


def them_file(z: zipfile.ZipFile, p: Path, name: str):
    zi = zipfile.ZipInfo(name, FIXED_TIME)
    thuc_thi = p.suffix in {".py", ".sh"} and "/scripts/" in f"/{name}"
    zi.external_attr = ((0o100755 if thuc_thi else 0o100644) << 16)
    zi.compress_type = zipfile.ZIP_DEFLATED
    z.writestr(zi, p.read_bytes(), compresslevel=9)


def lay_wheel(chi_dinh: str | None) -> Path:
    if chi_dinh:
        return Path(chi_dinh).resolve()
    cache = ROOT / "tools" / ".wheels"
    found = sorted(cache.glob("pymupdf-1.26.0-*manylinux*x86_64*.whl"))
    if found:
        return found[0]
    cache.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, "-m", "pip", "download", WHEEL_PIN, "--no-deps", "--only-binary=:all:",
                    "--platform", "manylinux2014_x86_64", "--python-version", "3.11", "-d", str(cache)], check=True)
    return sorted(cache.glob("pymupdf-*.whl"))[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wheel", help="File wheel PyMuPDF manylinux x86_64 cho bản ChatGPT")
    ap.add_argument("--khong-chatgpt", action="store_true", help="Bỏ qua bản ChatGPT (không cần wheel)")
    a = ap.parse_args()

    kiem_skill(SKILL)
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()

    # 1) Claude
    with zipfile.ZipFile(DIST / "pdf-translation-layout.zip", "w") as z:
        them_thu_muc(z, SKILL, "pdf-translation-layout")

    # 2) ChatGPT
    if not a.khong_chatgpt:
        whl = lay_wheel(a.wheel)
        with zipfile.ZipFile(DIST / "pdf-translation-layout-chatgpt.zip", "w") as z:
            them_thu_muc(z, SKILL, "pdf-translation-layout")
            them_file(z, whl, f"pdf-translation-layout/assets/wheels/{whl.name}")
        for f in ("INSTRUCTIONS_GPT.txt", "HUONG_DAN_TAO_GPT.md"):
            shutil.copy2(ROOT / "chatgpt" / f, DIST / f)

    # 3) Antigravity: thư mục plugin + zip
    plug = DIST / "antigravity" / "pdf-translation-layout"
    (plug / "assets").mkdir(parents=True)
    shutil.copy2(ROOT / "plugin.json", plug / "plugin.json")
    shutil.copy2(ROOT / "antigravity" / "README.md", plug / "README.md")
    for f in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        shutil.copy2(ROOT / f, plug / f)
    shutil.copy2(ROOT / "assets" / "logo.svg", plug / "assets" / "logo.svg")
    shutil.copytree(SKILL, plug / "skills" / "pdf-translation-layout",
                    ignore=shutil.ignore_patterns(*BO_QUA, "*.pyc"))
    (plug / "skills" / "pdf-translation-layout" / "scripts" / "dich_pdf.py").chmod(0o755)
    kiem_plugin(plug)
    with zipfile.ZipFile(DIST / "pdf-translation-layout-antigravity.zip", "w") as z:
        them_thu_muc(z, plug, "pdf-translation-layout")

    with open(DIST / "SHA256SUMS.txt", "w", encoding="utf-8") as f:
        for p in sorted(DIST.glob("*.zip")):
            f.write(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n")

    for p in sorted(DIST.iterdir()):
        if p.is_file():
            print(f"  {p.name:45s} {p.stat().st_size / 1e6:6.2f} MB")
    for c in canh_bao:
        print("CẢNH BÁO:", c)
    for e in loi:
        print("LỖI:", e)
    print("KẾT QUẢ:", "ĐẠT" if not loi else f"{len(loi)} LỖI")
    return 1 if loi else 0


if __name__ == "__main__":
    sys.exit(main())
