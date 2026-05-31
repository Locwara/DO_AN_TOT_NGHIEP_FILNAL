# 📋 Bảng Dữ Liệu Demo Hệ Thống DevLearn (C++)
> Tài liệu tra cứu nhanh dữ liệu để copy-paste trong lúc Demo.

---

## 🏫 1. THIẾT LẬP LỚP HỌC
- **Tên lớp**: `Ngôn ngữ lập trình 2 (C++) - Nhóm 02`
- **Năm học**: `2025-2026` | **Học kỳ**: `Học kỳ 2`
- **Môn học gán**: `Ngôn ngữ lập trình 2` (hoặc `CPP102`)

---

## 📝 2. TẠO BÀI TẬP & ĐỀ THI (VAI GIÁO VIÊN)

### 🟦 A. BÀI TẬP CODE: TÌM SỐ LỚN NHẤT
- **Tên bài**: `Tìm số lớn nhất`
- **Mô tả ngắn**: `Tìm số lớn nhất trong 3 số nguyên.`
- **Đề bài chi tiết**:
```markdown
Viết chương trình nhập vào 3 số nguyên `a`, `b`, `c`. In ra số lớn nhất trong 3 số đó.
Ví dụ: Input: `10 25 7` -> Output: `25`.
```
- **Starter Code**:
```cpp
#include <iostream>
using namespace std;
int main() {
    // Viết code của bạn ở đây
    return 0;
}
```
- **Solution Code**:
```cpp
#include <iostream>
#include <algorithm>
using namespace std;
int main() {
    int a, b, c;
    if (!(cin >> a >> b >> c)) return 0;
    cout << max({a, b, c});
    return 0;
}
```
- **Testcase**: Input: `10 25 7` | Output: `25` (Tích chọn: **Test mẫu**)

---

### 🟪 B. BÀI TẬP QUIZ: C++ CƠ BẢN
- **Tên bài**: `Trắc nghiệm C++ Cơ bản`
- **Mô tả ngắn**: `Kiểm tra kiến thức con trỏ và cú pháp C++.`
- **Nội dung file Word để Import**:
```text
[QUESTION]: Ký tự nào dùng để khai báo một biến con trỏ trong C++?
[TYPE]: single_choice
[A]: &
[B]: #
[C]: *
[D]: @
[CORRECT]: C
[EXPLANATION]: Dấu sao (*) dùng để định nghĩa kiểu dữ liệu con trỏ.
--------------------
[QUESTION]: Lệnh nào dùng để in dữ liệu ra màn hình trong C++?
[TYPE]: single_choice
[A]: cin
[B]: cout
[C]: print
[D]: scanf
[CORRECT]: B
[EXPLANATION]: cout thuộc thư viện iostream dùng để xuất dữ liệu.
```
- **Cấu hình (Bước 4)**: Tích chọn `Hiện đáp án đúng` và `Hiện giải thích`.

---

### 🟩 C. BÀI TẬP FILE: ĐỒ ÁN
- **Tên bài**: `Báo cáo Thực hành C++`
- **Mô tả ngắn**: `Nộp mã nguồn và báo cáo PDF.`
- **Hình thức**: `Nộp file` | Định dạng: `.zip`

---

### 🟥 D. BÀI THI CODE: TỔNG CHẴN
- **Tên bài**: `Thi cuối kỳ - C++ Programming`
- **Mô tả ngắn**: `Tính tổng các số chẵn trong mảng.`
- **Solution Code**:
```cpp
#include <iostream>
using namespace std;
int main() {
    int n, val, sum = 0;
    if (!(cin >> n)) return 0;
    for(int i=0; i<n; i++) {
        cin >> val;
        if(val % 2 == 0) sum += val;
    }
    cout << sum;
    return 0;
}
```
- **Testcase**: Input: `5 1 2 3 4 5` | Output: `6` (Tích chọn: **Test mẫu**)
- **Cấu hình thi**: Tích `Chế độ thi`, `Fullscreen`, Max runs: `10`.

---

## 👨‍🎓 3. NỘP BÀI (VAI HỌC SINH)

- **BT CODE (Tìm Max)**:
```cpp
#include <iostream>
#include <algorithm>
using namespace std;
int main() {
    int a, b, c;
    if (cin >> a >> b >> c) cout << max({a, b, c});
    return 0;
}
```

- **BT QUIZ**: Câu 1 chọn **\*** | Câu 2 chọn **cout**

- **BT FILE**: Upload 1 file `.zip` bất kỳ.

- **THI CODE (Tổng chẵn)**:
```cpp
#include <iostream>
using namespace std;
int main() {
    int n, v, s=0;
    cin >> n;
    while(n--) { cin >> v; if(v%2==0) s+=v; }
    cout << s;
    return 0;
}
```
