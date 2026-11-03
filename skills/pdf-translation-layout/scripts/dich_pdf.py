#!/usr/bin/env python3
"""
dich_pdf.py — Dịch PDF Anh ⇄ Việt giữ nguyên bố cục, chạy được ngay trong khung chat của trợ lý AI
(Claude.ai, ChatGPT, Antigravity, Claude Code…) hoặc trên máy. Một file duy nhất, chỉ cần PyMuPDF.

Hai chiều: Anh → Việt (en-vi) và Việt → Anh (vi-en). Mặc định công cụ tự nhận chiều theo ngôn ngữ của tài liệu.
Với PDF tiếng Việt, chữ được làm sạch trước khi đưa cho AI: chuyển mã phông cũ TCVN3 (.VnTime…) và VNI,
gắn lại dấu thanh bị tách rời, chuẩn hóa Unicode NFC.

Trợ lý AI của người dùng là người dịch: công cụ này chỉ TÁCH chữ ra, rồi GHÉP bản dịch vào đúng chỗ.
Không gọi API nào, không cần khóa API.

Quy trình (trợ lý AI tự chạy, người dùng không gõ lệnh):
  python dich_pdf.py kiem-tra                         # kiểm tra / tự cài PyMuPDF
  python dich_pdf.py chuan-bi  tai-lieu.pdf --lo 15   # tách đoạn, chia lô 15 trang (thêm --trang 1-10 để dịch vài trang,
                                                      #   --huong vi-en hoặc en-vi để chọn chiều; mặc định tự nhận)
  python dich_pdf.py lay-lo                           # in các đoạn của lô kế tiếp để AI dịch
  python dich_pdf.py nap-lo   ban-dich.json           # nạp bản dịch lô đó (JSON {id: "bản dịch"})
  python dich_pdf.py dung     --che-do tat-ca         # dựng PDF đã dịch + song ngữ
  python dich_pdf.py kiem-dinh                        # phiếu kiểm định chất lượng bản dịch
  python dich_pdf.py tien-do                          # xem đã dịch đến đâu
  python dich_pdf.py cham-diem --goc A.pdf --dich B.pdf   # chấm một PDF dịch bất kỳ (kể cả của công cụ khác)

Giấy phép: mã MIT (Huỳnh Anh Thuận). Khi chạy, công cụ dùng PyMuPDF (AGPL-3.0 hoặc giấy phép thương mại của Artifex).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import glob
import html
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

PHIEN_BAN = "3.2.0"
HERE = Path(__file__).resolve().parent
SKILL_DIR = HERE.parent
FONT_DIR = SKILL_DIR / "assets" / "fonts"
# Phông đủ dấu tiếng Việt, cùng số đo bề ngang với phông phổ biến nên bản dịch chiếm chỗ gần như bản gốc:
# Liberation Serif ≈ Times New Roman, Liberation Sans ≈ Arial/Helvetica, Liberation Mono ≈ Courier New, Carlito ≈ Calibri.
FAMILIES = {
    "serif": "LiberationSerif",
    "sans": "LiberationSans",
    "mono": "LiberationMono",
    "calibri": "Carlito",
}
STYLES = {"regular": "Regular", "bold": "Bold", "italic": "Italic", "bolditalic": "BoldItalic"}
FONT_FILES = {f"{fam}-{st}": f"{base}-{suf}.ttf" for fam, base in FAMILIES.items() for st, suf in STYLES.items()}
CHAN_TRANG = "Bản dịch cá nhân bằng AI · không phân phối · pdf-translation-layout"
# Bản tiếng Anh dễ bị đem nộp như bản dịch chính thức (con dấu, chữ ký dạng ảnh vẫn nằm nguyên trên trang),
# nên chân trang nói rõ đây không phải bản dịch có chứng thực.
CHAN_TRANG_EN = "Unofficial AI translation for reference only · not a certified translation · pdf-translation-layout"
HUONG = {"en-vi": ("en", "vi"), "vi-en": ("vi", "en")}
TEN_NGU = {"en": "tiếng Anh", "vi": "tiếng Việt"}
GIOI_HAN_TAI_VE_MB = 30  # Claude.ai: tối đa 30 MB mỗi file
SAVE_OPTS = dict(garbage=4, deflate=True, deflate_images=True, deflate_fonts=True)  # gộp ảnh/phông trùng lặp

# --------------------------------------------------------------------------------------------
# Môi trường
# --------------------------------------------------------------------------------------------


def _import_pymupdf():
    try:
        import pymupdf  # PyMuPDF >= 1.24.3
        return pymupdf
    except ImportError:
        import fitz  # bản cũ
        return fitz


def cmd_kiem_tra(_a) -> int:
    """Có PyMuPDF thì thôi; chưa có thì tự cài từ PyPI; không có mạng thì cài bản đóng kèm trong assets/wheels."""
    print(f"Python {sys.version.split()[0]} · dich_pdf {PHIEN_BAN}")
    try:
        fz = _import_pymupdf()
        print(f"PyMuPDF {getattr(fz, '__version__', fz.VersionBind)}: có sẵn")
    except ImportError:
        print("Chưa có PyMuPDF → đang tự cài…")
        cmds = [[sys.executable, "-m", "pip", "install", "-q", "pymupdf"],
                [sys.executable, "-m", "pip", "install", "-q", "--user", "pymupdf"],
                [sys.executable, "-m", "pip", "install", "-q", "--break-system-packages", "pymupdf"]]
        wheels = sorted(glob.glob(str(SKILL_DIR / "assets" / "wheels" / "*.whl")))
        for w in wheels:  # dự phòng khi không ra được mạng
            cmds.append([sys.executable, "-m", "pip", "install", "-q", "--no-index", w])
            cmds.append([sys.executable, "-m", "pip", "install", "-q", "--no-index", "--break-system-packages", w])
        ok = False
        for c in cmds:
            r = subprocess.run(c, capture_output=True, text=True)
            if r.returncode == 0:
                ok = True
                break
        if not ok:
            print("KHÔNG CÀI ĐƯỢC PyMuPDF.\n"
                  "→ Trong Claude.ai: Cài đặt > Capabilities: bật 'Code execution and file creation' và quyền truy cập mạng cho gói thư viện.\n"
                  "→ Trên máy: cài Python 3.10+ rồi chạy  pip install pymupdf")
            return 1
        import importlib
        importlib.invalidate_caches()
        fz = _import_pymupdf()
        print(f"Đã cài PyMuPDF {getattr(fz, '__version__', '')}")
    missing = [f for f in FONT_FILES.values() if not (FONT_DIR / f).is_file()]
    if missing:
        print(f"THIẾU PHÔNG CHỮ trong {FONT_DIR}: {missing}")
        return 1
    print("Phông tiếng Việt: đủ")
    print("SẴN SÀNG")
    return 0


# --------------------------------------------------------------------------------------------
# Thư mục làm việc và trạng thái
# --------------------------------------------------------------------------------------------

def _work_root(a) -> Path:
    return Path(getattr(a, "thu_muc", None) or os.environ.get("DICH_PDF_WORK", "dich_pdf_work")).resolve()


def _job_dir(a) -> Path:
    root = _work_root(a)
    cur = root / "hien_tai.txt"
    if getattr(a, "viec", None):
        return root / a.viec
    if not cur.is_file():
        sys.exit("Chưa có tài liệu nào. Chạy:  dich_pdf.py chuan-bi <file.pdf>")
    return root / cur.read_text(encoding="utf-8").strip()


def _load(p: Path, default=None):
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else default


def _save(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(p)


def _out_dir(a) -> Path:
    if getattr(a, "xuat", None):
        d = Path(a.xuat)
    elif Path("/mnt/user-data/outputs").is_dir():
        d = Path("/mnt/user-data/outputs")  # nơi Claude.ai đưa file cho người dùng tải
    else:
        d = Path("ket_qua")
    d.mkdir(parents=True, exist_ok=True)
    return d.resolve()


# --------------------------------------------------------------------------------------------
# Tách đoạn
# --------------------------------------------------------------------------------------------

_LETTER = re.compile(r"[A-Za-z]")
_URLISH = re.compile(r"^\s*(https?://\S+|www\.\S+|\S+@\S+\.\S+)\s*$")
_EN_STOP = set("the and of to in is are for with on that this be as by or from it at an not your you can".split())


def _hexcolor(c: int) -> str:
    return f"#{c:06x}"


# --------------------------------------------------------------------------------------------
# Chữ tiếng Việt trong PDF nguồn: mã phông cũ, dấu thanh tách rời, Unicode
# --------------------------------------------------------------------------------------------
# Bảng chuyển mã TCVN3 (ABC, phông .VnTime, .VnArial…) và VNI (phông VNI-Times…) lấy từ viparse 0.1.31
# (giấy phép MIT, © 2026 minhtridinh, https://github.com/TrizenX/viparse), đã được đối chiếu với văn bản hành chính
# thật. Thêm VNI "aú" → ẳ, "AÚ" → Ẳ: viparse để trống vì chưa gặp trong mẫu; suy ra theo hàng ắ ằ ẵ ặ.
_TCVN3 = str.maketrans(
    "\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xad\xae\xb5\xb8\xb6\xb7\xb9\xbb\xbe\xbc\xbd\xc6\xc7\xca\xc8\xc9"
    "\xcb\xcc\xd0\xce\xcf\xd1\xd2\xd5\xd3\xd4\xd6\xd7\xdd\xd8\xdc\xde\xdf\xe3\xe1\xe2\xe4\xe5\xe8\xe6\xe7\xe9\xea\xed"
    "\xeb\xec\xee\xef\xf3\xf1\xf2\xf4\xf5\xf8\xf6\xf7\xf9\xfa\xfd\xfb\xfc\xfe",
    "ĂÂÊÔƠƯĐăâêôơưđàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ")
_VNI = {p[:-1]: p[-1] for p in (
    "aøà aùá aïạ aûả aáấ aäậ aêă aââ aõã aàầ aåẩ aéắ aüẵ aëặ aèằ aãẫ aúẳ AØÀ AÙÁ AÂÂ AÛẢ AÕÃ AÏẠ AÊĂ AÁẤ AÅẨ AÄẬ "
    "AÀẦ AÃẪ AÉẮ AÈẰ AÜẴ AËẶ AÚẲ eäệ eáế eàề eâê eåể eùé eûẻ eõẽ eãễ eøè eïẹ EÄỆ EÁẾ EÀỀ EÂÊ EÅỂ EØÈ EÙÉ EÏẸ EÛẺ "
    "EÕẼ EÃỄ IØÌ IÙÍ iøì iùí oäộ oâô oáố ôïợ oùó ôøờ ôûở ôùớ oøò oåổ oàồ oïọ oãỗ oûỏ oõõ ôõỡ OÄỘ OÂÔ ÔÛỞ OÅỔ "
    "OÁỐ OØÒ OÙÓ OÀỒ ÔÙỚ ÔØỜ OÕÕ OÏỌ OÛỎ OÃỖ ÔÕỠ ÔÏỢ uûủ öïự uïụ öùứ öûử öøừ uùú öõữ uøù uõũ UÛỦ ÖÙỨ UÕŨ UÏỤ "
    "ÖÛỬ ÖÕỮ ÖÏỰ UØÙ UÙÚ ÖØỪ yùý yõỹ yûỷ yøỳ yïỵ YÙÝ YÛỶ YØỲ YÏỴ YÕỸ ñđ ÑĐ òị æỉ ÒỊ ÆỈ ÓĨ óĩ ôơ ÔƠ öư ÖƯ").split()}
# Ký tự không bao giờ có trong tiếng Việt Unicode đúng nhưng hay gặp khi phông TCVN3/VNI bị trích ra
_SIG_TCVN3 = set("\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xad\xae\xb5\xb6\xb7\xb8\xb9\xbb\xbc\xbd\xbe\xc6\xc7"
                 "\xcb\xce\xcf\xd0\xd1\xd6\xd7\xd8\xdc\xde\xdf\xe4\xe5\xe6\xe7\xeb\xee\xef\xf1\xf6\xf7\xf8\xfb\xfc\xfe")
_SIG_VNI = set("\xc4\xc5\xc6\xcb\xcf\xd1\xd6\xd8\xdb\xdc\xe4\xe5\xe6\xeb\xef\xf1\xf6\xf8\xfb\xfc")
_VI_TONES = {"̀", "́", "̃", "̉", "̣"}
_VI_SYL = re.compile(r"^(ngh|ng|nh|ch|gh|gi|kh|ph|qu|th|tr|[bcdđghklmnprstvx])?[aăâeêioôơuưy]{1,3}(ch|ng|nh|[cmnpt])?$")
_INVISIBLE = dict.fromkeys(map(ord, "​‌‍﻿­"))


def _legacy_of_font(name: str):
    """Phông TCVN3 tên bắt đầu ".Vn" (.VnTime, .VnArialH), phông VNI bắt đầu "VNI" (VNI-Times).
    Trả về (mã, là_phông_chữ_hoa). Phông TCVN3 đuôi H vẽ chữ thường thành chữ hoa."""
    n = re.sub(r"^[A-Z]{6}\+", "", name or "").lower().replace(" ", "")
    base = re.sub(r"(bold|italic|oblique|regular)+$", "", re.split(r"[,\-]", n)[0])
    if n.startswith("vni"):
        return "vni", False
    if n.startswith(".vn") or (n.startswith("vn") and len(n) > 3 and n[2].isalpha()):
        return "tcvn3", base.endswith("h")
    return None, False


def _convert_legacy(text: str, enc: str) -> str:
    if enc == "tcvn3":
        # Khi trích PDF, ư (byte 0xAD) hay ra dấu trừ U+2212 và ã (0xB7) ra U+2219: chỉ đổi khi đứng sát chữ cái
        if "−" in text or "∙" in text:
            text = re.sub(r"(?<=[^\W\d_])[−∙]|[−∙](?=[^\W\d_])",
                          lambda m: {"−": "\xad", "∙": "\xb7"}[m.group(0)], text)
        return text.translate(_TCVN3)
    out, i = [], 0
    while i < len(text):
        two = text[i:i + 2]
        if len(two) == 2 and two in _VNI:
            out.append(_VNI[two])
            i += 2
            continue
        out.append(_VNI.get(text[i], text[i]))
        i += 1
    return "".join(out)


def _strip_tones(w: str) -> str:
    return unicodedata.normalize("NFC", "".join(c for c in unicodedata.normalize("NFD", w) if c not in _VI_TONES))


def _valid_syllable(w: str) -> bool:
    """Âm tiết tiếng Việt hợp lệ: đúng cấu trúc phụ âm đầu + vần, nhiều nhất một dấu thanh, dấu thanh nằm trên nguyên âm
    (và không nằm trên i/u/y khi ngay sau là nguyên âm có mũ, móc, trăng như iê, uô, ươ)."""
    if not _VI_SYL.match(_strip_tones(w)):
        return False
    d = unicodedata.normalize("NFD", w)
    tones, prev = 0, ""
    for i, c in enumerate(d):
        if c in _VI_TONES:
            tones += 1
            if prev not in "aeiouy":
                return False
            if prev in "iuy" and any(x in "\u0302\u031b\u0306" for x in d[i + 1:i + 4]):
                return False
        elif not unicodedata.combining(c):
            prev = c
    return tones <= 1


def _syllable_ratio(text: str) -> float:
    """Tỷ lệ từ có dấu (chữ ngoài bảng ASCII) là âm tiết tiếng Việt hợp lệ. Chữ hỏng mã hiếm khi ghép thành âm tiết đúng."""
    toks = [w for w in re.findall(r"[^\W\d_]+", text.lower()) if any(ord(c) > 127 for c in w)]
    if not toks:
        return 1.0
    return sum(1 for w in toks if _valid_syllable(w)) / len(toks)


def _guess_legacy(text: str):
    """Dò mã cũ theo nội dung (khi tên phông không nói gì): chỉ nhận khi chuyển thử làm chữ thành tiếng Việt hợp lệ."""
    nonascii = [c for c in text if ord(c) > 127]
    if len(nonascii) < 3:
        return None
    for enc, sig in (("tcvn3", _SIG_TCVN3), ("vni", _SIG_VNI)):
        s = sum(c in sig for c in nonascii)
        if s >= 2 and s >= 0.3 * len(nonascii):
            after = _syllable_ratio(unicodedata.normalize("NFC", _convert_legacy(text, enc)))
            if after >= 0.7 and after > _syllable_ratio(text) + 0.2:
                return enc
    return None


class _PageTrace:
    """Vị trí thật của từng ký tự trên trang (get_texttrace), chỉ đọc khi cần sửa dấu rời. Dấu thanh là glyph không
    có bề ngang, nên vị trí hình của dấu lấy từ khung glyph trong phông nhúng; không đọc được phông thì đoán theo
    quy ước phổ biến (dấu đặt ở cuối chữ cái nó thuộc về)."""

    def __init__(self, page):
        self.page, self._chars, self._fonts, self.active = page, None, {}, False

    def _font(self, name):
        if name not in self._fonts:
            self._fonts[name] = None
            try:
                fz = _import_pymupdf()
                norm = lambda x: re.sub(r"[\s\-_,]", "", _font_key(x)).lower()  # noqa: E731
                want = norm(name)
                for f in self.page.get_fonts():
                    have = norm(f[3])
                    if have and want and (have.startswith(want) or want.startswith(have)):
                        buf = self.page.parent.extract_font(f[0])[3]
                        if buf:
                            self._fonts[name] = fz.Font(fontbuffer=buf)
                        break
            except Exception:
                pass
        return self._fonts[name]

    def chars(self):
        if self._chars is None:
            self._chars = []
            try:
                for sp in self.page.get_texttrace():
                    for ch in sp["chars"]:
                        c, ox = chr(ch[0]), ch[2][0]
                        x0, _y0, x1, _y1 = ch[3]
                        cx = (x0 + x1) / 2 if x1 > x0 else None
                        if cx is None and unicodedata.combining(c):
                            f = self._font(sp.get("font", ""))
                            try:
                                gb = f.glyph_bbox(ord(c)) if f else None
                                if gb is not None and gb.x1 > gb.x0:
                                    cx = ox + (gb.x0 + gb.x1) / 2 * sp.get("size", 1)
                            except Exception:
                                pass
                        self._chars.append((c, ox, ch[2][1], cx, x0, x1))
            except Exception:
                pass
        return self._chars


def _fix_marks(text: str, bbox, trace: _PageTrace) -> str:
    """Dấu thanh vẽ thành glyph riêng bị MuPDF dồn về cuối dòng ("tiêng Viêṭ́"). Gắn lại từng dấu vào chữ cái
    nằm ngay dưới nó (so tâm hình của dấu với tâm các chữ cái, theo get_texttrace), rồi chuẩn hoá NFC.
    Không chắc chắn thì trả nguyên văn."""
    x0, y0, x1, y1 = bbox
    chars = [c for c in trace.chars() if x0 - 1 <= c[1] <= x1 + 1 and y0 - 2 <= c[2] <= y1 + 2]
    bases = sorted((c for c in chars if not c[0].isspace() and not unicodedata.combining(c[0])), key=lambda c: c[1])
    marks = [c for c in chars if unicodedata.combining(c[0])]
    plain = [ch for ch in text if not unicodedata.combining(ch)]
    seq = [ch for ch in plain if not ch.isspace()]
    if not marks or len(seq) != len(bases) or sum(a == b[0] for a, b in zip(seq, bases)) < 0.9 * len(seq):
        return unicodedata.normalize("NFC", text)
    def build(pick):
        attach = {}
        for m in marks:
            attach.setdefault(pick(m), []).append(m[0])
        out, k = [], 0
        for ch in plain:
            out.append(ch)
            if not ch.isspace():
                out.extend(attach.get(k, []))
                k += 1
        return unicodedata.normalize("NFC", "".join(out))

    near = lambda key: (lambda m: min(range(len(bases)), key=lambda i: abs(key(bases[i]) - m[1])))  # noqa: E731
    tries = []
    if all(m[3] is not None for m in marks):  # biết vị trí hình của dấu (từ phông nhúng): chữ cái có tâm gần nhất
        tries.append(build(lambda m: min(range(len(bases)), key=lambda i: abs(bases[i][3] - m[3]))))
    # Phông nhúng dạng tập con có thể trả khung glyph sai, nên thử thêm hai quy ước đặt dấu phổ biến
    # (dấu đặt sau chữ cái, hoặc tại gốc chữ cái) rồi chọn bản ra tiếng Việt hợp lệ nhất
    tries += [build(near(lambda c: c[5])), build(near(lambda c: c[4]))]
    ok = [t for t in tries if not any(unicodedata.combining(c) for c in t)]
    if not ok:  # vẫn còn dấu lẻ: không chắc, giữ nguyên
        return unicodedata.normalize("NFC", text)
    return max(ok, key=_syllable_ratio)  # max giữ phương án đứng trước khi bằng điểm


def _font_key(name: str) -> str:
    return re.sub(r"^[A-Z]{6}\+", "", name or "")


def _legacy_fonts(doc) -> dict:
    """Phông nào trong tài liệu thật sự chứa chữ mã cũ. Tên phông .Vn*/VNI* là tín hiệu mạnh, nhưng có PDF dùng phông
    tên cũ mà đã ánh xạ sang Unicode đúng; khi đó chuyển mã sẽ làm hỏng chữ. Nên đếm thêm ký tự đặc trưng của mã cũ."""
    names = {}
    pages = []
    for page in doc:
        hit = False
        for f in page.get_fonts():
            enc, up = _legacy_of_font(f[3])
            if enc:
                names[_font_key(f[3])] = (enc, up)
                hit = True
        if hit:
            pages.append(page)
    if not names:
        return {}
    sig, uni = {}, {}
    for page in pages:
        for b in page.get_text("dict").get("blocks", []):
            for ln in b.get("lines", []):
                for sp in ln.get("spans", []):
                    k = _font_key(sp.get("font", ""))
                    enc, _up = _legacy_of_font(k)
                    if not enc:
                        continue
                    names.setdefault(k, _legacy_of_font(k))
                    t = sp["text"]
                    sig[k] = sig.get(k, 0) + sum(c in (_SIG_TCVN3 if enc == "tcvn3" else _SIG_VNI) for c in t)
                    uni[k] = uni.get(k, 0) + sum(1 for c in t if 0x1EA0 <= ord(c) <= 0x1EF9 or c in "ăĂơƠưƯđĐĩĨũŨ")
    return {k: v for k, v in names.items() if sig.get(k, 0) >= 3 and sig.get(k, 0) > uni.get(k, 0)}


def _clean_line(ln, trace: _PageTrace, stats: dict, fonts: dict) -> str:
    """Chữ của một dòng sau khi: chuyển mã phông cũ theo từng span, chuẩn hoá NFC (không bao giờ NFKC),
    gắn lại dấu rời, bỏ ký tự vô hình."""
    parts, plain_idx = [], []
    for sp in ln["spans"]:
        enc, upper = fonts.get(_font_key(sp.get("font", "")), (None, False))
        t = sp["text"]
        if enc:
            t = _convert_legacy(t, enc)
            t = t.upper() if upper else t
            stats[enc] = stats.get(enc, 0) + 1
        else:
            plain_idx.append(len(parts))
        parts.append(t)
    rest = "".join(parts[i] for i in plain_idx)
    enc = _guess_legacy(rest) if rest else None
    if enc:
        for i in plain_idx:
            parts[i] = _convert_legacy(parts[i], enc)
        stats[enc] = stats.get(enc, 0) + 1
    raw = "".join(parts)
    t = unicodedata.normalize("NFC", raw)
    if trace.active:
        fixed = _fix_marks(raw, ln["bbox"], trace)
        if fixed != t:
            stats["dau_roi"] = stats.get("dau_roi", 0) + 1
            t = fixed
    return t.translate(_INVISIBLE)


def _bad_ratio(text: str) -> float:
    """Tỷ lệ ký tự hỏng: U+FFFD, vùng riêng (PUA), ký tự điều khiển (phông không có bảng ToUnicode)."""
    cs = [c for c in text if not c.isspace()]
    if not cs:
        return 0.0
    bad = sum(1 for c in cs if c == "�" or 0xE000 <= ord(c) <= 0xF8FF or ord(c) < 32)
    return bad / len(cs)


_SERIF = ("times", "tiro", "georgia", "garamond", "cambria", "minion", "palatino", "antiqua", "baskerville", "caslon",
          "libertine", "charter", "century", "bodoni", "didot", "merriweather", "lora", "serif", "nimbusrom", "roman",
          "book", "utopia", "sabon", "janson", "caladea", "tinos", "constantia", "vntime")


def _family_of(span) -> str:
    name = _font_key(span.get("font") or "").lower().replace(" ", "").replace("-", "").lstrip(".")
    flags = span.get("flags", 0)
    if "calibri" in name or "carlito" in name:
        return "calibri"
    if flags & 8 or any(k in name for k in ("courier", "couri", "mono", "consolas", "menlo", "cousine")):
        return "mono"
    if "sans" in name:
        return "sans"
    if flags & 4 or any(k in name for k in _SERIF):
        return "serif"
    return "sans"


def _style_of(span) -> tuple:
    name = (span.get("font") or "").lower()
    flags = span.get("flags", 0)
    bold = bool(flags & 16) or any(k in name for k in ("bold", "black", "heavy", "semibold", "demi"))
    italic = bool(flags & 2) or any(k in name for k in ("italic", "oblique"))
    return bold, italic


_LIGA = str.maketrans({"\ufb00": "ff", "\ufb01": "fi", "\ufb02": "fl", "\ufb03": "ffi", "\ufb04": "ffl", "\ufb05": "st", "\ufb06": "st"})
_LIST_START = re.compile(r"^\s*([•·▪‣◦●○■□➢➤✓✔\-–—*]|\(?\d{1,3}[.)]|\(?[a-zA-Z][.)]|[ivxIVX]{1,4}\.)\s+")


def _split_line(ln):
    """Tách một dòng thành các ô khi giữa các cụm chữ có khoảng trống lớn (bảng biểu, cột số liệu)."""
    spans = sorted([s for s in ln["spans"] if s["text"].strip()], key=lambda s: s["bbox"][0])
    if len(spans) < 2:
        return [ln]
    pieces, cur = [], [spans[0]]
    for sp in spans[1:]:
        gap = sp["bbox"][0] - cur[-1]["bbox"][2]
        if gap > max(6.0, 0.9 * cur[-1]["size"]):
            pieces.append(cur)
            cur = []
        cur.append(sp)
    pieces.append(cur)
    if len(pieces) == 1:
        return [ln]
    out = []
    for sps in pieces:
        bb = [min(s["bbox"][0] for s in sps), min(s["bbox"][1] for s in sps),
              max(s["bbox"][2] for s in sps), max(s["bbox"][3] for s in sps)]
        out.append({"bbox": bb, "spans": sps, "dir": ln.get("dir", (1, 0))})
    return out


def _line_style(ln):
    sp = max(ln["spans"], key=lambda s: len(s["text"].strip()))
    letters = [c for c in "".join(s["text"] for s in ln["spans"]) if c.isalpha()]
    caps = len(letters) >= 4 and all(c.isupper() for c in letters)  # quốc hiệu, tên cơ quan viết hoa
    return (round(sp["size"]), *_style_of(sp), caps)


def _split_paragraphs(lines, split_style=False):
    """Tách một khối thành các đoạn: mỗi mục danh sách, hoặc chỗ có khoảng cách dọc lớn, là một đoạn riêng.
    split_style: dòng đổi kiểu chữ (đậm, nghiêng, cỡ) cũng là đoạn mới, như khối quốc hiệu, tiêu ngữ, ngày tháng
    của văn bản hành chính Việt Nam."""
    groups, cur, prev = [], [], None
    for ln in lines:
        t = "".join(s["text"] for s in ln["spans"])
        if cur and prev is not None:
            h = prev["bbox"][3] - prev["bbox"][1]
            gap = ln["bbox"][1] - prev["bbox"][3]
            if _LIST_START.match(t) or gap > 0.8 * max(h, 1) or (split_style and _line_style(ln) != _line_style(prev)):
                groups.append(cur)
                cur = []
        cur.append(ln)
        prev = ln
    if cur:
        groups.append(cur)
    return groups


def _join_lines(lines_text, keep_hyphen=False):
    """Nối các dòng thành đoạn. Tiếng Anh: bỏ gạch nối cuối dòng khi từ bị ngắt. Tiếng Việt không ngắt âm tiết giữa
    hai dòng, còn gạch nối luôn là thật ("Bà Rịa - Vũng Tàu", "ra-đi-ô"), nên giữ nguyên."""
    out = ""
    for t in lines_text:
        t = t.strip()
        if not t:
            continue
        if not out:
            out = t
        elif not keep_hyphen and out.endswith("-") and t[:1].islower():
            out = out[:-1] + t
        elif out.endswith("/") or (keep_hyphen and out.endswith("-") and not out.endswith(" -")):
            out += t  # đường dẫn, số hiệu văn bản (45/2024/TT-BTC, NĐ-CP) hay từ ghép (ra-đi-ô) bị ngắt dòng: nối liền
        else:
            out += " " + t
    return re.sub(r"\s+", " ", out).strip()


def _should_translate(text: str, src_lang: str = "en") -> bool:
    if len(_LETTER.findall(text)) < 2:
        return False
    if _URLISH.match(text):
        return False
    if re.fullmatch(r"[\W\d_]*(page|trang|p\.)?\s*\d+[\W\d_]*", text.strip(), flags=re.I):
        return False
    if src_lang == "vi" and len(text.split()) >= 4 and _vi_ratio(text) == 0 and _en_ratio(text) >= 0.15:
        return False  # tài liệu tiếng Việt có đoạn đã là tiếng Anh (hợp đồng song ngữ, tóm tắt): giữ nguyên
    return True


def _detect_lang(texts) -> str:
    """vi nếu đủ nhiều từ mang dấu tiếng Việt, ngược lại en."""
    words = [w for t in texts for w in re.findall(r"[^\W\d_]+", t.lower())]
    if not words:
        return "en"
    marked = sum(1 for w in words if any(c in _VI_MARK for c in w))
    return "vi" if marked / len(words) >= 0.12 else "en"


def extract_segments(doc, huong: str = "tu-dong"):
    """Tách đoạn. Trả về (pages, huong, info): huong là "en-vi" hoặc "vi-en" (tự nhận nếu "tu-dong"),
    info ghi lại việc làm sạch chữ tiếng Việt (số dòng đã chuyển mã, đã gắn lại dấu, trang chữ hỏng)."""
    fz = _import_pymupdf()
    fonts = _legacy_fonts(doc)
    stats = {}
    pages = []
    # Chiều dịch: theo yêu cầu, hoặc theo ngôn ngữ của tài liệu (phông mã cũ tiếng Việt là dấu hiệu chắc chắn)
    if huong not in HUONG:
        sample = [unicodedata.normalize("NFC", doc[i].get_text()) for i in range(min(doc.page_count, 20))]
        huong = "vi-en" if fonts or _detect_lang(sample) == "vi" else "en-vi"
    src_lang = HUONG[huong][0]
    for page in doc:
        d = page.get_text("dict", flags=fz.TEXTFLAGS_DICT & ~fz.TEXT_PRESERVE_IMAGES)
        trace = _PageTrace(page)
        # Trang có dấu thanh vẽ rời (sau NFC vẫn còn dấu tổ hợp đứng lẻ): sửa theo vị trí thật của từng glyph.
        # Tuỳ bản PyMuPDF, các dấu đó bị dồn về cuối dòng hoặc bị tách thành dòng riêng.
        trace.active = src_lang == "vi" and any(
            unicodedata.combining(c) for c in unicodedata.normalize("NFC", page.get_text()))
        segs = []
        groups = []
        for b in d.get("blocks", []):
            if b.get("type", 0) != 0:
                continue
            lines = [ln for ln in b.get("lines", []) if "".join(s["text"] for s in ln["spans"]).strip()]
            if not lines:
                continue
            pieces = [_split_line(ln) for ln in lines]
            side_by_side = any(
                min(l1["bbox"][3], l2["bbox"][3]) - max(l1["bbox"][1], l2["bbox"][1])
                > 0.5 * min(l1["bbox"][3] - l1["bbox"][1], l2["bbox"][3] - l2["bbox"][1])
                and (l2["bbox"][0] >= l1["bbox"][2] - 1 or l1["bbox"][0] >= l2["bbox"][2] - 1)
                for i, l1 in enumerate(lines) for l2 in lines[i + 1:i + 8])
            if side_by_side or any(len(pc) > 1 for pc in pieces):  # khối dạng bảng: mỗi ô là một đoạn
                for pc in pieces:
                    groups.extend([[x] for x in pc])
            else:
                groups.extend(_split_paragraphs(lines, split_style=(src_lang == "vi")))
        for lines in groups:
            # chữ xoay dọc: giữ nguyên
            rotated = any(abs(ln.get("dir", (1, 0))[1]) > 0.1 for ln in lines)
            texts, lrects, chars = [], [], {}
            for ln in lines:
                texts.append(_clean_line(ln, trace, stats, fonts))
                lrects.append([round(v, 2) for v in ln["bbox"]])
                for s in ln["spans"]:
                    n = len(s["text"].strip())
                    if not n:
                        continue
                    key = (round(s["size"], 1), s["color"], *_style_of(s), _family_of(s))
                    chars[key] = chars.get(key, 0) + n
            if not chars:
                continue
            (size, color, bold, italic, family), _n = max(chars.items(), key=lambda kv: kv[1])
            bx = [round(min(r[0] for r in lrects), 2), round(min(r[1] for r in lrects), 2),
                  round(max(r[2] for r in lrects), 2), round(max(r[3] for r in lrects), 2)]
            # căn lề
            x0s = [r[0] for r in lrects]
            x1s = [r[2] for r in lrects]
            cx = [(r[0] + r[2]) / 2 for r in lrects]
            bc = (bx[0] + bx[2]) / 2
            align = "left"
            if len(lrects) >= 1 and all(abs(c - bc) < 2.5 for c in cx) and max(x0s) - min(x0s) > 3:
                align = "center"
            elif len(lrects) >= 3 and sum(abs(x - bx[2]) < 2.5 for x in x1s[:-1]) >= 0.8 * (len(x1s) - 1):
                align = "justify"
            if len(lrects) > 1:
                spacing = (lrects[-1][1] - lrects[0][1]) / (len(lrects) - 1)
                lh = max(1.0, min(1.6, spacing / max(size, 1)))
            else:
                lh = 1.2
            segs.append({
                "id": f"p{page.number + 1}-{len(segs) + 1}",
                "page": page.number + 1,
                "_lt": texts,
                "_rot": rotated,
                "rect": bx,
                "lines": lrects,
                "size": size,
                "color": _hexcolor(color),
                "bold": bold,
                "italic": italic,
                "family": family,
                "align": align,
                "line_height": round(lh, 2),
            })
        img_rects = []
        for img in page.get_images(full=True):
            try:
                for r in page.get_image_rects(img[0]):
                    img_rects.append([round(v, 2) for v in r])
            except Exception:
                pass
        pages.append({"page": page.number + 1, "width": page.rect.width, "height": page.rect.height,
                      "segments": segs, "images": img_rects, "links": len(page.get_links())})
    loi_chu = []
    for p in pages:
        sizes = []
        for s in p["segments"]:
            s["text"] = _join_lines(s.pop("_lt"), keep_hyphen=(src_lang == "vi")).translate(_LIGA)
            s["translate"] = (not s.pop("_rot")) and _should_translate(s["text"], src_lang)
            sizes.append(s["size"])
        if sizes:
            med = sorted(sizes)[len(sizes) // 2]
            for s in p["segments"]:
                s["kind"] = "tieu-de" if (s["size"] >= med * 1.25 or (s["bold"] and len(s["text"].split()) <= 12)) else "doan"
        page_text = " ".join(s["text"] for s in p["segments"])
        p["chars"] = len(page_text)
        # Trang chữ hỏng (phông không có bảng ToUnicode, mã lạ): không đưa cho AI để tránh dịch bịa
        toks_vi = [w for w in re.findall(r"[^\W\d_]+", page_text) if any(ord(c) > 127 for c in w)]
        hong = _bad_ratio(page_text) > 0.1 or (src_lang == "vi" and len(toks_vi) >= 20 and _syllable_ratio(page_text) < 0.5)
        if hong and p["chars"] >= 40:
            loi_chu.append(p["page"])
            for s in p["segments"]:
                s["translate"] = False
    info = {"chuyen_ma": {k: v for k, v in stats.items() if k in ("tcvn3", "vni")},
            "dau_roi": stats.get("dau_roi", 0), "trang_loi_chu": loi_chu,
            "phong_ma_cu": sorted(fonts)}
    return pages, huong, info


def cmd_chuan_bi(a) -> int:
    fz = _import_pymupdf()
    src = Path(a.pdf).resolve()
    if not src.is_file():
        sys.exit(f"Không thấy file: {src}")
    doc = fz.open(src)
    if doc.needs_pass:
        sys.exit("PDF có mật khẩu. Hãy mở khóa trước rồi gửi lại.")
    ten = src.name
    if getattr(a, "trang", None):  # chỉ dịch một số trang, vd "1-10,15"
        chon = _parse_pages(a.trang, doc.page_count)
        if not chon:
            sys.exit(f"Khoảng trang '{a.trang}' không hợp lệ (tài liệu có {doc.page_count} trang).")
        doc.select(chon)
        ten = f"{src.stem}_trang-{a.trang.replace(',', '_').replace(' ', '')}{src.suffix}"
    pages, huong, info = extract_segments(doc, getattr(a, "huong", None) or "tu-dong")
    root = _work_root(a)
    name = re.sub(r"[^\w\-]+", "_", Path(ten).stem, flags=re.UNICODE)[:60] or "tai_lieu"
    if huong == "vi-en":
        name += "_vi-en"  # cùng tài liệu dịch hai chiều thì hai việc riêng
    job = root / name
    if job.exists() and not a.lam_lai and (job / "meta.json").is_file():
        print(f"Đã có việc dang dở cho '{src.name}'. Dùng tiếp (thêm --lam-lai để làm lại từ đầu).")
        (root / "hien_tai.txt").write_text(name, encoding="utf-8")
        return cmd_tien_do(a)
    if job.exists():
        shutil.rmtree(job)
    job.mkdir(parents=True)
    if ten != src.name:
        doc.save(job / "goc.pdf", garbage=3, deflate=True)
    else:
        shutil.copy2(src, job / "goc.pdf")
    segs_all = [s for p in pages for s in p["segments"]]
    scanned = [p["page"] for p in pages if p["chars"] < 20 and p["images"]]
    n = doc.page_count
    lo = max(1, a.lo)
    batches = []
    for start in range(1, n + 1, lo):
        end = min(n, start + lo - 1)
        ids = [s["id"] for s in segs_all if start <= s["page"] <= end and s["translate"]]
        if ids:
            batches.append({"lo": len(batches) + 1, "trang": [start, end], "ids": ids, "xong": False})
    meta = {"ten": ten, "so_trang": n, "lo_trang": lo, "tao_luc": _dt.datetime.now().isoformat(timespec="seconds"),
            "phien_ban": PHIEN_BAN, "trang_scan": scanned, "huong": huong, "lam_sach": info}
    _save(job / "meta.json", meta)
    _save(job / "trang.json", pages)
    _save(job / "lo.json", batches)
    _save(job / "ban_dich.json", {})
    (root / "hien_tai.txt").write_text(name, encoding="utf-8")
    n_tr = sum(len(b["ids"]) for b in batches)
    words = sum(len(s["text"].split()) for s in segs_all if s["translate"])
    src_l, tgt_l = HUONG[huong]
    tu_nhan = "" if getattr(a, "huong", None) in HUONG else " (tự nhận theo tài liệu; đổi bằng --huong en-vi hoặc vi-en)"
    print(f"Tài liệu: {ten} · {n} trang · {n_tr} đoạn cần dịch (~{words} từ) · {len(batches)} lô × {lo} trang")
    print(f"Chiều dịch: {TEN_NGU[src_l]} → {TEN_NGU[tgt_l]}{tu_nhan}")
    if info["chuyen_ma"]:
        print("Đã chuyển mã phông tiếng Việt cũ sang Unicode: "
              + ", ".join(f"{k.upper()} {v} dòng" for k, v in info["chuyen_ma"].items())
              + (f" (phông {', '.join(info['phong_ma_cu'][:4])})" if info["phong_ma_cu"] else ""))
    if info["dau_roi"]:
        print(f"Đã gắn lại dấu thanh bị tách rời ở {info['dau_roi']} dòng.")
    if info["trang_loi_chu"]:
        tl = info["trang_loi_chu"]
        print(f"CẢNH BÁO: {len(tl)} trang trích ra chữ bị hỏng mã (phông không có bảng Unicode): {tl[:15]}"
              f"{'…' if len(tl) > 15 else ''}. Các trang này giữ nguyên, không đưa cho AI để tránh dịch sai.")
    if scanned:
        print(f"CẢNH BÁO: {len(scanned)} trang có vẻ là ảnh scan (không có lớp chữ): {scanned[:15]}"
              f"{'…' if len(scanned) > 15 else ''}. Công cụ này chỉ dịch PDF có chữ thật; trang scan sẽ giữ nguyên.")
    if n_tr == 0:
        print("Không tìm thấy chữ nào để dịch. PDF có thể là bản scan.")
        return 1
    print("Tiếp theo: dich_pdf.py lay-lo")
    return 0


def _parse_pages(spec: str, n: int) -> list:
    out = []
    for part in re.split(r"[,;]\s*", spec.strip()):
        m = re.fullmatch(r"(\d+)\s*[-–]\s*(\d+)|(\d+)", part.strip())
        if not m:
            return []
        a_, b_ = (int(m.group(1)), int(m.group(2))) if m.group(1) else (int(m.group(3)), int(m.group(3)))
        out.extend(range(max(1, a_), min(n, b_) + 1))
    return sorted(set(i - 1 for i in out))


# --------------------------------------------------------------------------------------------
# Lô dịch
# --------------------------------------------------------------------------------------------

# Quy tắc dịch, dùng chung cho dòng lệnh, trang web và chỉ dẫn GPT
QUY_TAC = {
    "en-vi": "\n".join([
        "Dịch các đoạn tiếng Anh dưới đây sang tiếng Việt cho một tài liệu PDF.",
        "Yêu cầu:",
        "- Tiếng Việt tự nhiên, đủ dấu, đúng văn phong của tài liệu.",
        "- Giữ nguyên số liệu, đơn vị, tên riêng, URL, email, mã, công thức.",
        "- Thuật ngữ thống nhất với các lô trước trong cuộc trò chuyện này.",
        "- Mục danh sách giữ ký hiệu đầu dòng (•, 1., a)…). Đoạn có \"loai\": \"tieu-de\" là tiêu đề: dịch ngắn gọn.",
        "- Ô bảng và nhãn ngắn: dịch thật ngắn để vừa chỗ.",
        "- Không gộp, không tách, không bỏ đoạn nào; không thêm chú thích hay giải thích."]),
    "vi-en": "\n".join([
        "Translate the Vietnamese segments below into English for a PDF document. "
        "The English will be placed back into the original page layout.",
        "Rules:",
        "- Natural, idiomatic English in the register of the document (formal for legal and administrative text). "
        "Translate the meaning, not word for word; render idioms by their meaning.",
        "- Keep numbers, units, codes, URLs, e-mails, formulas and placeholders. Every number in the source must appear "
        "in the translation. Switch separators to English style without changing values (1.000.000 -> 1,000,000; "
        "3,5% -> 3.5%; 1.000.000 đồng -> VND 1,000,000).",
        "- Dates: never swap day and month. Keep numeric dates as written (03/02/2020); "
        "\"ngày 3 tháng 2 năm 2020\" -> \"3 February 2020\".",
        "- Keep legal document numbers exactly (15/2020/NĐ-CP). Luật = Law, Bộ luật = Code, Nghị định = Decree, "
        "Thông tư = Circular, Quyết định = Decision, Nghị quyết = Resolution, Chỉ thị = Directive, "
        "Công văn = Official Letter, Điều = Article, Khoản = Clause, Điểm = Point, Chương = Chapter, Phụ lục = Appendix.",
        "- Official names (Circular 05/2026/TT-BNG): Cộng hòa xã hội chủ nghĩa Việt Nam = Socialist Republic of Viet Nam; "
        "Độc lập - Tự do - Hạnh phúc = Independence - Freedom - Happiness; Chính phủ = Government; Bộ = Ministry; "
        "Ủy ban nhân dân = People's Committee; Hội đồng nhân dân = People's Council; Sở = Department; Phòng = Division. "
        "Translate administrative units as the source names them; never update an older document to the post-2025 map.",
        "- Person names: family name first, without diacritics (Nguyễn Văn An -> Nguyen Van An). Places: name without "
        "diacritics + type (Ho Chi Minh City, Nghe An Province, Ba Dinh District). Ông = Mr., Bà = Ms., GS. = Prof., "
        "PGS. = Assoc. Prof., TS. = Dr., ThS. = MSc/MA. Công ty Cổ phần X = X Joint Stock Company; Công ty TNHH X = X Co., Ltd.",
        "- Pronouns and kinship terms (anh, chị, em, chúng tôi…): resolve to I/you/he/she/we/they from context; if the "
        "gender is unknown use \"they\". Missing subjects: imperative for instructions, \"we\" for an organisation, passive "
        "for rules. Tense from đã/đang/sẽ and context. In legal text phải = shall, được = may, không được = shall not.",
        "- Keep list markers (•, 1., a), -) and ALL-CAPS. A segment with \"loai\": \"tieu-de\" is a heading: keep it "
        "short. Table cells and labels: as short as possible so they fit the box.",
        "- Text that is already English, codes or numbers: return unchanged.",
        "- Use the same English term for the same Vietnamese term in every batch of this document.",
        "- Do not merge, split or skip segments. No notes, explanations or alternatives."]),
}
DONG_KET = {
    "en-vi": 'Chỉ trả về MỘT khối JSON dạng {{"<id>": "<bản dịch>", ...}} với đủ {n} id dưới đây.',
    "vi-en": 'Return ONE JSON object {{"<id>": "<English translation>", ...}} with exactly these {n} ids, '
             'in one ```json block, and nothing else.',
}


def _huong(job: Path) -> str:
    return (_load(job / "meta.json", {}) or {}).get("huong", "en-vi")


def _seg_index(job: Path):
    return {s["id"]: s for p in _load(job / "trang.json") for s in p["segments"]}


def _propagate(trans: dict, idx: dict) -> int:
    """Đoạn trùng chữ (đầu trang, chân trang, tiêu đề lặp lại) dùng chung một bản dịch: AI không phải dịch lại."""
    by_text = {}
    for k, v in trans.items():
        if v and k in idx:
            by_text.setdefault(idx[k]["text"], v)
    n = 0
    for k, s in idx.items():
        if s["translate"] and not trans.get(k) and s["text"] in by_text:
            trans[k] = by_text[s["text"]]
            n += 1
    return n


def cmd_lay_lo(a) -> int:
    job = _job_dir(a)
    batches = _load(job / "lo.json")
    trans = _load(job / "ban_dich.json", {})
    idx = _seg_index(job)
    if a.lo:
        b = next((x for x in batches if x["lo"] == a.lo), None)
    else:
        b = next((x for x in batches if not x["xong"]), None)
    if not b:
        print("TẤT CẢ CÁC LÔ ĐÃ DỊCH XONG. Tiếp theo: dich_pdf.py dung --che-do tat-ca")
        return 0
    if _propagate(trans, idx):
        _save(job / "ban_dich.json", trans)
    todo, seen = [], set()
    for i in b["ids"]:
        if (not a.lo and trans.get(i)) or idx[i]["text"] in seen:
            continue
        seen.add(idx[i]["text"])
        todo.append(i)
    if not todo:
        b["xong"] = True
        _save(job / "lo.json", batches)
        print(f"Lô {b['lo']} đã đủ bản dịch (đoạn lặp lại được điền tự động).")
        return cmd_lay_lo(a)
    items, used = [], 0
    for i in todo:  # mỗi lần in tối đa ~12.000 ký tự để vừa một lượt dịch; phần còn lại lấy ở lần gọi sau
        if items and used + len(idx[i]["text"]) > a.toi_da:
            break
        items.append({"id": i, "text": idx[i]["text"], **({"loai": "tieu-de"} if idx[i].get("kind") == "tieu-de" else {})})
        used += len(idx[i]["text"])
    con_lai = len(todo) - len(items)
    (job / f"lo_{b['lo']:03d}_nguon.json").write_text(json.dumps(items, ensure_ascii=False, indent=0), encoding="utf-8")
    total = len(batches)
    print(f"LÔ {b['lo']}/{total} · trang {b['trang'][0]}–{b['trang'][1]} · {len(items)} đoạn"
          + (f" (lô này còn {con_lai} đoạn nữa, lấy ở lần gọi lay-lo sau)" if con_lai else ""))
    if _huong(job) == "vi-en":
        print("CHIỀU VIỆT → ANH. " + QUY_TAC["vi-en"])
        print('Return JSON {"<id>": "<English>", ...} with EVERY id below, then run: dich_pdf.py nap-lo <file.json>')
    else:
        print("Dịch sang tiếng Việt có dấu đầy đủ, giữ nguyên số liệu, tên riêng, URL, email; không gộp hay tách đoạn.")
        print('Trả về JSON dạng {"<id>": "<bản dịch>", ...} với ĐỦ mọi id dưới đây, rồi chạy: dich_pdf.py nap-lo <file.json>')
    print("---BẮT ĐẦU---")
    for it in items:
        print(json.dumps(it, ensure_ascii=False))
    print("---HẾT---")
    return 0


_VI_MARK = set("àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ")


def _vi_ratio(text: str) -> float:
    words = re.findall(r"[^\W\d_]+", text.lower())
    if not words:
        return 1.0
    return sum(1 for w in words if any(c in _VI_MARK for c in w)) / len(words)


def _en_ratio(text: str) -> float:
    words = re.findall(r"[a-z]+", text.lower())
    if not words:
        return 0.0
    return sum(1 for w in words if w in _EN_STOP) / len(words)


def _check_translation(src: str, vi: str, huong: str = "en-vi") -> str | None:
    if huong == "vi-en":
        return _check_en(src, vi)
    if not vi or not vi.strip():
        return "trống"
    n = len(re.findall(r"[^\W\d_]+", vi))
    if n >= 6 and _en_ratio(vi) > 0.12:
        return "có vẻ chưa dịch (còn tiếng Anh)"
    if n >= 6 and _vi_ratio(vi) < 0.08:
        return "có vẻ thiếu dấu tiếng Việt"
    nums_src = sorted(re.findall(r"\d+(?:[.,]\d+)?", src))
    nums_vi = sorted(re.findall(r"\d+(?:[.,]\d+)?", vi))
    if len(nums_src) >= 2 and not set(x.replace(",", ".") for x in nums_src) <= set(x.replace(",", ".") for x in nums_vi) | {
            x.replace(".", ",") for x in nums_vi} | {x.replace(",", "") for x in nums_vi}:
        return "số liệu có thể bị thay đổi"
    return None


# ---- Kiểm tra bản tiếng Anh (chiều Việt → Anh) ----
_VI_ONLY = re.compile(r"[ăâđêôơưĂÂĐÊÔƠƯ\u0300-\u036f\u1ea0-\u1ef9ìíỉĩịÌÍỈĨỊùúủũụÙÚỦŨỤỳýỷỹỵỲÝỶỸỴàáảãạÀÁẢÃẠèéẻẽẹÈÉẺẼẸòóỏõọÒÓỎÕỌ]")
_VI_NODIA = set("cua cac nhung duoc khong trong voi nay mot nguoi theo cung nhu neu thi hoac bang phai viec ngay "
                "thang nhieu chung toi tren duoi giua truoc dong thuc hien quy dinh nhan dan".split())
_MASK = re.compile(r"\S*\d\S*/\S*|\b[A-ZĐ][A-ZĐ\-]*Đ[A-ZĐ\-]*\b|https?://\S+|www\.\S+|\S+@\S+\.\w+")
_MONTHS = {m: str(i + 1) for i, m in enumerate("january february march april may june july august september october "
                                               "november december".split())}
_MONTHS.update({m[:3]: v for m, v in list(_MONTHS.items())})
_CHATTER = re.compile(r"^\s*(here is|here's|here are|translation\s*:|note\s*:|sure[,!]|certainly|below is)", re.I)


def _digits(t: str, months: bool = False) -> list:
    if months:  # chỉ bản tiếng Anh: "3 February 2020" ↔ 03/02/2020
        t = re.sub(r"\b(" + "|".join(_MONTHS) + r")\b\.?", lambda m: " " + _MONTHS[m.group(1).lower()] + " ", t, flags=re.I)
    return [re.sub(r"[.,]", "", x).lstrip("0") or "0" for x in re.findall(r"\d(?:[\d.,]*\d)?", t)]


def _vi_words_left(en: str) -> int:
    """Số từ tiếng Việt còn sót trong bản tiếng Anh (đã bỏ qua số hiệu văn bản như NĐ-CP, URL, email)."""
    t = _MASK.sub(" ", unicodedata.normalize("NFC", en))
    return sum(1 for w in re.findall(r"[^\W\d_]+", t) if _VI_ONLY.search(w))


def _check_en(src: str, en: str) -> str | None:
    if not en or not en.strip():
        return "trống"
    src_n, en_n = unicodedata.normalize("NFC", src), unicodedata.normalize("NFC", en)
    norm = lambda x: re.sub(r"[\W_]+", " ", x.casefold()).strip()  # noqa: E731
    if norm(src_n) == norm(en_n) and _VI_ONLY.search(src_n):
        return "chưa dịch (còn nguyên tiếng Việt)"
    if _CHATTER.match(en_n):
        return "AI chèn lời dẫn vào bản dịch"
    words = re.findall(r"[^\W\d_]+", _MASK.sub(" ", en_n))
    left = _vi_words_left(en_n)
    if left >= 2 or (left and left >= 0.2 * max(len(words), 1)):
        return "còn chữ tiếng Việt"
    nodia = {w.lower() for w in words if w.lower() in _VI_NODIA}
    if len(nodia) >= 2 and sum(1 for w in words if w.lower() in _VI_NODIA) >= 0.15 * len(words):
        return "còn tiếng Việt không dấu"
    for m in re.finditer(r"https?://\S+|www\.\S+|\S+@\S+\.\w+|\b\d+[\w\-]*/(?:\d{4}/)?[A-ZĐ][A-ZĐ0-9\-]*", src_n):
        code = m.group(0).rstrip(".,;:)")
        if code not in en_n and code.replace("Đ", "D") not in en_n:
            return "mất số hiệu văn bản, URL hoặc email"
    for m in re.finditer(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", src_n):
        d, mo, y = int(m.group(1)), int(m.group(2)), m.group(3)
        if d != mo and d <= 12 and mo <= 12:
            swapped = re.search(rf"\b0?{mo}/0?{d}/{y}\b", en_n)
            kept = re.search(rf"\b0?{d}/0?{mo}/{y}\b", en_n)
            if swapped and not kept:
                return "ngày và tháng có thể bị đảo"
    ds, de = _digits(src_n), _digits(en_n, months=True)
    if ds and set(ds) - set(de):
        return "số liệu có thể bị thay đổi"
    if len(src_n) >= 20:
        r = len(en_n) / len(src_n)
        if r < 0.35 or r > 2.5:
            return "độ dài bất thường (có thể sót hoặc thêm nội dung)"
    return None


def cmd_nap_lo(a) -> int:
    job = _job_dir(a)
    raw = Path(a.file).read_text(encoding="utf-8") if Path(a.file).is_file() else a.file
    raw = raw.strip()
    m = re.search(r"\{.*\}|\[.*\]", raw, flags=re.S)
    if not m:
        sys.exit("Không đọc được JSON bản dịch.")
    data = json.loads(m.group(0))
    if isinstance(data, list):
        data = {d["id"]: d.get("vi") or d.get("en") or d.get("dich") or d.get("text") for d in data}
    data = {k: unicodedata.normalize("NFC", str(v)) for k, v in data.items() if v is not None}
    batches = _load(job / "lo.json")
    trans = _load(job / "ban_dich.json", {})
    idx = _seg_index(job)
    unknown = [k for k in data if k not in idx]
    trans.update({k: v for k, v in data.items() if k in idx})
    auto = _propagate(trans, idx)
    _save(job / "ban_dich.json", trans)
    warn = {}
    huong = _huong(job)
    for k in data:
        if k in idx:
            w = _check_translation(idx[k]["text"], data[k], huong)
            if w:
                warn[k] = w
    changed = []
    for b in batches:
        missing = [i for i in b["ids"] if not trans.get(i)]
        if not missing and not b["xong"]:
            b["xong"] = True
            changed.append(b["lo"])
    _save(job / "lo.json", batches)
    print(f"Đã nạp {len(data) - len(unknown)} đoạn" + (f" (+{auto} đoạn lặp lại điền tự động)." if auto else "."))
    if unknown:
        print(f"Bỏ qua {len(unknown)} id lạ: {unknown[:8]}")
    if warn:
        print(f"CẦN XEM LẠI {len(warn)} đoạn:")
        for k, w in list(warn.items())[:20]:
            print(f"  {k}: {w}")
    if changed:
        print(f"Hoàn tất lô: {changed}")
    pending = [b for b in batches if not b["xong"]]
    cur = next(iter(pending), None)
    if cur:
        miss = [i for i in cur["ids"] if not trans.get(i)]
        print(f"Còn {len(pending)} lô. Lô {cur['lo']} còn thiếu {len(miss)} đoạn. Tiếp theo: dich_pdf.py lay-lo")
    else:
        print("ĐÃ DỊCH ĐỦ. Tiếp theo: dich_pdf.py dung --che-do tat-ca")
    return 0


def cmd_tien_do(a) -> int:
    job = _job_dir(a)
    meta = _load(job / "meta.json")
    batches = _load(job / "lo.json")
    trans = _load(job / "ban_dich.json", {})
    total = sum(len(b["ids"]) for b in batches)
    done = sum(1 for b in batches for i in b["ids"] if trans.get(i))
    print(f"{meta['ten']} · {meta['so_trang']} trang · đã dịch {done}/{total} đoạn "
          f"({100 * done // max(total, 1)}%) · lô xong {sum(b['xong'] for b in batches)}/{len(batches)}")
    nxt = next((b for b in batches if not b["xong"]), None)
    print("Tiếp theo: " + ("dich_pdf.py lay-lo" if nxt else "dich_pdf.py dung --che-do tat-ca"))
    return 0


# --------------------------------------------------------------------------------------------
# Dựng PDF
# --------------------------------------------------------------------------------------------

def _css():
    out = []
    for fam in FAMILIES:
        out.append("@font-face {font-family: vn%s; src: url(%s);}" % (fam, FONT_FILES[f"{fam}-regular"]))
        out.append("@font-face {font-family: vn%s; src: url(%s); font-weight: bold;}" % (fam, FONT_FILES[f"{fam}-bold"]))
        out.append("@font-face {font-family: vn%s; src: url(%s); font-style: italic;}" % (fam, FONT_FILES[f"{fam}-italic"]))
        out.append("@font-face {font-family: vn%s; src: url(%s); font-weight: bold; font-style: italic;}"
                   % (fam, FONT_FILES[f"{fam}-bolditalic"]))
    out.append("* {font-family: vnsans;} body, p, div, h1, h2, h3, ul, ol, li {margin: 0; padding: 0;}")
    return "".join(out)


def _html_for(seg, text, color=None, align=None):
    style = [f"font-family:vn{seg.get('family', 'sans')}", f"font-size:{seg['size']:.2f}pt",
             f"color:{color or seg['color']}", f"line-height:{seg['line_height']}",
             f"text-align:{align or seg['align']}", "margin:0"]
    if seg["bold"]:
        style.append("font-weight:bold")
    if seg["italic"]:
        style.append("font-style:italic")
    return f'<p style="{";".join(style)}">{html.escape(text)}</p>'


def _free_rect(seg, page_info, others):
    """Khung được phép dùng cho bản dịch (thường dài hơn bản gốc 15–30%):
    nới sang phải tới đoạn/ảnh bên cạnh hoặc mép phải vùng chữ của trang, rồi nới xuống tới vật cản phía dưới."""
    x0, y0, x1, y1 = seg["rect"]
    text_right = max([r[2] for r in page_info.get("_text_rects", [])] + [x1])
    right = max(text_right, x1)
    if seg["align"] == "center":
        right = x1  # căn giữa: nới đều hai bên, tính ở dưới
    band_bottom = max(y1, y0 + (y1 - y0) * 1.6)
    for r in others:
        rx0, ry0, rx1, ry1 = r
        if rx0 >= x1 - 1 and min(band_bottom, ry1) - max(y0, ry0) > 0:
            gap = rx0 - x1
            right = min(right, x1 + max(0.0, gap - max(6.0, 0.6 * gap)))  # giữ lại phần lớn khe giữa các cột
    right = max(right, x1)
    left = x0
    if seg["align"] == "center":
        half = min(x0 - 18, page_info["width"] - 18 - x1)
        for r in others:
            rx0, ry0, rx1, ry1 = r
            if min(y1, ry1) - max(y0, ry0) > 0.3 * (y1 - y0):
                if rx1 <= x0 + 1:  # chia đôi khe với khối bên cạnh: hai khối căn giữa cạnh nhau không lấn vào nhau
                    half = min(half, (x0 - rx1) / 2 - 1.5)
                if rx0 >= x1 - 1:
                    half = min(half, (rx0 - x1) / 2 - 1.5)
        half = max(half, 0)
        left, right = x0 - half, x1 + half
    bottom = page_info["height"] - 18
    for r in others:
        rx0, ry0, rx1, ry1 = r
        if ry0 >= y1 - 1 and min(right, rx1) - max(left, rx0) > 2:
            bottom = min(bottom, ry0 - 1.5)
    return left, y0, right, max(bottom, y1)


def build_translated(job: Path, out_pdf: Path, footer=True):
    fz = _import_pymupdf()
    pages = _load(job / "trang.json")
    trans = _load(job / "ban_dich.json", {})
    huong = _huong(job)
    doc = fz.open(job / "goc.pdf")
    arch = fz.Archive(str(FONT_DIR))
    css = _css()
    log = {}
    # Chụp lại mọi liên kết trước khi sửa trang: lệnh xóa chữ làm mất liên kết nằm đè lên chữ, và có PDF
    # dùng chung một đối tượng liên kết cho nhiều trang (sửa trang này làm hỏng liên kết trang kia).
    snap = {i: _links_of(doc[i]) for i in range(doc.page_count)}
    for pinfo in pages:
        page = doc[pinfo["page"] - 1]
        todo = [s for s in pinfo["segments"] if s["translate"] and trans.get(s["id"])]
        if not todo:
            if footer:
                _footer(page, arch, css, huong)
            continue
        for s in todo:  # xóa chữ gốc theo từng dòng (dải giữa dòng để không đụng dòng bên cạnh)
            for (x0, y0, x1, y1) in s["lines"]:
                h = y1 - y0
                page.add_redact_annot(fz.Rect(x0, y0 + h * 0.3, x1, y1 - h * 0.3), fill=False)
        _drop_links(page)  # tháo liên kết ra trước, gắn lại từ bản chụp sau
        page.apply_redactions(images=0, graphics=0, text=0)  # giữ ảnh, giữ nét vẽ, chỉ xóa chữ
        for lk in snap.get(pinfo["page"] - 1, []):
            try:
                page.insert_link(dict(lk))
            except Exception:
                pass
        pinfo["_text_rects"] = [s["rect"] for s in pinfo["segments"]]
        obstacles = [s["rect"] for s in pinfo["segments"]] + pinfo["images"]
        for s in todo:
            others = [r for r in obstacles if r is not s["rect"]]
            vi = trans[s["id"]]
            align = None
            if huong == "vi-en" and s["align"] == "justify" and len(vi.split()) < 6 * len(s["lines"]):
                align = "left"  # tiếng Anh ngắn hơn: căn đều với ít từ mỗi dòng làm giãn khoảng trắng
            body = _html_for(s, vi, align=align)
            spare = -1
            if huong == "vi-en":
                # Tiếng Anh thường hẹp hơn tiếng Việt 5–17%: thử đúng khung gốc, cỡ chữ gốc trước; chỉ nới khung khi tràn
                x0, y0, x1, y1 = s["rect"]
                spare, scale = page.insert_htmlbox(fz.Rect(x0, y0, x1 + 0.5, y1 + 0.5), body, css=css, archive=arch,
                                                   scale_low=1)
            if spare >= 0:
                status = "vua"
            else:
                fx0, fy0, fx1, fy1 = _free_rect(s, pinfo, others)
                rect = fz.Rect(fx0, fy0, fx1 + 0.5, fy1)
                spare, scale = page.insert_htmlbox(rect, body, css=css, archive=arch, scale_low=0.55)
                status = "vua"
                if spare < 0:
                    spare, scale = page.insert_htmlbox(rect, body, css=css, archive=arch, scale_low=0)
                    status = "tran"
                elif scale < 0.8:
                    status = "thu-nho"
            log[s["id"]] = {"scale": round(scale, 3), "status": status, "page": s["page"]}
        if footer:
            _footer(page, arch, css, huong)
    page = None  # bỏ tham chiếu tới trang cuối cùng: reload_page đòi trang không còn ai giữ
    for i, want in snap.items():  # trang nào bị mất liên kết (do dùng chung đối tượng) thì gắn lại
        if not want:
            continue
        page = doc.reload_page(doc[i])  # nạp lại để thấy cả liên kết vừa gắn
        if len(_links_of(page)) < len(want):
            _drop_links(page)
            for lk in want:
                try:
                    page.insert_link(dict(lk))
                except Exception:
                    pass
    doc.subset_fonts()
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_pdf, **SAVE_OPTS)
    doc.close()
    _save(job / "dung_log.json", log)
    return log


def _links_of(page) -> list:
    try:
        out = []
        for lk in page.get_links():
            lk = dict(lk)
            lk.pop("xref", None)
            lk.pop("id", None)
            out.append(lk)
        return out
    except Exception:  # PyMuPDF cũ có thể lỗi khi trang trỏ tới liên kết đã bị xóa
        return []


def _drop_links(page):
    try:
        for lk in page.get_links():
            page.delete_link(lk)
    except Exception:
        pass


def _footer(page, arch, css, huong="en-vi"):
    fz = _import_pymupdf()
    w, h = page.rect.width, page.rect.height
    text = CHAN_TRANG_EN if huong == "vi-en" else CHAN_TRANG
    page.insert_htmlbox(fz.Rect(36, h - 13, w - 36, h - 3),
                        f'<p style="font-family:vnsans;font-size:6pt;color:#8a9597;text-align:center">{text}</p>',
                        css=css, archive=arch, scale_low=0.5)


def build_facing_book(src, vi, out):
    fz = _import_pymupdf()
    s, t, o = fz.open(src), fz.open(vi), fz.open()
    for i in range(min(s.page_count, t.page_count)):
        o.insert_pdf(s, from_page=i, to_page=i)
        o.insert_pdf(t, from_page=i, to_page=i)
    o.save(out, **SAVE_OPTS)


def build_facing_sheet(src, vi, out):
    fz = _import_pymupdf()
    s, t, o = fz.open(src), fz.open(vi), fz.open()
    for i in range(min(s.page_count, t.page_count)):
        r = s[i].rect
        pg = o.new_page(width=r.width * 2, height=r.height)
        pg.show_pdf_page(fz.Rect(0, 0, r.width, r.height), s, i)
        pg.show_pdf_page(fz.Rect(r.width, 0, 2 * r.width, r.height), t, i)
        sh = pg.new_shape()
        sh.draw_line((r.width, 0), (r.width, r.height))
        sh.finish(color=(0.82, 0.84, 0.85), width=0.6)
        sh.commit()
    o.save(out, **SAVE_OPTS)


def build_interleaved(job: Path, out_pdf: Path, footer=True):
    """Xen đoạn: mỗi đoạn gốc (xám) ngay trên bản dịch (xanh), dàn lại theo dòng chảy trên khổ giấy gốc."""
    fz = _import_pymupdf()
    pages = _load(job / "trang.json")
    trans = _load(job / "ban_dich.json", {})
    huong = _huong(job)
    arch = fz.Archive(str(FONT_DIR))
    css = _css() + "p, h3 {margin: 0 0 2pt 0;} .goc {color:#5b6466;} .dich {color:#0a6c7d; margin: 0 0 7pt 0;}"
    parts = []
    counts = {}
    for pinfo in pages:
        for s in {x["text"] for x in pinfo["segments"]}:
            counts[s] = counts.get(s, 0) + 1
    repeated = {t for t, c in counts.items() if c >= 3 and len(t.split()) <= 12}  # đầu trang / chân trang lặp lại
    for pinfo in pages:
        parts.append(f'<p style="font-size:7.5pt;color:#9aa4a6;margin-top:6pt">— Trang {pinfo["page"]} —</p>')
        for s in pinfo["segments"]:
            if not s["translate"] or s["text"] in repeated:
                continue
            tag = "h3" if s.get("kind") == "tieu-de" else "p"
            sz = min(max(s["size"], 8.5), 14) if tag == "h3" else 9.5
            parts.append(f'<{tag} class="goc" style="font-size:{sz}pt">{html.escape(s["text"])}</{tag}>')
            vi = trans.get(s["id"])
            if vi:
                parts.append(f'<{tag} class="dich" style="font-size:{sz}pt">{html.escape(vi)}</{tag}>')
    story = fz.Story("".join(parts), user_css=css, archive=arch)
    w, h = pages[0]["width"], pages[0]["height"]
    writer = fz.DocumentWriter(str(out_pdf))
    more = True
    while more:
        dev = writer.begin_page(fz.Rect(0, 0, w, h))
        more, _ = story.place(fz.Rect(54, 54, w - 54, h - 40))
        story.draw(dev)
        writer.end_page()
    writer.close()
    d = fz.open(out_pdf)
    if footer:
        for pg in d:
            _footer(pg, arch, _css(), huong)
    d.subset_fonts()
    tmp = out_pdf.with_suffix(".tmp.pdf")
    d.save(tmp, **SAVE_OPTS)
    d.close()
    tmp.replace(out_pdf)


def cmd_dung(a) -> int:
    job = _job_dir(a)
    meta = _load(job / "meta.json")
    batches = _load(job / "lo.json")
    trans = _load(job / "ban_dich.json", {})
    total = sum(len(b["ids"]) for b in batches)
    done = sum(1 for b in batches for i in b["ids"] if trans.get(i))
    if done == 0:
        sys.exit("Chưa có bản dịch nào. Chạy lay-lo / nap-lo trước.")
    huong = meta.get("huong", "en-vi")
    src_l, tgt_l = HUONG[huong]
    if done < total:
        print(f"LƯU Ý: mới dịch {done}/{total} đoạn; phần chưa dịch giữ nguyên {TEN_NGU[src_l]}.")
    out = _out_dir(a)
    stem = Path(meta["ten"]).stem
    files = []
    vi_pdf = out / f"{stem}_{tgt_l.upper()}.pdf"
    # Dựng lại bản tiếng Việt chỉ khi bản dịch hoặc tùy chọn chân trang đổi; nhờ vậy gọi từng chế độ một
    # (don-ngu rồi doi-trang, hai-cot, xen-doan) mà không phải dựng lại từ đầu mỗi lần.
    khoa = f"{(job / 'ban_dich.json').stat().st_mtime_ns}|{not a.khong_chan_trang}|{vi_pdf}|{PHIEN_BAN}"
    khoa_file = job / "vi_khoa.txt"
    if vi_pdf.is_file() and khoa_file.is_file() and khoa_file.read_text(encoding="utf-8") == khoa \
            and (job / "dung_log.json").is_file():
        log = _load(job / "dung_log.json")
        print(f"Dùng lại bản {TEN_NGU[tgt_l]} đã dựng: {vi_pdf.name}")
    else:
        log = build_translated(job, vi_pdf, footer=not a.khong_chan_trang)
        khoa_file.write_text(khoa, encoding="utf-8")
    files.append(vi_pdf)
    modes = {"tat-ca": ["doi-trang", "hai-cot", "xen-doan"]}.get(a.che_do, [a.che_do])
    if "doi-trang" in modes:
        p = out / f"{stem}_song-ngu-doi-trang.pdf"
        build_facing_book(job / "goc.pdf", vi_pdf, p)
        files.append(p)
    if "hai-cot" in modes:
        p = out / f"{stem}_song-ngu-hai-cot.pdf"
        build_facing_sheet(job / "goc.pdf", vi_pdf, p)
        files.append(p)
    if "xen-doan" in modes:
        p = out / f"{stem}_song-ngu-xen-doan.pdf"
        build_interleaved(job, p, footer=not a.khong_chan_trang)
        files.append(p)
    _save(job / "ket_qua.json", [str(f) for f in files])
    n_tran = sum(1 for v in log.values() if v["status"] == "tran")
    n_nho = sum(1 for v in log.values() if v["status"] == "thu-nho")
    print("ĐÃ DỰNG:")
    for f in files:
        mb = f.stat().st_size / 1e6
        print(f"  {f}  ({mb:.1f} MB){'  ⚠ quá ' + str(GIOI_HAN_TAI_VE_MB) + ' MB, có thể không tải về được trong Claude.ai' if mb > GIOI_HAN_TAI_VE_MB else ''}")
    print(f"Đoạn phải thu nhỏ chữ dưới 80%: {n_nho} · đoạn tràn khung: {n_tran}")
    print("Tiếp theo: dich_pdf.py kiem-dinh")
    return 0


# --------------------------------------------------------------------------------------------
# Kiểm định
# --------------------------------------------------------------------------------------------

def _font_glyph_checker():
    fz = _import_pymupdf()
    # Bản web chỉ nạp những họ phông tài liệu dùng tới, nên bỏ qua file phông không có.
    fonts = {k: fz.Font(fontfile=str(FONT_DIR / f)) for k, f in FONT_FILES.items() if (FONT_DIR / f).is_file()}

    def missing(text, bold, italic, family="sans"):
        st = ("bold" if bold else "") + ("italic" if italic else "") or "regular"
        f = fonts.get(f"{family}-{st}") or fonts.get(f"{family}-regular") or fonts["sans-regular"]
        return [c for c in set(text) if not c.isspace() and not f.has_glyph(ord(c))]
    return missing


def _ghost_words(job: Path, out_doc, pages, trans) -> dict:
    """Chữ tiếng Việt gốc còn sót dưới bản tiếng Anh (lệnh xóa không xóa hết): từ có dấu tiếng Việt nằm trong dòng gốc
    đã dịch mà không có trong bản dịch của đoạn đó."""
    fz = _import_pymupdf()
    found = {}
    for pinfo in pages:
        segs = [s for s in pinfo["segments"] if s["translate"] and trans.get(s["id"])]
        if not segs or pinfo["page"] > out_doc.page_count:
            continue
        words = out_doc[pinfo["page"] - 1].get_text("words")
        for s in segs:
            mine = set(re.findall(r"[^\W\d_]+", unicodedata.normalize("NFC", trans[s["id"]])))
            rects = [fz.Rect(r) for r in s["lines"]]
            for w in words:
                t = unicodedata.normalize("NFC", w[4])
                if not _VI_ONLY.search(t) or any(x in mine for x in re.findall(r"[^\W\d_]+", t)):
                    continue
                c = fz.Point((w[0] + w[2]) / 2, (w[1] + w[3]) / 2)
                if any(r.contains(c) for r in rects):
                    found.setdefault(s["id"], []).append(t)
    return {k: " ".join(v[:6]) for k, v in found.items()}


def cmd_kiem_dinh(a) -> int:
    fz = _import_pymupdf()
    job = _job_dir(a)
    meta = _load(job / "meta.json")
    pages = _load(job / "trang.json")
    trans = _load(job / "ban_dich.json", {})
    log = _load(job / "dung_log.json", {})
    files = [Path(f) for f in _load(job / "ket_qua.json", [])]
    if not files:
        sys.exit("Chưa dựng PDF. Chạy: dich_pdf.py dung")
    huong = meta.get("huong", "en-vi")
    src_l, tgt_l = HUONG[huong]
    vi_pdf = files[0]
    missing_glyph = _font_glyph_checker()
    segs = [s for p in pages for s in p["segments"] if s["translate"]]
    chua_dich = [s["id"] for s in segs if not trans.get(s["id"])]
    tofu, nghi_van = {}, {}
    for s in segs:
        vi = trans.get(s["id"])
        if not vi:
            continue
        m = missing_glyph(vi, s["bold"], s["italic"], s.get("family", "sans"))
        if m:
            tofu[s["id"]] = "".join(sorted(m))
        w = _check_translation(s["text"], vi, huong)
        if w:
            nghi_van[s["id"]] = w
    tran = [k for k, v in log.items() if v["status"] == "tran"]
    thu_nho = [k for k, v in log.items() if v["status"] == "thu-nho"]
    src = fz.open(job / "goc.pdf")
    out = fz.open(vi_pdf)
    links_src = sum(len(p.get_links()) for p in src)
    links_out = sum(len(p.get_links()) for p in out)
    bad_chars = sum(p.get_text().count("�") for p in out)
    no_text_pages = [p.number + 1 for p in out if pages[p.number]["chars"] > 20 and len(p.get_text().strip()) < 10]
    same_pages = src.page_count == out.page_count and all(
        abs(src[i].rect.width - out[i].rect.width) < 0.5 and abs(src[i].rect.height - out[i].rect.height) < 0.5
        for i in range(src.page_count))
    n_tofu = sum(len(v) for v in tofu.values()) + bad_chars
    ghost = _ghost_words(job, out, pages, trans) if huong == "vi-en" else {}
    # (tên hạng mục, đạt?, chi tiết, chặn?) — mục không chặn chỉ là cảnh báo, không đánh trượt
    checks = [
        ("Số trang và khổ giấy giữ nguyên", same_pages, f"{out.page_count}/{src.page_count} trang", True),
        ("Ký tự lỗi phông (ô vuông, mất dấu do phông)" if tgt_l == "vi" else "Ký tự lỗi phông (ô vuông)",
         n_tofu == 0, f"{n_tofu} ký tự", True),
        ("Chữ là chữ thật (bôi đen, tìm kiếm được)", not no_text_pages, f"{len(no_text_pages)} trang không có lớp chữ", True),
        ("Đoạn tràn khung", not tran, f"{len(tran)} đoạn", True),
        ("Liên kết giữ nguyên", links_out >= links_src, f"{links_out}/{links_src} liên kết", True),
        ("Đoạn chưa dịch", not chua_dich, f"{len(chua_dich)}/{len(segs)} đoạn", True),
    ]
    if huong == "vi-en":
        checks.append(("Chữ tiếng Việt gốc chưa xóa hết", not ghost, f"{len(ghost)} đoạn", True))
        checks.append(("Đoạn nghi vấn (còn tiếng Việt, lệch số liệu, ngày, số hiệu)", not nghi_van,
                       f"{len(nghi_van)} đoạn", False))
    else:
        checks.append(("Đoạn nghi vấn (còn tiếng Anh, thiếu dấu, lệch số liệu)", not nghi_van, f"{len(nghi_van)} đoạn", False))
    ok = all(c[1] for c in checks if c[3])
    now = _dt.datetime.now().strftime("%d/%m/%Y %H:%M")
    ls = meta.get("lam_sach") or {}
    lines = ["# Phiếu kiểm định bản dịch", "",
             f"- Tài liệu: **{meta['ten']}** · {meta['so_trang']} trang · {len(segs)} đoạn",
             f"- Chiều dịch: {TEN_NGU[src_l]} → {TEN_NGU[tgt_l]}",
             f"- File kiểm định: `{vi_pdf.name}`",
             f"- Thời điểm: {now} · công cụ pdf-translation-layout {PHIEN_BAN}",
             f"- Kết luận: **{'ĐẠT' if ok else 'CHƯA ĐẠT'}**" + ("" if not (nghi_van or chua_dich or thu_nho) else " (có mục cần xem lại)"),
             "", "| Hạng mục | Kết quả | Chi tiết |", "|---|---|---|"]
    for name, passed, detail, block in checks:
        mark = '✔ Đạt' if passed else ('✘ Cần sửa' if block else '⚠ Xem lại')
        lines.append(f"| {name} | {mark} | {detail} |")
    lines.append(f"| Đoạn phải thu nhỏ chữ dưới 80% | {'✔' if not thu_nho else 'ⓘ'} | {len(thu_nho)} đoạn |")
    if meta.get("trang_scan"):
        lines.append(f"| Trang scan không dịch được | ⓘ | {len(meta['trang_scan'])} trang |")
    if ls.get("chuyen_ma"):
        lines.append("| Chữ phông cũ đã chuyển sang Unicode | ⓘ | "
                     + ", ".join(f"{k.upper()} {v} dòng" for k, v in ls["chuyen_ma"].items()) + " |")
    if ls.get("dau_roi"):
        lines.append(f"| Dòng đã gắn lại dấu thanh bị tách rời | ⓘ | {ls['dau_roi']} dòng |")
    if ls.get("trang_loi_chu"):
        lines.append(f"| Trang chữ hỏng mã, giữ nguyên không dịch | ⓘ | {len(ls['trang_loi_chu'])} trang |")
    n_head = len(lines)

    def _detail(title, items):
        if not items:
            return
        lines.extend(["", f"## {title}", ""])
        idx = {s["id"]: s for s in segs}
        for k in list(items)[:40]:
            note = items[k] if isinstance(items, dict) else ""
            src_t = idx[k]["text"][:90] if k in idx else ""
            lines.append(f"- `{k}` (trang {idx[k]['page'] if k in idx else '?'}) {note}: “{src_t}…”")
        if len(items) > 40:
            lines.append(f"- … và {len(items) - 40} đoạn khác")
    _detail("Ký tự phông không hiển thị được", tofu)
    _detail("Đoạn tràn khung", {k: "" for k in tran})
    _detail("Chữ tiếng Việt gốc chưa xóa hết", ghost)
    _detail("Đoạn nghi vấn", nghi_van)
    _detail("Đoạn chưa dịch", {k: "" for k in chua_dich})
    if huong == "vi-en":
        lines += ["", "> Bản dịch máy để tham khảo, không phải bản dịch có chứng thực. Giấy tờ nộp cơ quan nhà nước, "
                  "đại sứ quán, trường học (học bạ, bằng cấp, giấy tờ hộ tịch, sao kê) cần người dịch ký và được chứng thực. "
                  "Con dấu và chữ ký dạng ảnh trong bản gốc vẫn nằm nguyên trên bản tiếng Anh."]
    else:
        lines += ["", "> Bản dịch cá nhân bằng AI, dùng để đọc hiểu. Muốn phát hành hoặc chia sẻ công khai cần có sự đồng ý của chủ sở hữu bản quyền."]
    report_md = _out_dir(a) / f"{Path(meta['ten']).stem}_phieu-kiem-dinh.md"
    report_md.write_text("\n".join(lines), encoding="utf-8")
    _save(job / "kiem_dinh.json", {"dat": ok, "huong": huong,
                                    "checks": [{"muc": c[0], "dat": c[1], "chi_tiet": c[2], "canh_bao": not c[3]} for c in checks],
                                    "tofu": tofu, "tran": tran, "thu_nho": thu_nho, "nghi_van": nghi_van,
                                    "chua_dich": chua_dich, "chu_bong": ghost})
    print("\n".join(lines[:n_head]))
    print(f"\nPhiếu kiểm định: {report_md}")
    if nghi_van or tofu:
        print("Gợi ý: dịch lại các đoạn nghi vấn rồi nap-lo, sau đó dung + kiem-dinh lại.")
    return 0 if ok else 2


# --------------------------------------------------------------------------------------------
# Chấm điểm PDF dịch bất kỳ (bộ đo công khai)
# --------------------------------------------------------------------------------------------

_BROKEN_IN_WORD = re.compile(r"(?<=[^\W\d_])[·?\ufffd□■](?=[^\W\d_])")


def _tofu_count(doc) -> int:
    """Ký tự người đọc sẽ thấy là ô vuông hoặc mất dấu:
    glyph số 0 (.notdef) của phông nhúng, ký tự thay thế U+FFFD/□, và dấu '·'/'?' chen giữa một từ
    (dấu hiệu phông chuẩn kiểu Helvetica không có chữ Việt nên làm rơi ký tự)."""
    bad = 0
    for page in doc:
        try:
            for sp in page.get_texttrace():
                for ch in sp["chars"]:
                    if ch[1] == 0 and not chr(ch[0]).isspace():
                        bad += 1
        except Exception:
            pass
        t = page.get_text()
        bad += t.count("\ufffd") + t.count("□")
        bad += len(_BROKEN_IN_WORD.findall(t))
    return bad


def cmd_cham_diem(a) -> int:
    fz = _import_pymupdf()
    src, out = fz.open(a.goc), fz.open(a.dich)
    tofu = _tofu_count(out)
    txt_src = "".join(p.get_text() for p in src)
    txt_out = "".join(p.get_text() for p in out)
    words_out = re.findall(r"[^\W\d_]+", txt_out)
    vi = _vi_ratio(txt_out)
    en = _en_ratio(txt_out)
    links_src = sum(len(p.get_links()) for p in src)
    links_out = sum(len(p.get_links()) for p in out)
    text_pages_src = [i for i, p in enumerate(src) if len(p.get_text().strip()) > 20]
    raster = [i + 1 for i in text_pages_src if i < out.page_count and len(out[i].get_text().strip()) < 10]
    overlap = 0
    for p in out:
        boxes = [fz.Rect(l["bbox"]) for b in p.get_text("dict")["blocks"] for l in b.get("lines", [])]
        for i in range(len(boxes)):
            for j in range(i + 1, min(len(boxes), i + 40)):
                inter = boxes[i] & boxes[j]
                if not inter.is_empty and inter.get_area() > 0.25 * min(boxes[i].get_area(), boxes[j].get_area()):
                    overlap += 1
    lang_metrics = {"ty_le_tu_co_dau": round(vi, 3), "ty_le_tu_tieng_anh_con_lai": round(en, 3)}
    if _detect_lang([txt_src]) == "vi":
        # Chiều Việt → Anh: đo tiếng Việt còn sót (có dấu, và không dấu) thay cho tỷ lệ từ có dấu
        masked = _MASK.sub(" ", unicodedata.normalize("NFC", txt_out))
        ws = re.findall(r"[^\W\d_]+", masked)
        lang_metrics = {"huong": "vi-en",
                        "ty_le_tu_tieng_viet_con_lai": round(sum(1 for w in ws if _VI_ONLY.search(w)) / max(len(ws), 1), 3),
                        "ty_le_tu_tieng_viet_khong_dau": round(sum(1 for w in ws if w.lower() in _VI_NODIA) / max(len(ws), 1), 3)}
    res = {
        "cong_cu": a.ten or Path(a.dich).stem,
        "tai_lieu": Path(a.goc).name,
        "so_trang": f"{out.page_count}/{src.page_count}",
        "ky_tu_loi_phong": tofu,
        **lang_metrics,
        "lien_ket": f"{links_out}/{links_src}",
        "trang_mat_lop_chu": len(raster),
        "cap_dong_chong_nhau": overlap,
        "do_trung_bo_cuc": _layout_match(src, out) if out.page_count == src.page_count else "",
        "dung_luong_mb": round(Path(a.dich).stat().st_size / 1e6, 2),
        "so_tu": len(words_out),
    }
    print(json.dumps(res, ensure_ascii=False, indent=1))
    if a.csv:
        import csv
        new = not Path(a.csv).is_file()
        with open(a.csv, "a", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(res.keys())
            w.writerow(res.values())
    _ = txt_src
    return 0


def _layout_match(src, out, nx=24, ny=32) -> float:
    """Độ trùng bố cục: chia trang thành lưới, đánh dấu ô có chữ ở bản gốc và bản dịch, lấy chỉ số Jaccard trung bình.
    1.0 = chữ dịch nằm đúng những vùng chữ gốc chiếm; thấp = chữ bị dồn, tràn, dời chỗ hoặc mất."""
    scores = []
    for ps, po in zip(src, out):
        def cells(page):
            w, h = page.rect.width / nx, page.rect.height / ny
            got = set()
            for b in page.get_text("dict")["blocks"]:
                for ln in b.get("lines", []):
                    x0, y0, x1, y1 = ln["bbox"]
                    if not ln.get("spans") or not "".join(sp["text"] for sp in ln["spans"]).strip():
                        continue
                    for i in range(max(0, int(x0 // w)), min(nx, int(x1 // w) + 1)):
                        for j in range(max(0, int(y0 // h)), min(ny, int(y1 // h) + 1)):
                            got.add((i, j))
            return got
        a_, b_ = cells(ps), cells(po)
        if len(a_) >= 4:
            scores.append(len(a_ & b_) / len(a_ | b_))
    return round(sum(scores) / len(scores), 3) if scores else 0.0


# --------------------------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(prog="dich_pdf.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--thu-muc", help="Thư mục làm việc (mặc định ./dich_pdf_work)")
    ap.add_argument("--viec", help="Tên việc (mặc định: tài liệu đang làm)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("kiem-tra").set_defaults(f=cmd_kiem_tra)
    p = sub.add_parser("chuan-bi")
    p.add_argument("pdf")
    p.add_argument("--lo", type=int, default=15, help="Số trang mỗi lô (10–20)")
    p.add_argument("--lam-lai", action="store_true")
    p.add_argument("--trang", help="Chỉ dịch các trang này, vd \"1-10\" hoặc \"1-5,8,12-14\"")
    p.add_argument("--huong", choices=["tu-dong", "en-vi", "vi-en"], default="tu-dong",
                   help="Chiều dịch: en-vi (Anh → Việt), vi-en (Việt → Anh); mặc định tự nhận theo tài liệu")
    p.set_defaults(f=cmd_chuan_bi)
    p = sub.add_parser("lay-lo")
    p.add_argument("--lo", type=int, default=0)
    p.add_argument("--toi-da", type=int, default=12000, help="Số ký tự tối đa mỗi lần in (mặc định 12000)")
    p.set_defaults(f=cmd_lay_lo)
    p = sub.add_parser("nap-lo")
    p.add_argument("file", help="File JSON {id: bản dịch} (hoặc chuỗi JSON)")
    p.set_defaults(f=cmd_nap_lo)
    sub.add_parser("tien-do").set_defaults(f=cmd_tien_do)
    p = sub.add_parser("dung")
    p.add_argument("--che-do", default="tat-ca", choices=["don-ngu", "doi-trang", "hai-cot", "xen-doan", "tat-ca"])
    p.add_argument("--xuat", help="Thư mục xuất (mặc định /mnt/user-data/outputs nếu có, không thì ./ket_qua)")
    p.add_argument("--khong-chan-trang", action="store_true", help="Không in dòng chân trang 'bản dịch cá nhân'")
    p.set_defaults(f=cmd_dung)
    p = sub.add_parser("kiem-dinh")
    p.add_argument("--xuat")
    p.set_defaults(f=cmd_kiem_dinh)
    p = sub.add_parser("cham-diem")
    p.add_argument("--goc", required=True)
    p.add_argument("--dich", required=True)
    p.add_argument("--ten", default="")
    p.add_argument("--csv", default="")
    p.set_defaults(f=cmd_cham_diem)
    a = ap.parse_args()
    if a.cmd != "kiem-tra":
        try:
            _import_pymupdf()
        except ImportError:
            sys.exit("Chưa có PyMuPDF. Chạy trước:  dich_pdf.py kiem-tra")
    sys.exit(a.f(a))


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    try:
        main()
    except BrokenPipeError:  # khi đầu ra bị cắt (vd. | head), thoát êm
        try:
            sys.stdout = open(os.devnull, "w")
        except Exception:
            pass
        sys.exit(0)
