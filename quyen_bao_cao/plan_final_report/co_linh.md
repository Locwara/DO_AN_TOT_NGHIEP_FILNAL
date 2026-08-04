Toàn bộ mục 1.7 (giới thiệu công nghệ Django, Docker, Monaco, Winnowing, Python, HTML/CSS/JS, Bootstrap, Supabase, Cloudinary, AJAX) sao chép gần như nguyên văn từ các trang web nguồn.
Viết lại toàn bộ bằng lời văn kèm trích dẫn tài liệu tham khảo.
Tại sao Django, không phải Flask/FastAPI/Spring Boot/Node.js Express?
Tại sao Supabase (PostgreSQL managed), không phải MySQL/MongoDB/Firebase tự triển khai?
Tại sao Winnowing, không phải MOSS hay thuật toán so khớp cây cú pháp trừu tượng khác (ví dụ Tree edit distance)?
Không có bất kỳ trích dẫn trong-văn-bản nào dù danh mục Tài liệu tham khảo có 13 mục
Nguồn tài liệu tham khảo cũng bất ổn nữa
phần lớn là blog phổ thông (vietnix.vn, topdev.vn), trang tài liệu sản phẩm thương mại (Supabase, Cloudinary docs), và Wikipedia
nên là các bài báo hoặc giáo trình chẳng hạn
cần ít nhất vài công trình nghiên cứu liên quan (ví dụ về hệ thống chấm bài tự động trong giáo dục - online judge systems, hoặc các thuật toán phát hiện đạo văn mã nguồn khác như MOSS, JPlag để so sánh với lựa chọn Winnowing)
các hệ thống đã tồn tại và tương tự (Moodle, HackerRank, Codeforces, Judge0, DOMjudge, LeetCode, Google Classroom + kết hợp online judge...) Ví dụ giảng viên phản biện hỏi: "Đề tài này khác gì so với các nền tảng đã có sẵn? Tại sao không dùng Judge0 (mã nguồn mở, có sẵn engine chấm bài) mà phải tự viết sandbox từ đầu?"... nên cẩn thận phải tìm hiểu nha
Lý do chọn đề tài, mục tiêu, đối tượng, phạm vi, ý nghĩa: viết đủ nhưng mang tính liệt kê chung chung, không có số liệu thực tế minh chứng cho "cấp thiết" của đề tài (ví dụ: không có thống kê về số giờ giảng viên tốn cho việc chấm bài thủ công, không có khảo sát thực tế bao nhiêu sinh viên gặp khó khăn với việc cài đặt môi trường lập trình). Số liệu phải lấy từ các nguồn uy tín nhe
Định dạng bảng không nhất quán ( kiểm tra từ bảng 2.1 về sau
Nếu dc bổ sung thêm Sequence Diagram để mô tả tương tác giữa các thành phần theo thời gian. nộp bài → gửi vào Sandbox → biên dịch → đối chiếu Testcase → trả điểm; hoặc luồng quét đạo văn chéo hàng loạt bài nộp
Phương pháp nghiên cứu "top-down" được nêu tên nhưng không giải thích rõ vì sao chọn mô hình này thay vì mô hình phát triển phần mềm lặp (Agile/Scrum)
Mục 2.1 cam kết: kiểm thử "xử lý các lỗi biên dịch, vượt quá thời gian, tràn bộ nhớ", "tính chính xác của thuật toán quét tỷ lệ đạo văn", và đánh giá "tốc độ xử lý của Sandbox khi có nhiều lượt nộp bài đồng thời". Nhưng Chương 3 chỉ trình bày 29 hình chụp màn hình giao diện kèm mô tả tính năng (mục 3.1) hoàn toàn không có số liệu định lượng nào để chứng minh:
1/ Bao nhiêu testcase đã chạy, tỷ lệ pass/fail thực tế?
2/ Thời gian phản hồi trung bình của Sandbox khi có N submission đồng thời (benchmark)?
3/ Độ chính xác (Precision/Recall) của thuật toán Winnowing khi test trên bộ dữ liệu bài nộp thật - có bao nhiêu trường hợp dương tính giả (false positive) khi hai sinh viên viết code tương tự nhưng không đạo văn?
4/ Có khảo sát người dùng thật (giảng viên/sinh viên dùng thử) để đánh giá UX không?
