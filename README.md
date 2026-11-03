# pdf-translation-layout

Dịch PDF tiếng Anh sang tiếng Việt **giữ nguyên bố cục trang**, ngay trên trình duyệt hoặc trong trợ lý AI bạn đang dùng: Claude, ChatGPT, Antigravity. Không cài Python, không gõ lệnh.

- Chữ trong bản dịch là chữ thật: bôi đen, tìm kiếm, sao chép được. Ảnh, bảng, nét vẽ, liên kết giữ nguyên.
- Phông đủ dấu tiếng Việt, cùng số đo bề ngang với Times New Roman, Arial, Courier New, Calibri, nên bản dịch nằm gọn trong khung cũ.
- Xuất 4 kiểu: bản tiếng Việt, song ngữ đối trang, song ngữ hai cột, song ngữ xen đoạn.
- Mỗi lần dịch kèm **phiếu kiểm định**: lỗi phông/mất dấu, đoạn tràn khung, đoạn còn tiếng Anh hoặc lệch số liệu, liên kết, lớp chữ thật.

Trang chủ và hướng dẫn có hình: https://pdf.huynhanhthuan.com

## Cách hoạt động

Trợ lý AI của bạn là người dịch. Công cụ (`dich_pdf.py`, một file Python) chỉ làm hai việc trợ lý AI làm kém: tách chữ khỏi trang PDF theo từng đoạn có mã số, và ghép bản dịch vào đúng chỗ với phông, cỡ chữ, màu, căn lề phù hợp. Tài liệu dài được chia lô; tiến độ lưu trên đĩa nên làm tiếp được.

## Dùng

| Nền tảng | Cách cài | File |
|---|---|---|
| Trình duyệt (mọi AI chat) | Mở https://pdf.huynhanhthuan.com/dich, kéo PDF vào. Bộ máy chạy trong trình duyệt (Pyodide + PyMuPDF), tài liệu không rời máy | `web/` |
| Claude.ai, Claude Desktop | Customize → Skills → + → Upload a skill. Bật Settings → Capabilities → Code execution and file creation | `pdf-translation-layout.zip` (trong Releases) |
| ChatGPT | Mở GPT "Dịch PDF giữ bố cục" (link trên trang chủ). Ai muốn tự dựng GPT: xem `chatgpt/` | `pdf-translation-layout-chatgpt.zip` |
| Antigravity | Giải nén rồi `agy plugin install ./pdf-translation-layout` | `pdf-translation-layout-antigravity.zip` |
| Claude Code | Chép `skills/pdf-translation-layout` vào `~/.claude/skills/` | — |

Sau đó đính kèm PDF và nhắn: **"Dịch file này sang tiếng Việt, giữ nguyên bố cục"**.

## Cấu trúc kho mã

```
plugin.json, assets/logo.svg     manifest plugin Antigravity (gốc kho = gốc plugin)
skills/pdf-translation-layout/   skill dùng chung cho mọi nền tảng
  SKILL.md                       hướng dẫn cho trợ lý AI
  scripts/dich_pdf.py            công cụ tách chữ, ghép bản dịch, dựng PDF, kiểm định, chấm điểm
  assets/fonts/                  phông Liberation, Carlito (SIL OFL 1.1)
chatgpt/                         Instructions và hướng dẫn tạo GPT
web/                             Trang dịch trên web: dich.html, dich-app.js, dich-worker.js, engine/web_api.py
antigravity/README.md            README hiển thị trong Marketplace
benchmark/                       giao thức đo, bộ chấm, PDF mẫu CC0, kết quả đo
tools/dong_goi.py                kiểm tra và đóng gói ba bản phát hành vào dist/
```

Đóng gói: `python tools/dong_goi.py` (bản ChatGPT tự tải wheel PyMuPDF 1.26.0 cho Linux x86_64). Lắp trang web: `python tools/dung_web.py <thư mục website>` (tải Pyodide 0.29.5 và PyMuPDF 1.28.2 bản WebAssembly làm bản dự phòng; mặc định trình duyệt tải hai thư viện này từ jsDelivr và PyPI, kiểm mã SHA-256 từng file, nên website chỉ phát phông chữ và mã dịch).

## Đo chất lượng

`benchmark/GIAO_THUC_DO.md` mô tả cách chấm **bất kỳ** PDF dịch tiếng Việt nào (của công cụ này hay công cụ khác): ký tự lỗi phông, tỷ lệ từ có dấu, liên kết, lớp chữ thật, dòng đè nhau, độ trùng bố cục. Kết quả đo hiện có: `benchmark/KET_QUA.md`.

## Bản quyền nội dung

Bản dịch một tác phẩm là tác phẩm phái sinh. Công cụ phục vụ **đọc hiểu cá nhân**: mỗi trang có dòng chân trang nhỏ "Bản dịch cá nhân bằng AI · không phân phối". Muốn đăng, chia sẻ công khai hoặc bán bản dịch sách, bài báo có bản quyền, bạn cần sự đồng ý của chủ sở hữu bản quyền.

## Tài liệu của bạn đi đâu

| Cách dùng | Tài liệu đi đâu |
|---|---|
| Claude.ai, ChatGPT | Chỉ vào tài khoản AI của bạn, theo chính sách của nhà cung cấp đó. Tác giả công cụ không nhận, không lưu gì. |
| Antigravity, Claude Code | Trang PDF được dựng trên máy bạn; chỉ phần chữ cần dịch đi tới AI bạn đang dùng. |

## Giới hạn

- PDF scan (trang là ảnh chụp) chưa dịch được.
- Chữ nằm trong ảnh, biểu đồ dạng ảnh giữ nguyên tiếng Anh.
- Claude.ai cho tải về tối đa 30 MB mỗi file.

## Giấy phép

Mã nguồn và tài liệu: MIT (`LICENSE`). Khi chạy, công cụ dùng PyMuPDF (AGPL-3.0) và phông chữ SIL OFL 1.1: xem `THIRD_PARTY_NOTICES.md`. File PDF mẫu trong `benchmark/mau/`: CC0.

Tác giả: Huỳnh Anh Thuận · hello@huynhanhthuan.com
