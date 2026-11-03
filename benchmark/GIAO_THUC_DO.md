# Giao thức đo chất lượng PDF dịch tiếng Việt

Mục tiêu: đo **phần kỹ thuật** của một file PDF đã dịch sang tiếng Việt (dấu có hiển thị đúng không, chữ có nằm đúng chỗ không, còn là chữ thật không, liên kết còn không). Bộ đo chạy được với PDF của **bất kỳ công cụ nào**, không chỉ pdf-translation-layout.

Bộ đo **không** chấm văn dịch hay hay dở. Phần đó cần người đọc chấm (mục 5).

## 1. Bộ chấm

Nằm trong `skills/pdf-translation-layout/scripts/dich_pdf.py`, lệnh `cham-diem`. Cần Python 3.9+ và PyMuPDF.

```bash
python skills/pdf-translation-layout/scripts/dich_pdf.py cham-diem \
    --goc  mau_6trang.pdf \
    --dich "google-dich__mau_6trang.pdf" \
    --ten  "Google Dịch (tài liệu)" \
    --csv  ket_qua.csv
```

Mỗi lần chạy in kết quả ra màn hình và thêm một dòng vào `ket_qua.csv`.

| Cột | Đo gì | Tốt khi |
|---|---|---|
| `so_trang` | Số trang bản dịch / bản gốc | Bằng nhau (với bản đơn ngữ) |
| `ky_tu_loi_phong` | Ký tự người đọc thấy là ô vuông hoặc mất dấu: glyph rỗng (.notdef) của phông nhúng, ký tự thay thế U+FFFD/□, dấu `?` `·` chen giữa một từ | 0 |
| `ty_le_tu_co_dau` | Tỷ lệ từ có dấu tiếng Việt trong toàn bộ chữ của bản dịch | Văn bản mẫu của dự án đạt 0,85. Dưới 0,5 là dấu hiệu mất dấu (ngưỡng tham khảo, chưa kiểm chứng trên nhiều thể loại) |
| `ty_le_tu_tieng_anh_con_lai` | Tỷ lệ từ thuộc danh sách từ chức năng tiếng Anh thông dụng (the, and, of…) còn sót | Gần 0 |
| `lien_ket` | Liên kết còn lại / liên kết gốc | Bằng nhau |
| `trang_mat_lop_chu` | Trang gốc có chữ nhưng bản dịch không còn chữ thật (bị biến thành ảnh, không bôi đen, không tìm kiếm được) | 0 |
| `cap_dong_chong_nhau` | Cặp dòng chữ đè lên nhau quá 25% diện tích | 0 |
| `do_trung_bo_cuc` | Chia mỗi trang thành lưới 24×32 ô, đánh dấu ô có chữ ở bản gốc và bản dịch, lấy chỉ số Jaccard trung bình | Càng gần 1 càng sát bố cục gốc |
| `dung_luong_mb` | Dung lượng file | Không phình bất thường |
| `so_tu` | Số từ đọc được trong bản dịch | Để đối chiếu |

Cách đọc `do_trung_bo_cuc`: chỉ số này chỉ nói chữ có nằm ở những vùng chữ gốc chiếm hay không. Một bản dịch giữ đúng khung nhưng mất hết dấu vẫn có thể đạt cao, nên **luôn đọc cùng `ky_tu_loi_phong` và `ty_le_tu_co_dau`**. Dòng chân trang "Bản dịch cá nhân bằng AI" của pdf-translation-layout làm chỉ số này giảm nhẹ.

## 2. Bộ tài liệu mẫu

| File | Nội dung | Ghi chú |
|---|---|---|
| `mau/mau_6trang.pdf` | 6 bố cục: trang bìa, 2 cột, danh sách, bảng, biểu đồ ảnh, hộp tô nền, chú thích, liên kết | Tác giả tự viết, CC0 |
| `mau_60trang.pdf` | Lặp 6 bố cục trên thành 60 trang, thử tài liệu dài | Tạo bằng `python mau/tao_pdf_mau.py --pages 60 --out mau_60trang.pdf` |
| `mau_150trang.pdf` | Lặp thành 150 trang, thử giới hạn lượt dùng của gói AI | `python mau/tao_pdf_mau.py --pages 150 --out mau_150trang.pdf` |

Bộ mẫu do chính tác giả công cụ tạo, nên có thiên lệch. Khi công bố so sánh, nên thêm 2–3 tài liệu **thật, có giấy phép cho phép dịch và đăng lại** (ví dụ tài liệu thuộc phạm vi công cộng, hoặc giấy phép CC BY), mỗi loại một bố cục: bài báo khoa học 2 cột, báo cáo có nhiều bảng, sách hướng dẫn có hình. Ghi rõ nguồn và giấy phép của từng file.

