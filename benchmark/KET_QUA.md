# Kết quả đo · 02/11/2026

Đo theo `GIAO_THUC_DO.md`. Số liệu gốc: `ket_qua_2026-11-02.csv`. File mẫu tạo bằng `mau/tao_pdf_mau.py --pages 6 | 60 | 150`.

- Công cụ: pdf-translation-layout 3.1.0, chạy bằng `chay_mau.py` với bản dịch tham chiếu (tác giả dịch tay), nên đây là kết quả **phần dựng trang**, không phải chất lượng văn dịch của một mô hình AI cụ thể.
- Môi trường: máy ảo Linux x86_64, 2 nhân. Chạy lại trên PyMuPDF 2.0 và 1.26.0 cho kết quả chỉ số giống hệt nhau.
- Đối chiếu: "Đường cơ sở" là cách thay chữ thô bằng phông Helvetica có sẵn (xem `duong_co_so.py`), cùng bản dịch, cùng vị trí. Không phải sản phẩm của bên nào.

## mau_6trang.pdf (6 trang, 11 liên kết)

| Chỉ số | pdf-translation-layout 3.1 | Đường cơ sở |
|---|---|---|
| Ký tự lỗi phông, mất dấu | **0** | 384 |
| Tỷ lệ từ có dấu | **0,85** | 0,22 |
| Từ tiếng Anh còn sót | 0 | 0 |
| Liên kết giữ lại | **11/11** | 2/11 |
| Trang mất lớp chữ thật | 0 | 0 |
| Cặp dòng đè nhau | 0 | 0 |
| Độ trùng bố cục | 0,87 | 0,91 |
| Dung lượng | 0,22 MB | 0,14 MB |

## mau_60trang.pdf và mau_150trang.pdf (tài liệu dài)

| Chỉ số | 3.1 · 60 trang | Đường cơ sở · 60 trang | 3.1 · 150 trang | Đường cơ sở · 150 trang |
|---|---|---|---|---|
| Ký tự lỗi phông, mất dấu | **0** | 4.039 | **0** | 10.087 |
| Tỷ lệ từ có dấu | **0,85** | 0,22 | **0,85** | 0,22 |
| Liên kết giữ lại | **76/76** | 2/76 | **184/184** | 2/184 |
| Trang mất lớp chữ thật | 0 | 0 | 0 | 0 |
| Cặp dòng đè nhau | 0 | 0 | 0 | 0 |
| Độ trùng bố cục | 0,87 | 0,90 | 0,87 | 0,90 |
| Dung lượng bản tiếng Việt | 0,31 MB | 0,18 MB | 0,43 MB | 0,26 MB |

Thời gian chạy trọn quy trình (tách đoạn, nạp bản dịch, dựng 4 kiểu PDF, kiểm định, chấm điểm) trên máy ảo 2 nhân: 60 trang khoảng 15 giây; 150 trang khoảng 32 giây với PyMuPDF 2.0 và 62 giây với PyMuPDF 1.26 (bản đóng kèm cho ChatGPT). Riêng bước dựng bản tiếng Việt 150 trang trên PyMuPDF 1.26 mất khoảng 34 giây, nên với ChatGPT nên dựng từng chế độ một.

Thời gian dựng không gồm thời gian AI dịch. Trên Claude.ai hay ChatGPT, phần dịch chiếm phần lớn thời gian và phụ thuộc gói dịch vụ.

## Đọc kết quả cho đúng

- Đường cơ sở có độ trùng bố cục cao hơn một chút vì nó ép chữ vào đúng khung cũ bằng cách thu nhỏ cỡ chữ, còn pdf-translation-layout cho phép đoạn dịch giãn sang khoảng trống bên cạnh để giữ cỡ chữ, và có thêm dòng chân trang. Đổi lại, đường cơ sở làm hỏng 384 ký tự trên 6 trang: người đọc thấy "Ch??ng 2. L?p m?t ngân sách".
- Phiếu kiểm định của pdf-translation-layout trên cả ba mẫu: **ĐẠT** (0 đoạn tràn khung, 0 đoạn phải thu nhỏ dưới 80%).

## Chưa đo

- Công cụ dịch tài liệu khác (Google Dịch, DeepL, Doctranslate.io, Immersive Translate…): chưa đo. Xem mục 3 và mục 6 của giao thức trước khi đo và công bố.
- Chất lượng văn dịch thật của Claude, ChatGPT khi chạy công cụ: chưa chấm theo mục 5.
- Tài liệu thật ngoài bộ mẫu tự tạo: chưa đo.
