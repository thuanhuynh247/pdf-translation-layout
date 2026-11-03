---
name: pdf-translation-layout
description: Dịch file PDF tiếng Anh sang tiếng Việt, hoặc tiếng Việt sang tiếng Anh, mà vẫn giữ nguyên bố cục trang (chữ thật, bôi đen và tìm kiếm được, giữ ảnh, bảng, liên kết), xuất thêm bản song ngữ đối trang, hai cột, xen đoạn và phiếu kiểm định. PDF tiếng Việt dùng phông cũ TCVN3 (.VnTime) hay VNI được tự chuyển sang Unicode. Chính trợ lý AI dịch, không cần khóa API, không cần người dùng gõ lệnh. Dùng khi người dùng gửi PDF và nói "dịch file này", "dịch PDF giữ nguyên định dạng/bố cục", "dịch sang tiếng Việt", "dịch sang tiếng Anh", "dịch hồ sơ năng lực/công văn/khóa luận sang tiếng Anh", "làm bản song ngữ", "translate this PDF to Vietnamese", "translate this Vietnamese PDF to English", "bilingual PDF", hoặc nhờ kiểm tra, chấm chất lượng một PDF đã dịch.
license: MIT (mã nguồn). Khi chạy dùng PyMuPDF (AGPL-3.0) và phông chữ SIL OFL 1.1, xem THIRD_PARTY_NOTICES.md
---

# Dịch PDF Anh ⇄ Việt giữ nguyên bố cục

Bạn (trợ lý AI) là người dịch. Công cụ `scripts/dich_pdf.py` chỉ **tách chữ** ra theo từng đoạn có mã số và **ghép bản dịch** vào đúng chỗ trên trang. Người dùng không phải gõ lệnh nào: bạn tự chạy mọi lệnh dưới đây.

Yêu cầu: chạy được Python 3.9+ (Claude.ai bật "Code execution and file creation"; ChatGPT bật Code Interpreter; Antigravity, Claude Code chạy trên máy). PyMuPDF được tự cài nếu thiếu.

Trong mọi lệnh, `SKILL` là thư mục chứa file này (ví dụ `/mnt/skills/user/pdf-translation-layout` trên Claude.ai). Hãy xác định đường dẫn thật trước khi chạy. Trên Windows, nếu không có lệnh `python` thì dùng `py`.

## Quy trình

**1. Tìm file PDF.** Claude.ai: file người dùng tải lên nằm trong `/mnt/user-data/uploads/`. ChatGPT: `/mnt/data/`. Trên máy: đường dẫn người dùng đưa. Chỉ nhận PDF có chữ thật; PDF scan (ảnh chụp) thì công cụ sẽ báo, hãy nói rõ với người dùng.

**2. Chuẩn bị môi trường** (tự cài PyMuPDF nếu thiếu):
```bash
python SKILL/scripts/dich_pdf.py kiem-tra
```
Nếu báo "KHÔNG CÀI ĐƯỢC", giải thích ngắn cho người dùng bật chạy mã (Claude.ai: Settings → Capabilities → Code execution and file creation) rồi dừng.

**3. Tách đoạn, chia lô** (10–20 trang mỗi lô; tài liệu dày chữ dùng 10):
```bash
python SKILL/scripts/dich_pdf.py chuan-bi "<đường dẫn PDF>" --lo 15
```
Người dùng chỉ muốn dịch vài trang thì thêm `--trang 1-10` (hoặc `--trang "1-5,8"`).

Chiều dịch được tự nhận theo chữ trong tài liệu và in ra ở dòng "Chiều dịch". Nếu người dùng nói rõ chiều (ví dụ "dịch sang tiếng Anh") mà khác với dòng đó, chạy lại với `--huong vi-en` (Việt → Anh) hoặc `--huong en-vi` (Anh → Việt). Báo người dùng một dòng: chiều dịch, số trang, số đoạn, số lô. Nếu công cụ báo đã chuyển mã phông cũ, gắn lại dấu, hoặc có trang chữ hỏng mã, nói thêm một câu.

