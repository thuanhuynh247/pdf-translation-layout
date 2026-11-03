# Dịch PDF giữ bố cục (Anh → Việt)

Gửi một file PDF tiếng Anh, nhận lại PDF tiếng Việt giữ nguyên trang: chữ thật (bôi đen, tìm kiếm được), giữ ảnh, bảng, liên kết. Kèm bản song ngữ đối trang, hai cột, xen đoạn và **phiếu kiểm định** (lỗi phông/mất dấu, đoạn tràn khung, đoạn còn tiếng Anh, lệch số liệu).

Chính trợ lý AI trong Antigravity là người dịch. Plugin chỉ mang công cụ tách chữ và ghép bản dịch vào đúng chỗ, nên không cần khóa API riêng.

## Cần có

- Python 3.9 trở lên trên máy (lệnh `python`, `python3` hoặc `py`).
- Thư viện PyMuPDF: lần đầu dùng, trợ lý tự cài bằng `pip`; bạn chỉ cần bấm cho phép chạy lệnh.

## Cài

```bash
agy plugin install ./pdf-translation-layout
agy plugin list
```

Hoặc trong Antigravity: bảng **Customizations → Plugins**, chọn cài từ thư mục đã giải nén.

## Dùng

Mở thư mục có file PDF làm workspace, rồi nhắn: **"Dịch file tai-lieu.pdf sang tiếng Việt, giữ nguyên bố cục"**.

Kết quả nằm cạnh file gốc:

| File | Nội dung |
|---|---|
| `…_VI.pdf` | Bản tiếng Việt, đúng bố cục gốc |
| `…_song-ngu-doi-trang.pdf` | Trang gốc và trang dịch xen kẽ |
| `…_song-ngu-hai-cot.pdf` | Gốc bên trái, dịch bên phải |
| `…_song-ngu-xen-doan.pdf` | Mỗi đoạn gốc kèm bản dịch ngay dưới |
| `…_phieu-kiem-dinh.md` | Kết luận Đạt/Chưa đạt và các đoạn cần xem lại |

Tiến độ dịch lưu trong thư mục `dich_pdf_work/` của workspace; có thể xóa sau khi xong.

## Tài liệu của bạn đi đâu

Trang PDF được tách và dựng lại ngay trên máy bạn. Chỉ phần chữ cần dịch đi tới mô hình AI bạn đang dùng trong Antigravity, theo chính sách của nhà cung cấp đó. Tác giả plugin không nhận, không lưu gì.

## Bản quyền nội dung

Bản dịch phục vụ đọc hiểu cá nhân; mỗi trang có dòng chân trang nhỏ "Bản dịch cá nhân bằng AI · không phân phối". Muốn đăng, chia sẻ công khai hoặc bán bản dịch sách, bài báo có bản quyền, bạn cần sự đồng ý của chủ sở hữu bản quyền.

## Giới hạn

- PDF scan (trang là ảnh chụp) chưa dịch được.
- Chữ nằm trong ảnh, biểu đồ dạng ảnh giữ nguyên tiếng Anh.

Mã nguồn MIT · dùng PyMuPDF (AGPL-3.0) và phông SIL OFL 1.1, xem `THIRD_PARTY_NOTICES.md`.
Trang chủ: https://pdf.huynhanhthuan.com · Tác giả: Huỳnh Anh Thuận
