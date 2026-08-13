import sys
import os
import json

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from services.plagiarism_service import check_plagiarism_batch

# === DATASET GIẢ LẬP ĐỂ TEST ĐẠO VĂN ===

# Nhóm A: Thực sự ĐẠO VĂN của nhau (Chỉ đổi tên biến, thêm khoảng trắng, đổi for thành while)
CODE_A_ORIGINAL = """
def calculate_prime_sum(limit):
    total = 0
    for num in range(2, limit + 1):
        is_prime = True
        for i in range(2, int(num ** 0.5) + 1):
            if num % i == 0:
                is_prime = False
                break
        if is_prime:
            total += num
    return total
"""

CODE_A_PLAGIARIZED_1 = """
def tinh_tong_so_nguyen_to(gioi_han):
    # Khởi tạo tổng
    tong_so = 0
    for n in range(2, gioi_han + 1):
        nguyen_to = True
        for j in range(2, int(n ** 0.5) + 1):
            if n % j == 0:
                nguyen_to = False
                break
        if nguyen_to == True:
            tong_so += n
    return tong_so
"""

CODE_A_PLAGIARIZED_2 = """
def calculate_prime_sum(limit):
    total_val = 0
    # Loop through all numbers
    for number in range(2, limit + 1):
        prime_flag = True
        for j in range(2, int(number ** 0.5) + 1):
            if number % j == 0:
                prime_flag = False
                break
        if prime_flag:
            total_val += number
    return total_val
"""

# Nhóm B: KHÔNG ĐẠO VĂN (Cùng giải quyết một bài toán tương tự nhưng viết theo cách hoàn toàn khác)
CODE_B_INDEPENDENT_1 = """
def get_sum_of_primes(n):
    primes = []
    for i in range(2, n + 1):
        primes.append(i)
    
    p = 2
    while (p * p <= n):
        if p in primes:
            for i in range(p * p, n + 1, p):
                if i in primes:
                    primes.remove(i)
        p += 1
    return sum(primes)
"""

CODE_B_INDEPENDENT_2 = """
import math

def check_prime(number):
    if number < 2: return False
    for i in range(2, math.isqrt(number) + 1):
        if number % i == 0:
            return False
    return True

def prime_sum(n):
    return sum(filter(check_prime, range(2, n + 1)))
"""

submissions = [
    {'id': 1, 'student_id': 'Sinh viên 1 (Bài gốc)', 'code': CODE_A_ORIGINAL},
    {'id': 2, 'student_id': 'Sinh viên 2 (Đạo văn - Đổi tên biến)', 'code': CODE_A_PLAGIARIZED_1},
    {'id': 3, 'student_id': 'Sinh viên 3 (Đạo văn - Đổi for thành while)', 'code': CODE_A_PLAGIARIZED_2},
    {'id': 4, 'student_id': 'Sinh viên 4 (Tự làm - Thuật toán Sàng nguyên tố)', 'code': CODE_B_INDEPENDENT_1},
    {'id': 5, 'student_id': 'Sinh viên 5 (Tự làm - Dùng filter)', 'code': CODE_B_INDEPENDENT_2},
]

# Định nghĩa các cặp thực sự là Đạo Văn (Ground Truth)
actual_plagiarism_pairs = {
    tuple(sorted(['Sinh viên 1 (Bài gốc)', 'Sinh viên 2 (Đạo văn - Đổi tên biến)'])),
    tuple(sorted(['Sinh viên 1 (Bài gốc)', 'Sinh viên 3 (Đạo văn - Đổi for thành while)'])),
    tuple(sorted(['Sinh viên 2 (Đạo văn - Đổi tên biến)', 'Sinh viên 3 (Đạo văn - Đổi for thành while)']))
}