**4. Dịch từng lô** cho đến khi hết:
```bash
python SKILL/scripts/dich_pdf.py lay-lo
```
Lệnh in ra quy tắc dịch của chiều đang làm (chiều Việt → Anh có quy tắc riêng bằng tiếng Anh, làm đúng theo đó), rồi các dòng JSON `{"id": ..., "text": ...}` giữa `---BẮT ĐẦU---` và `---HẾT---`. Bạn dịch, ghi kết quả ra file JSON dạng `{"p3-4": "bản dịch", ...}` (đủ mọi id, mỗi id một đoạn, không gộp, không tách), rồi nạp:
```bash
python SKILL/scripts/dich_pdf.py nap-lo lo_dich.json
```
Nếu `nap-lo` báo "CẦN XEM LẠI", sửa các đoạn đó và nạp lại. Đoạn lặp lại (đầu trang, chân trang) được điền tự động.

Tài liệu dài: dịch khoảng 2–3 lô mỗi lượt trả lời, báo tiến độ ("đã xong lô 2/6"), rồi mời người dùng nhắn **"tiếp"** để làm tiếp. Tiến độ được lưu trên đĩa; nếu môi trường bị khởi động lại, chạy `tien-do`, và nếu mất dữ liệu thì chạy lại `chuan-bi` rồi tiếp tục.

**5. Dựng PDF:**
```bash
python SKILL/scripts/dich_pdf.py dung --che-do tat-ca
```
Tài liệu trên 80 trang hoặc môi trường giới hạn thời gian mỗi lần chạy: gọi từng chế độ một (`don-ngu` trước, sau đó `doi-trang`, `hai-cot`, `xen-doan`; bản dịch đã dựng được dùng lại). Bản dịch có đuôi `_VI.pdf` hoặc `_EN.pdf` tùy chiều. Các chế độ: `don-ngu` (chỉ bản dịch), `doi-trang` (trang gốc rồi trang dịch xen kẽ), `hai-cot` (gốc trái, dịch phải trên một trang ngang), `xen-doan` (mỗi đoạn gốc kèm bản dịch ngay dưới), `tat-ca`. Mặc định mỗi trang có dòng chân trang nhỏ ("Bản dịch cá nhân bằng AI · không phân phối", bản tiếng Anh ghi "Unofficial AI translation… not a certified translation"); chỉ bỏ (`--khong-chan-trang`) khi người dùng yêu cầu và tài liệu là của họ.

**6. Kiểm định:**
```bash
python SKILL/scripts/dich_pdf.py kiem-dinh
```
Nếu có đoạn tràn khung, nghi vấn hay chưa dịch: dịch lại các đoạn được liệt kê (ngắn gọn hơn nếu tràn khung), `nap-lo`, rồi `dung` và `kiem-dinh` lại. Tối đa 2 vòng sửa.

**7. Giao kết quả.** Claude.ai: file đã nằm trong `/mnt/user-data/outputs/`, hãy trình bày cho người dùng tải. ChatGPT: chạy `dung`/`kiem-dinh` với `--xuat /mnt/data/ket_qua` rồi đưa link tải. Trên máy (Antigravity, Claude Code): chạy `dung`/`kiem-dinh` với `--xuat "<thư mục chứa PDF gốc>"` để file nằm ngay cạnh bản gốc, rồi báo đường dẫn. Trả lời ngắn: tên các file, kết luận phiếu kiểm định (Đạt/Chưa đạt và vì sao), và những gì người dùng nên tự xem lại.

## Chấm một bản dịch có sẵn

Khi người dùng gửi file gốc kèm một PDF đã dịch (của bất kỳ công cụ nào, chiều nào cũng được) và nhờ kiểm tra hoặc chấm:
```bash
python SKILL/scripts/dich_pdf.py cham-diem --goc "<PDF gốc>" --dich "<PDF đã dịch>"
```
Giải thích kết quả bằng lời thường: `ky_tu_loi_phong` (ký tự hiện thành ô vuông hoặc mất dấu, tốt nhất là 0), `ty_le_tu_co_dau` (dưới 0,5 là dấu hiệu mất dấu), `ty_le_tu_tieng_anh_con_lai`; với bản tiếng Anh dịch từ tiếng Việt (`"huong": "vi-en"`) thì thay bằng `ty_le_tu_tieng_viet_con_lai` và `ty_le_tu_tieng_viet_khong_dau` (tốt nhất là 0); `lien_ket` (còn/gốc), `trang_mat_lop_chu` (trang bị biến thành ảnh, không bôi đen được), `cap_dong_chong_nhau`, `do_trung_bo_cuc` (gần 1 là chữ nằm đúng vùng cũ; đọc cùng hai chỉ số về dấu). Không chấm được độ hay của văn dịch; nếu được hỏi, đọc vài đoạn và nhận xét riêng, nói rõ đó là nhận xét của bạn.

