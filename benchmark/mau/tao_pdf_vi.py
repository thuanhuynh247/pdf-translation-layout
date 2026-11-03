#!/usr/bin/env python3
"""Tạo các PDF tiếng Việt mẫu (nội dung giả, không có dữ liệu cá nhân thật) để thử chiều Việt → Anh.

    python tao_pdf_vi.py <thư mục phông> <thư mục ra>

Ra 5 file:
  mau_vi_congvan.pdf   công văn 2 trang, Unicode NFC: bảng tiêu đề hai cột, số hiệu văn bản, ngày, tiền, %, danh sách,
                       bảng số liệu, liên kết, đoạn tiếng Anh sẵn có, gạch nối thật ("Bà Rịa - Vũng Tàu")
  mau_vi_nfd.pdf       cùng nội dung trang 1 nhưng chữ ở dạng NFD (dấu tổ hợp)
  mau_vi_tcvn3.pdf     chữ mã TCVN3, phông tên .VnTime / .VnTimeH (tiêu đề chữ hoa)
  mau_vi_vni.pdf       chữ mã VNI, phông tên VNI-Times
  mau_vi_dauroi.pdf    dấu thanh vẽ thành glyph riêng (MuPDF dồn về cuối dòng)
"""
import sys
import unicodedata
from pathlib import Path

import pymupdf as fz

FONTS = Path(sys.argv[1])
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
SERIF = FONTS / "LiberationSerif-Regular.ttf"
SERIF_B = FONTS / "LiberationSerif-Bold.ttf"

CSS = ("@font-face{font-family:s;src:url(LiberationSerif-Regular.ttf)}"
       "@font-face{font-family:s;src:url(LiberationSerif-Bold.ttf);font-weight:bold}"
       "@font-face{font-family:s;src:url(LiberationSerif-Italic.ttf);font-style:italic}"
       "*{font-family:s;font-size:12pt;margin:0;padding:0} p{margin:0 0 6pt 0;line-height:1.3}")
ARCH = fz.Archive(str(FONTS))

HEAD_L = ["ỦY BAN NHÂN DÂN TỈNH NGHỆ AN", "<b>SỞ TÀI CHÍNH</b>", "Số: 123/STC-QLG",
          "V/v hướng dẫn quản lý giá năm 2026"]
HEAD_R = ["<b>CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</b>", "<b>Độc lập - Tự do - Hạnh phúc</b>",
          "<i>Nghệ An, ngày 03 tháng 02 năm 2026</i>"]
BODY = [
    "<p style='text-align:center'>Kính gửi: Các doanh nghiệp sản xuất sợi trên địa bàn tỉnh</p>",
    "<p style='text-align:justify'>Căn cứ Nghị định số 15/2020/NĐ-CP ngày 03/02/2020 của Chính phủ và Thông tư số "
    "45/2024/TT-BTC của Bộ Tài chính, Sở Tài chính hướng dẫn các doanh nghiệp thực hiện kê khai giá đối với "
    "các mặt hàng thuộc danh mục bình ổn giá. Doanh nghiệp phải gửi văn bản kê khai trước ngày 15/03/2026 "
    "và chịu trách nhiệm về tính chính xác của số liệu đã kê khai.</p>",
    "<p style='text-align:justify'>Năm 2025, tổng doanh thu của các doanh nghiệp trong ngành đạt 1.250.000.000.000 đồng, "
    "tăng 3,5% so với năm trước. Chúng tôi đề nghị các đơn vị chủ động rà soát chi phí đầu vào, đặc biệt là giá bông "
    "nhập khẩu và chi phí vận chuyển từ cảng Bà Rịa - Vũng Tàu.</p>",
    "<p>a) Thời hạn kê khai: 05 ngày làm việc kể từ ngày điều chỉnh giá.</p>",
    "<p>b) Hồ sơ gửi về địa chỉ thư điện tử quanlygia@example.gov.vn hoặc trang https://example.gov.vn/ke-khai-gia.</p>",
    "<p>c) Trường hợp không thực hiện đúng quy định sẽ bị xử lý theo Điều 12 Nghị định số 87/2024/NĐ-CP.</p>",
]
TABLE = [("Mặt hàng", "Đơn vị", "Giá bình quân (đồng)"),
         ("Sợi cotton chải kỹ", "kg", "78.500"),
         ("Sợi pha polyester", "kg", "52.300"),
         ("Bông nhập khẩu", "tấn", "41.200.000")]