def evaluate():
    print("==========================================")
    print(" BẮT ĐẦU TEST ĐỘ CHÍNH XÁC THUẬT TOÁN ĐẠO VĂN")
    print("==========================================")
    
    # 1. Xuất code của sinh viên ra file để làm minh chứng báo cáo
    code_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'code_sinh_vien')
    os.makedirs(code_dir, exist_ok=True)
    for sub in submissions:
        # Lược bỏ các ký tự không hợp lệ trong tên file
        safe_name = sub['student_id'].replace(" ", "_").replace("(", "").replace(")", "").replace("-", "")
        file_path = os.path.join(code_dir, f"{safe_name}.py")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(sub['code'].strip())
    print(f"[OK] Đã lưu 5 file mã nguồn minh chứng vào thư mục: {code_dir}")

    print("\nĐang quét Winnowing và So khớp cấu trúc AST...")
    
    results = check_plagiarism_batch(submissions, language='python')
    
    tp = fp = fn = tn = 0
    THRESHOLD = 0.80 # Ngưỡng 80% là nghi ngờ đạo văn
    
    print(f"\nKết quả phát hiện các cặp có độ tương đồng >= {THRESHOLD*100}%:")
    
    for r in results:
        pair = tuple(sorted([r['student_a'], r['student_b']]))
        is_actual_plagiarism = pair in actual_plagiarism_pairs
        is_predicted_plagiarism = r['is_suspicious']
        
        if is_predicted_plagiarism:
            print(f"- [Cảnh báo] {pair[0]} & {pair[1]} | Điểm: {r['similarity_score']*100:.1f}%")
        
        if is_actual_plagiarism and is_predicted_plagiarism:
            tp += 1
        elif not is_actual_plagiarism and is_predicted_plagiarism:
            fp += 1
        elif is_actual_plagiarism and not is_predicted_plagiarism:
            fn += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    print("\n==========================================")
    print(" MA TRẬN NHẦM LẪN (CONFUSION MATRIX)")
    print("==========================================")
    print(f"True Positive (Đúng - Có đạo văn)    : {tp}")
    print(f"False Positive (Sai - Báo nhầm)      : {fp} (Dương tính giả)")
    print(f"False Negative (Sai - Bỏ sót)        : {fn} (Âm tính giả)")
    print(f"True Negative (Đúng - Không đạo văn) : {tn}")
    print("------------------------------------------")
    print(f"Precision (Độ chính xác) : {precision*100:.1f}%")
    print(f"Recall (Độ bao phủ)      : {recall*100:.1f}%")
    print(f"F1-Score                 : {f1_score*100:.1f}%")
    print("==========================================")
    
    # Export to Excel (CSV format)
    import csv
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ket_qua')
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, "evaluate_plagiarism.csv")
    with open(filepath, mode='w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Thông số", "Giá trị"])
        writer.writerow(["True Positive (Đúng - Có đạo văn)", tp])
        writer.writerow(["False Positive (Sai - Báo nhầm)", fp])
        writer.writerow(["False Negative (Sai - Bỏ sót)", fn])
        writer.writerow(["True Negative (Đúng - Không đạo văn)", tn])
        writer.writerow(["Precision (Độ chính xác)", f"{precision*100:.1f}%"])
        writer.writerow(["Recall (Độ bao phủ)", f"{recall*100:.1f}%"])
        writer.writerow(["F1-Score", f"{f1_score*100:.1f}%"])
        
        writer.writerow([])
        writer.writerow(["Sinh viên A", "Sinh viên B", "Độ tương đồng (%)", "Máy báo đạo văn", "Thực tế"])
        for r in results:
            pair = tuple(sorted([r['student_a'], r['student_b']]))
            is_actual = "Có" if pair in actual_plagiarism_pairs else "Không"
            is_predicted = "Có" if r['is_suspicious'] else "Không"
            writer.writerow([pair[0], pair[1], f"{r['similarity_score']*100:.1f}%", is_predicted, is_actual])
    print(f"Đã xuất dữ liệu ra file Excel (CSV) tại: {filepath}")
    
if __name__ == "__main__":
    evaluate()