## Nguyên tắc dịch Anh → Việt

- Tiếng Việt tự nhiên, **đủ dấu**, đúng văn phong tài liệu (học thuật, kinh doanh, hướng dẫn…). Không dịch kiểu từng chữ.
- Giữ nguyên: số liệu, đơn vị, tên riêng, tên sản phẩm, URL, email, mã, công thức. Số thập phân có thể đổi dấu chấm thành dấu phẩy theo cách viết Việt Nam.
- Thuật ngữ nhất quán suốt tài liệu: khi gặp thuật ngữ chuyên ngành lần đầu, chọn một cách dịch và giữ nguyên ở các lô sau (ghi nhớ trong cuộc trò chuyện).
- Mục danh sách giữ ký hiệu đầu dòng (•, 1., a)…) ở đầu bản dịch. Tiêu đề (`"loai": "tieu-de"`) dịch ngắn gọn.
- Ô bảng biểu và nhãn ngắn: dịch ngắn nhất có thể để vừa khung.
- Không thêm chú thích, không bỏ câu.

## Nguyên tắc dịch Việt → Anh

`lay-lo` in đủ quy tắc. Những điểm dễ sai nhất:

- Tiếng Anh tự nhiên, đúng văn phong (văn bản hành chính, hợp đồng: trang trọng). Đại từ xưng hô (anh, chị, em, chúng tôi) chuyển theo ngữ cảnh; không rõ giới tính thì dùng "they". Câu không chủ ngữ: mệnh lệnh cho hướng dẫn, "we" khi tổ chức tự nói về mình, bị động cho quy định.
- Không đổi số: đổi dấu phân cách sang kiểu Anh mà giữ giá trị (1.000.000 → 1,000,000; 3,5% → 3.5%). Ngày dạng số giữ nguyên (03/02/2020), không đảo ngày tháng. Số hiệu văn bản giữ đúng (15/2020/NĐ-CP).
- Tên cơ quan, chức danh theo Thông tư 05/2026/TT-BNG của Bộ Ngoại giao (Ủy ban nhân dân = People's Committee, Sở = Department…). Tên người giữ thứ tự họ trước, bỏ dấu (Nguyen Van An); địa danh bỏ dấu kèm loại (Nghe An Province). Không tự đổi địa danh cũ theo bản đồ hành chính sau năm 2025.
- Đoạn đã là tiếng Anh, mã, số: để nguyên.

## Bản quyền và quyền riêng tư

- Bản dịch tác phẩm của người khác là tác phẩm phái sinh. Dịch để tự đọc, tự học là phù hợp; nếu người dùng nói muốn **đăng, chia sẻ công khai hoặc bán** bản dịch sách, bài báo có bản quyền, hãy nhắc một câu rằng cần sự đồng ý của chủ sở hữu bản quyền, rồi vẫn làm phần dịch cho mục đích cá nhân.
- File chỉ được xử lý trong môi trường của trợ lý AI người dùng đang dùng; tác giả công cụ không nhận được gì.

## Giới hạn cần nói thật với người dùng

- PDF scan (trang là ảnh) không dịch được bằng công cụ này.
- Chữ nằm trong ảnh, biểu đồ dạng ảnh, con dấu và chữ ký giữ nguyên như bản gốc.
- Bản tiếng Anh là bản nháp để đọc và tự kiểm, không phải bản dịch có chứng thực. Học bạ, bằng cấp, giấy tờ hộ tịch, hồ sơ thị thực hay giấy tờ nộp cơ quan nhà nước vẫn cần người dịch ký và được chứng thực; nói rõ điều này khi người dùng dịch loại giấy tờ đó.
- Phông chữ được thay bằng phông cùng kích thước có đủ dấu tiếng Việt (Liberation Serif/Sans/Mono, Carlito), nên kiểu chữ có thể khác bản gốc đôi chút.
- Mỗi file tải về trên Claude.ai tối đa 30 MB; nếu bản song ngữ quá lớn, đề nghị chỉ xuất `don-ngu` hoặc chia tài liệu.
