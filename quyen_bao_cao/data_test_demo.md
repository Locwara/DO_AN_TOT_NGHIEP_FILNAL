# Dữ liệu Test Demo Báo Cáo Đồ Án
*(Dùng để copy/paste nhanh trong lúc quay video demo - Phần 2: Thiết lập không gian giảng dạy)*

## 1. Tạo Môn học mới
*Mục đích: Thể hiện hệ thống quản lý môn học rõ ràng, cho phép chọn ngôn ngữ lập trình cho môn học.*

**Data nhập vào Form:**
- **Mã môn học (Code):** `IT1001`
- **Tên môn học:** `Nhập môn Lập trình Python`
- **Mô tả (Description):** `Môn học cung cấp các kiến thức nền tảng về tư duy lập trình và cú pháp cơ bản của ngôn ngữ Python.`
- **Ngôn ngữ hỗ trợ (Languages):** Tích chọn `Python` (và có thể chọn thêm ngôn ngữ khác nếu hệ thống có sẵn).

*Lưu ý quay video: Nếu hệ thống có quy trình duyệt môn học (Pending -> Approved), hãy nhớ dùng tài khoản Admin để duyệt môn học này trước, hoặc nhắc khéo trong video là "Môn học sau khi tạo đã được admin phê duyệt".*

---

## 2. Tạo Lớp học mới
*Mục đích: Thể hiện khả năng tổ chức lớp học, giới hạn sinh viên và gán môn học vào lớp.*

**Data nhập vào Form:**
- **Tên lớp học:** `CQ_IT1001_N01_2025`
- **Mô tả:** `Lớp chính quy nhóm 01 - Học kỳ 1, năm học 2025-2026.`
- **Năm học (School year):** `2025-2026`
- **Học kỳ (Semester):** `Học kỳ 1`
- **Số sinh viên tối đa (Max students):** `60`
- **Mật khẩu lớp (Password - nếu cần demo bảo mật):** *(Để trống hoặc nhập `123456` nếu muốn demo cảnh sinh viên cần pass)*

**Gán Môn Học:**
Sau khi tạo lớp xong, vào phần thiết lập môn học của lớp -> Chọn gán môn **"Nhập môn Lập trình Python (IT1001)"** vừa tạo ở bước 1 vào lớp này.

---

## 3. Import Sinh viên hàng loạt (Tính năng cốt lõi)
*Mục đích: Show cho hội đồng thấy việc áp dụng vào thực tế trường Đại học rất nhàn rỗi cho GV, tự động hóa quản lý user.*

**Kịch bản thực hiện (Action Plan):**
1. Mở sẵn file CSV `sinh_vien_mau.csv` bằng Excel hoặc Notepad trên máy tính. 
   *(Nói vào video hoặc để caption: "Hệ thống hỗ trợ import danh sách sinh viên chuẩn từ phòng đào tạo gồm MSSV, Họ tên, Email, Lớp sinh hoạt...")*
2. Trên website, vào lớp học `CQ_IT1001_N01_2025` -> Chuyển sang Tab **Thành viên** -> Chọn **Import CSV**.
3. Upload file CSV.
4. Bấm Import và chờ hệ thống chạy.
5. **Đọc thoại/Hiển thị kết quả:** *"Hệ thống đã tự động quét danh sách. Đối với sinh viên chưa có tài khoản, hệ thống sẽ tự động khởi tạo bằng MSSV và không làm ảnh hưởng (không ghi đè mật khẩu) đến các sinh viên đã có tài khoản từ trước, sau đó đồng loạt gán tất cả vào lớp học này cực kỳ nhanh chóng."*

**Lưu ý:** Nếu bạn chưa chuẩn bị file CSV, hãy tạo một file `sinh_vien_mau.csv` có nội dung mẫu sau (cột phải đúng với format hệ thống bạn code):
```csv
username,first_name,last_name,email
2211001,Nguyen,Van A,2211001@student.edu.vn
2211002,Tran,Thi B,2211002@student.edu.vn
2211003,Le,Van C,2211003@student.edu.vn
```
*(Bạn điều chỉnh header file CSV ở trên khớp với quy định code của bạn nếu cần nhé).*

---

## 4. Tạo Bài tập Lập trình (Phần 3)
*Mục đích: Thể hiện tính năng gán bài tập đa ngôn ngữ (Python, JavaScript...) và thiết lập mã nguồn khởi tạo / code mẫu.*

**1/4: Thông tin cơ bản**
- **Tên bài tập:** `Tính tổng 2 số nguyên A và B`
- **Môn học (trong lớp):** Chọn `Nhập môn Lập trình Python`
- **Độ khó:** `Dễ` (hoặc `1` sao)
- **Điểm tối đa:** `100`