## 3. Đo một công cụ khác

1. Dùng đúng file mẫu gốc, không sửa.
2. Dịch bằng công cụ cần đo theo cách người dùng bình thường vẫn làm (giao diện web, gói miễn phí hoặc gói đang dùng). Không chỉnh tay file kết quả.
3. Đặt tên file kết quả theo mẫu `<cong-cu>__<tai-lieu>.pdf`, ví dụ `deepl__mau_6trang.pdf`.
4. Ghi vào sổ đo: ngày đo, gói dịch vụ (miễn phí/trả phí), phiên bản hoặc ngày cập nhật nếu thấy, giới hạn gặp phải (số trang, dung lượng, phải đăng nhập, có chèn quảng cáo hay hình mờ không).
5. Chạy `cham-diem` cho từng file, gom vào cùng một `ket_qua.csv`.
6. Mở từng file xem bằng mắt ít nhất 3 trang (trang bìa, trang bảng, trang 2 cột) và chụp màn hình cùng một vùng để đối chiếu.
7. Lưu cả file kết quả gốc của công cụ đó để người khác kiểm lại được.

Công cụ thường được người Việt dùng để dịch PDF, nên đo khi có điều kiện: Google Dịch (mục Tài liệu), DeepL (dịch tài liệu), Doctranslate.io, Immersive Translate (BabelDOC), và bản dịch trực tiếp bằng ChatGPT/Gemini khi đính kèm PDF.

## 4. Đo pdf-translation-layout

```bash
python benchmark/chay_mau.py benchmark/mau/mau_6trang.pdf --xuat ket_qua_do --csv ket_qua.csv
```

`chay_mau.py` chạy trọn quy trình với **bản dịch tham chiếu** do tác giả dịch tay (`mau/ban_dich_tham_chieu.json`) thay cho AI, nên con số đo phần dựng trang của công cụ, độc lập với mô hình AI. Khi đo bản dịch thật do Claude hoặc ChatGPT làm, chấm file `_VI.pdf` mà trợ lý trả về bằng `cham-diem` như mục 3.

`duong_co_so.py` dựng một bản đối chiếu theo cách "thay chữ thô" (phông Helvetica có sẵn trong chuẩn PDF, không có chữ Việt), để thấy bộ chấm bắt được lỗi gì. Đó không phải sản phẩm của bên nào.

## 5. Chấm văn dịch (người đọc)

Bộ chấm máy không biết câu dịch có đúng nghĩa không. Khi cần so văn dịch:

- Lấy ngẫu nhiên 20 đoạn trong mỗi tài liệu (cùng 20 đoạn cho mọi công cụ).
- Che tên công cụ, xáo thứ tự.
- 2 người đọc độc lập, biết tiếng Anh, chấm mỗi đoạn hai điểm từ 1 đến 5: **Đúng nghĩa** (không sai, không sót ý) và **Tự nhiên** (đọc như người Việt viết, thuật ngữ nhất quán).
- Báo cáo điểm trung bình và độ lệch giữa hai người chấm. Lệch quá 1 điểm ở đoạn nào thì hai người bàn lại đoạn đó.

## 6. Quy tắc công bố

- Chỉ đăng con số đã đo, kèm ngày đo, gói dịch vụ, file mẫu và file kết quả để người khác kiểm lại.
- Ghi rõ bộ mẫu do tác giả tạo và giới hạn của bộ chấm (mục 1).
- Không dùng logo, ảnh giao diện của sản phẩm khác.
- Không viết "tốt nhất", "số một", "duy nhất".
- **So sánh có nêu tên sản phẩm khác trên trang giới thiệu sản phẩm**: pháp luật Việt Nam về quảng cáo và cạnh tranh có quy định hạn chế quảng cáo so sánh trực tiếp với sản phẩm cùng loại của người khác, và Luật Quảng cáo vừa được sửa đổi năm 2025 (Luật số 75/2025/QH15). Tôi không phải luật sư và chưa đọc được bản đầy đủ của luật sửa đổi. Trước khi đăng bảng so sánh có nêu tên, nên hỏi ý kiến luật sư. Cách an toàn trong lúc chờ: trang công khai chỉ đăng kết quả của chính công cụ này cùng bộ chấm mở, để ai cũng tự chấm được công cụ họ đang dùng.
