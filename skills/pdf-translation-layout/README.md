# pdf-translation-layout 3.1

Dịch PDF tiếng Anh sang tiếng Việt **giữ nguyên bố cục trang**, chạy ngay trong trợ lý AI bạn đang dùng. Không cài Python, không gõ lệnh, không cần khóa API.

- Chữ trong bản dịch là chữ thật: bôi đen, tìm kiếm, sao chép được. Ảnh, bảng, nét vẽ, liên kết giữ nguyên.
- Phông chữ đủ dấu tiếng Việt, cùng số đo bề ngang với Times New Roman, Arial, Courier New, Calibri, nên bản dịch nằm gọn trong khung cũ.
- Xuất 4 kiểu: bản tiếng Việt, song ngữ đối trang, song ngữ hai cột, song ngữ xen đoạn.
- Mỗi lần dịch kèm **phiếu kiểm định**: lỗi phông/mất dấu, đoạn tràn khung, đoạn còn tiếng Anh hoặc lệch số liệu, liên kết, lớp chữ thật.

Trang chủ: https://pdf.huynhanhthuan.com

## Dùng với Claude (Claude.ai, Claude Desktop): khuyên dùng

1. Tải file `pdf-translation-layout.zip`.
2. Vào **Customize → Skills → + → Create skill → Upload a skill**, chọn file zip.
3. Kiểm tra **Settings → Capabilities**: bật *Code execution and file creation*.
4. Mở cuộc trò chuyện mới, đính kèm PDF và nhắn: **"Dịch file này sang tiếng Việt, giữ nguyên bố cục"**.

Tài liệu dài, Claude dịch theo từng lô và mời bạn nhắn "tiếp". Tốn lượt dùng trong gói Claude của bạn, không tốn thêm tiền.

## Dùng với ChatGPT

Mở GPT "Dịch PDF giữ bố cục" (đường dẫn trên trang chủ), đính kèm PDF và nhắn như trên. GPT mang sẵn mọi thứ cần thiết trong file kiến thức.

## Dùng với Antigravity

Cài plugin `pdf-translation-layout` (thẻ **Plugins** trong bảng Customizations, hoặc `agy plugin install <thư mục plugin>`), rồi nhắn như trên. Trợ lý tự kiểm tra và cài thư viện, bạn chỉ cần bấm cho phép.

## Dùng với Claude Code hoặc trên máy

Chép thư mục `pdf-translation-layout` vào `~/.claude/skills/` (Claude Code) rồi nhắn như trên. Tự chạy tay: xem các lệnh ở đầu `scripts/dich_pdf.py`.

## Bản quyền nội dung

Bản dịch một tác phẩm là tác phẩm phái sinh. Công cụ này phục vụ **đọc hiểu cá nhân**: mỗi trang có dòng chân trang nhỏ "Bản dịch cá nhân bằng AI · không phân phối". Muốn đăng, chia sẻ công khai hoặc bán bản dịch sách, bài báo có bản quyền, bạn cần sự đồng ý của chủ sở hữu bản quyền.

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

Mã nguồn: MIT (`LICENSE`). Khi chạy dùng PyMuPDF (AGPL-3.0) và phông chữ SIL OFL 1.1: xem `THIRD_PARTY_NOTICES.md`.

Tác giả: Huỳnh Anh Thuận · hello@huynhanhthuan.com