P2 = [
    "<p style='font-size:15pt'><b>HỒ SƠ NĂNG LỰC TÓM TẮT</b></p>",
    "<p style='text-align:justify'>Công ty Cổ phần Dệt May Phú Hưng được thành lập năm 2008, chuyên sản xuất sợi đơn và "
    "sợi pha phục vụ xuất khẩu. Nhà máy đặt tại khu công nghiệp ở huyện Nghi Lộc, có 350 lao động và công suất "
    "12.000 tấn sợi mỗi năm.</p>",
    "<p style='text-align:justify'>Sản phẩm của công ty đã có mặt tại Hàn Quốc, Nhật Bản và Thổ Nhĩ Kỳ. Chúng tôi cam kết "
    "giao hàng đúng hạn và kiểm soát chất lượng theo tiêu chuẩn ISO 9001:2015.</p>",
    "<p><i>Our mission is to deliver reliable yarn with consistent quality to every partner.</i></p>",
    "<p>Người liên hệ: Ông Nguyễn Văn An, Giám đốc Kinh doanh. Điện thoại: 0238 3123 456.</p>",
]


def page_one(doc, nfd=False):
    pg = doc.new_page(width=595, height=842)
    tx = (lambda t: unicodedata.normalize("NFD", t)) if nfd else (lambda t: t)
    pg.insert_htmlbox(fz.Rect(50, 50, 290, 140), tx("".join(f"<p style='text-align:center;font-size:11pt;margin:0'>{x}</p>" for x in HEAD_L)),
                      css=CSS, archive=ARCH)
    pg.insert_htmlbox(fz.Rect(300, 50, 560, 140), tx("".join(f"<p style='text-align:center;font-size:11pt;margin:0'>{x}</p>" for x in HEAD_R)),
                      css=CSS, archive=ARCH)
    pg.insert_htmlbox(fz.Rect(60, 160, 535, 520), tx("".join(BODY)), css=CSS, archive=ARCH)
    y = 540
    for i, row in enumerate(TABLE):
        xs = [(60, 260), (270, 360), (370, 535)]
        for (x0, x1), cell in zip(xs, row):
            b = "<b>" if i == 0 else ""
            pg.insert_htmlbox(fz.Rect(x0, y, x1, y + 18), tx(f"<p style='font-size:11pt;margin:0'>{b}{cell}</p>"), css=CSS, archive=ARCH)
        y += 22
    pg.insert_link({"kind": fz.LINK_URI, "from": fz.Rect(60, 380, 535, 400), "uri": "https://example.gov.vn/ke-khai-gia"})
    return pg


def page_two(doc):
    pg = doc.new_page(width=595, height=842)
    pg.insert_htmlbox(fz.Rect(60, 60, 535, 600), "".join(P2), css=CSS, archive=ARCH)
    pg.insert_htmlbox(fz.Rect(60, 760, 535, 790), "<p style='text-align:center;font-size:9pt'>Trang 2</p>", css=CSS, archive=ARCH)


d = fz.open()
page_one(d)
page_two(d)
d.subset_fonts()
d.save(OUT / "mau_vi_congvan.pdf", garbage=4, deflate=True)

d = fz.open()
page_one(d, nfd=True)
d.subset_fonts()
d.save(OUT / "mau_vi_nfd.pdf", garbage=4, deflate=True)


# ---- Mã cũ: viết chữ "mặt chữ" TCVN3/VNI bằng một phông thường, rồi đổi tên phông thành .VnTime / VNI-Times ----
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skills" / "pdf-translation-layout" / "scripts"))
import dich_pdf as D  # noqa: E402

TO_TCVN3 = {}
for i in range(0xA1, 0xFF):
    c = chr(i)
    v = c.translate(D._TCVN3)
    if v != c:
        TO_TCVN3[v] = c
TO_VNI = {v: k for k, v in D._VNI.items()}