**2/4: Hình thức & Yêu cầu**
- **Hình thức làm bài:** Chọn `code Lập trình`
- **Cách chấm điểm:** *(Để mặc định)*

**3/4: Nội dung & Đề bài**
- **Mô tả ngắn:** `Bài tập làm quen với nhập xuất trong Python`
- **Nội dung đề bài chi tiết (Markdown):** 
```markdown
Viết chương trình nhập vào 2 số nguyên dương $A$ và $B$ (mỗi số trên 1 dòng hoặc cách nhau bởi khoảng trắng). 
Hãy tính và in ra màn hình tổng của 2 số đó.

**Giới hạn:**
$1 \le A, B \le 10^5$
```
- **Ngôn ngữ cho phép:** Tích chọn `Python` (và có thể thêm `JavaScript` hoặc `C++` để demo tính năng đa ngôn ngữ).

- **Mã nguồn khởi tạo (Python):**
```python
def main():
    # Viết mã nguồn của bạn ở đây
    pass

if __name__ == '__main__':
    main()
```

- **Mã nguồn mẫu (Python):**
```python
def main():
    a, b = map(int, input().split())
    print(a + b)

if __name__ == '__main__':
    main()
```

- **Danh sách Testcase (Thêm 2-3 testcase):**
  - **Test mẫu 1 (Được tích chọn "Test mẫu"):** 
    - Input: `1 2`
    - Output: `3`
  - **Test ẩn 1 (Không tích chọn "Test mẫu"):** 
    - Input: `100 250`
    - Output: `350`
  - **Test ẩn 2 (Không tích chọn "Test mẫu"):** 
    - Input: `99999 1`
    - Output: `100000`

**4/4: Chính sách & Thời gian**
- **Ngày bắt đầu:** *(Chọn ngày giờ hiện tại hoặc để trống nếu hệ thống cho phép)*
- **Hạn nộp:** *(Chọn ngày giờ của tuần sau)*
- **Số lần nộp tối đa:** `5` (Để demo việc giới hạn số lần nộp, chống spam server)
- **Cách tính điểm tổng kết:** `Điểm cao nhất`
- **Cho phép nộp muộn (trừ điểm):** *(Bỏ trống)*
- **Kích hoạt chế độ thi:** *(Bỏ trống)*

## 5. Tạo Bài tập Trắc nghiệm (Quiz)
*Mục đích: Thể hiện tính năng tạo bài thi trắc nghiệm và import câu hỏi hàng loạt từ file Docx/Excel.*

**1/4: Thông tin cơ bản**
- **Tên bài tập:** `Trắc nghiệm ôn tập Python cơ bản`
- **Môn học (trong lớp):** Chọn `Nhập môn Lập trình Python`
- **Độ khó:** `Trung bình`
- **Điểm tối đa:** `10` (Hệ thống sẽ tự chia đều điểm cho các câu)

**2/4: Hình thức & Yêu cầu**
- **Hình thức làm bài:** Chọn `quiz Trắc nghiệm`
- **Cách chấm điểm:** Chọn `Tự động`
- **Cấu hình trắc nghiệm:**
  - Tích chọn: `Đảo câu hỏi`, `Đảo đáp án`, `Hiện điểm ngay`
  - (Các tùy chọn "Hiện đáp án đúng", "Hiện giải thích", "Cho xem lại bài" có thể để trống hoặc tích tùy ý)
  - **Thời gian làm bài (phút):** `15`

**3/4: Nội dung & Đề bài**
- **Mô tả ngắn:** `Kiểm tra kiến thức cơ bản về ngôn ngữ lập trình Python.`
- **Nội dung đề bài chi tiết (Markdown):** 
```markdown
Bài kiểm tra gồm 10 câu trắc nghiệm. 
Mỗi câu có duy nhất 1 đáp án đúng. Vui lòng hoàn thành trong thời gian quy định!
```
- **Import câu hỏi trắc nghiệm:**
  - Kéo thả (hoặc click chọn) file `quiz_python_10cau.docx` (đã chuẩn bị sẵn) vào ô upload. 
  - *Lưu ý khi quay video: Giải thích rằng file chứa 10 câu hỏi định dạng chuẩn, hệ thống sẽ tự động bóc tách câu hỏi, đáp án và giải thích.*

**4/4: Chính sách & Thời gian**
- **Kích hoạt chế độ thi:** (Không tích nếu chỉ là ôn tập, hoặc tích vào để thể hiện chống gian lận Fullscreen).

Bấm **Hoàn tất bài tập** -> **Công bố bài tập**. 
*Kết quả:* Hệ thống báo thành công và import thành công 10 câu hỏi trắc nghiệm từ file.
