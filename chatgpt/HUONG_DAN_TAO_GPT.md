# Tạo GPT "Dịch PDF giữ bố cục" (làm một lần, rồi chia sẻ link cho mọi người)

Cần tài khoản ChatGPT có quyền tạo GPT (Plus trở lên). Người dùng GPT thì gói nào cũng mở được.

## 1. Tạo GPT

1. Vào https://chatgpt.com/gpts/editor → thẻ **Configure**.
2. **Name**: `Dịch PDF giữ bố cục (Anh → Việt)`
3. **Description**: `Gửi PDF tiếng Anh, nhận lại PDF tiếng Việt giữ nguyên trang, kèm bản song ngữ và phiếu kiểm định lỗi dấu. Miễn phí, của pdf.huynhanhthuan.com.`
4. **Instructions**: dán toàn bộ nội dung file `INSTRUCTIONS_GPT.txt`.
5. **Conversation starters** (4 câu):
   - `Dịch file PDF này sang tiếng Việt, giữ nguyên bố cục`
   - `Làm bản song ngữ đối trang cho file này`
   - `Chỉ dịch trang 1–10 của file này`
   - `Kiểm tra lỗi dấu, tràn chữ trong bản dịch PDF của tôi`
6. **Knowledge**: tải lên **một** file `pdf-translation-layout-chatgpt.zip` (đừng giải nén; GPT chỉ giữ được tối đa 10 file trọn đời).
7. **Capabilities**: bật **Code Interpreter & Data Analysis**. Tắt Web Search, Image Generation (không cần).
8. Bấm **Create** → chia sẻ: **Anyone with the link** (hoặc **GPT Store** nếu muốn xuất hiện công khai).

## 2. Thử ngay (bắt buộc trước khi công bố)

1. Mở GPT vừa tạo, đính kèm `mau_6trang.pdf` (có trong bộ thử) và nhắn: `Dịch file này sang tiếng Việt, giữ nguyên bố cục`.
2. Đạt khi: GPT trả về file `..._VI.pdf` và phiếu kiểm định ghi **ĐẠT**, mở PDF thấy chữ tiếng Việt đủ dấu, đúng chỗ.
3. Nếu GPT báo không cài được PyMuPDF hoặc không tạo được file: ghi lại nguyên văn câu báo lỗi và gửi Claude. Khi đó tạm ghi trên website "ChatGPT tạm chưa xuất được PDF, hãy dùng Claude".

## 3. Sau khi chạy được

- Dán link GPT vào `config.js` của website (`GPT_URL`) và vào Apps Script (`CONFIG.GPT_URL`), rồi triển khai lại.
- Mỗi lần có bản mới: thay file trong Knowledge bằng file zip mới (xóa file cũ trước).