LEGACY_LINES = [
    "Cộng hòa xã hội chủ nghĩa Việt Nam",
    "Độc lập - Tự do - Hạnh phúc",
    "Căn cứ Nghị định số 15/2020/NĐ-CP, Sở Tài chính hướng dẫn kê khai giá.",
    "Thủ tướng Chính phủ yêu cầu các bộ, ngành thực hiện nghiêm túc.",
    "Thông tư này có hiệu lực từ ngày 01 tháng 7 năm 2009.",
]


def enc_tcvn3(t):
    out = []
    for ch in t:
        if ch in TO_TCVN3:
            out.append(TO_TCVN3[ch])
        elif ch.lower() in TO_TCVN3 and ch.isupper():
            out.append(TO_TCVN3[ch.lower()])  # TCVN3 không có chữ hoa có dấu: viết bằng chữ thường
        else:
            out.append(ch)
    return "".join(out)


def enc_vni(t):
    return "".join(TO_VNI.get(ch, ch) for ch in t)


def legacy_pdf(path, enc, fontname, heading_font=None):
    d = fz.open()
    pg = d.new_page(width=595, height=842)
    pg.insert_font(fontname="L1", fontfile=str(SERIF))
    if heading_font:
        pg.insert_font(fontname="L2", fontfile=str(SERIF_B))
        # Phông chữ hoa .VnTimeH: tài liệu gõ chữ thường, phông vẽ ra chữ hoa
        pg.insert_text((60, 70), enc("quyết định về việc ban hành quy chế"), fontname="L2", fontsize=13)
    y = 110
    for line in LEGACY_LINES:
        pg.insert_text((60, y), enc(line), fontname="L1", fontsize=12)
        y += 22
    d.subset_fonts()
    d.save(path, garbage=4, deflate=True)
    d.close()
    d = fz.open(path)
    for xref in range(1, d.xref_length()):
        t = d.xref_get_key(xref, "Type")[1]
        base = d.xref_get_key(xref, "BaseFont")[1]
        if t == "/Font" and base and base != "null":
            new = fontname if "Bold" not in base else (heading_font or fontname)
            d.xref_set_key(xref, "BaseFont", "/" + new)
        if d.xref_get_key(xref, "FontName")[0] == "name":
            base2 = d.xref_get_key(xref, "FontName")[1]
            d.xref_set_key(xref, "FontName", "/" + (heading_font if heading_font and "Bold" in base2 else fontname))
    d.save(path, incremental=True, encryption=0)


legacy_pdf(OUT / "mau_vi_tcvn3.pdf", enc_tcvn3, ".VnTime", heading_font=".VnTimeH")
legacy_pdf(OUT / "mau_vi_vni.pdf", enc_vni, "VNI-Times")

# ---- Dấu thanh vẽ thành glyph riêng ----
d = fz.open()
pg = d.new_page(width=595, height=842)
font = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
pg.insert_font(fontname="dv", fontfile=font)
fo = fz.Font(fontfile=font)
TONES = {"\u0300", "\u0301", "\u0303", "\u0309", "\u0323"}
target = "Tiếng Việt có dấu thanh rời"
bases, marks = [], {}
for ch in target:
    dec = unicodedata.normalize("NFD", ch)
    tone = [c for c in dec if c in TONES]
    if tone:
        marks[len(bases)] = tone[0]
    bases.append(unicodedata.normalize("NFC", "".join(c for c in dec if c not in TONES)))
base = "".join(bases)
x0, y0 = 60, 100
pg.insert_text((x0, y0), base, fontname="dv", fontsize=12)
for idx, mk in marks.items():
    bx0 = x0 + fo.text_length(base[:idx], 12)
    center = bx0 + fo.text_length(base[idx], 12) / 2
    gb = fo.glyph_bbox(ord(mk))
    xm = center - (gb.x0 + gb.x1) / 2 * 12  # đặt dấu đúng trên chữ cái, như phần mềm dàn trang thật
    pg.insert_text((xm, y0), mk, fontname="dv", fontsize=12)
d.subset_fonts()
d.save(OUT / "mau_vi_dauroi.pdf", garbage=4, deflate=True)
print("đã tạo:", sorted(p.name for p in OUT.glob("mau_vi_*.pdf")))
