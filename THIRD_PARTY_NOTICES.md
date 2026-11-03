# Thành phần của bên thứ ba

Mã nguồn và tài liệu do Huỳnh Anh Thuận viết dùng giấy phép MIT (xem `LICENSE`). Khi chạy, gói dùng thêm các thành phần dưới đây, mỗi thành phần giữ giấy phép riêng.

## PyMuPDF (MuPDF), bắt buộc khi chạy

- Giấy phép: **GNU AGPL-3.0**, hoặc giấy phép thương mại của Artifex Software, Inc.
- Trang chủ: https://pymupdf.readthedocs.io · mã nguồn: https://github.com/pymupdf/PyMuPDF
- `scripts/dich_pdf.py` tự cài PyMuPDF từ PyPI khi cần. Bản dành cho ChatGPT đóng kèm sẵn file cài đặt (wheel) PyMuPDF 1.26.0 trong `assets/wheels/` vì môi trường đó thường không ra được mạng.
- Hệ quả: khi phân phối gói này **cùng với** PyMuPDF (như bản ChatGPT), toàn bộ tổ hợp được phân phối theo AGPL-3.0. Mã nguồn đầy đủ của gói được công khai tại kho GitHub của dự án (đường dẫn trên trang pdf.huynhanhthuan.com); ai nhận bản ChatGPT đều có quyền lấy mã nguồn đó. Ai muốn dùng trong sản phẩm đóng mã nguồn để bán cần mua giấy phép thương mại của Artifex hoặc thay thư viện.

## Trang dịch trên web (`web/`)

- Trang tải về trình duyệt **PyMuPDF 1.28.2 bản WebAssembly** (AGPL-3.0, lấy nguyên từ PyPI) và **Pyodide 0.29.5** (Mozilla Public License 2.0, gồm CPython giấy phép PSF).
- Vì phân phối PyMuPDF tới người dùng qua mạng, toàn bộ trang dịch (`web/`) được công khai mã nguồn theo AGPL-3.0 tại kho này. Thông báo chi tiết đi kèm trang: `web/engine/NOTICE.txt`.

## Phông chữ, đóng kèm trong `assets/fonts/`

| Phông | Bản quyền | Giấy phép |
|---|---|---|
| Liberation Serif, Liberation Sans, Liberation Mono (2.x) | © 2010 Google Corporation (Arimo, Tinos, Cousine); © 2012 Red Hat, Inc. | SIL Open Font License 1.1, xem `assets/fonts/LICENSE-Liberation.txt` |
| Carlito | © 2010–2013 tyPoland Łukasz Dziedzic | SIL Open Font License 1.1, xem `assets/fonts/LICENSE-Carlito.txt` |

Các phông này có đủ chữ tiếng Việt và cùng số đo bề ngang với Times New Roman, Arial, Courier New và Calibri, nên bản dịch chiếm chỗ gần như bản gốc. Phông được nhúng (rút gọn) vào PDF kết quả, điều SIL OFL cho phép.

Ghi chú: phần này nhằm minh bạch giấy phép, không phải tư vấn pháp lý.
