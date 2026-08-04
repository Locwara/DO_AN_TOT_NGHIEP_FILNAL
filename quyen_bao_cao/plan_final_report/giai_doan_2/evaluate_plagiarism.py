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
    {'id': 1, 'student_id': 'sv1_original', 'code': CODE_A_ORIGINAL},
    {'id': 2, 'student_id': 'sv2_plagiarized_var_names', 'code': CODE_A_PLAGIARIZED_1},
    {'id': 3, 'student_id': 'sv3_plagiarized_while_loop', 'code': CODE_A_PLAGIARIZED_2},
    {'id': 4, 'student_id': 'sv4_independent_sieve', 'code': CODE_B_INDEPENDENT_1},
    {'id': 5, 'student_id': 'sv5_independent_filter', 'code': CODE_B_INDEPENDENT_2},
]

# Định nghĩa các cặp thực sự là Đạo Văn (Ground Truth)
actual_plagiarism_pairs = {
    ('sv1_original', 'sv2_plagiarized_var_names'),
    ('sv1_original', 'sv3_plagiarized_while_loop'),
    ('sv2_plagiarized_var_names', 'sv3_plagiarized_while_loop')
}

def evaluate():
    print("==========================================")
    print(" BẮT ĐẦU TEST ĐỘ CHÍNH XÁC THUẬT TOÁN ĐẠO VĂN")
    print("==========================================")
    print("Đang quét Winnowing và So khớp cấu trúc AST...")
    
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
    
if __name__ == "__main__":
    evaluate()
