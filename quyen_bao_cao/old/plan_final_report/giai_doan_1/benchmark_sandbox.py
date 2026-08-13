import sys
import os
import time
import concurrent.futures
import statistics
import argparse

# Add the project root to sys.path so we can import services
# The script is now in quyen_bao_cao/plan_final_report/giai_doan_1/
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from services.docker_service import execute_code

CODE_PYTHON = """
import time
# Simulate some CPU work
sum(i*i for i in range(10**6))
print("Done")
"""

CODE_CPP = """
#include <iostream>
int main() {
    long long sum = 0;
    for (long long i = 0; i < 10000000; ++i) {
        sum += i * i;
    }
    std::cout << "Done" << std::endl;
    return 0;
}
"""

def run_single(worker_id, code, lang):
    start = time.time()
    try:
        # Run code in Docker Sandbox with 5s timeout, 256MB RAM, 1 CPU core
        result = execute_code(code, language=lang, timeout_seconds=5, memory_limit_mb=256, cpu_limit=1.0)
        end = time.time()
        return {
            'worker_id': worker_id,
            'success': result.success,
            'exit_code': result.exit_code,
            'time_taken': end - start, # Total turnaround time including Docker boot
            'sandbox_time': result.execution_time / 1000.0, # Pure execution time inside sandbox
            'memory_mb': result.memory_usage,
            'error': result.stderr
        }
    except Exception as e:
        end = time.time()
        return {
            'worker_id': worker_id,
            'success': False,
            'error': str(e),
            'time_taken': end - start
        }

def run_benchmark(concurrency, total_requests, lang="python", code=CODE_PYTHON):
    print(f"==========================================")
    print(f" BẮT ĐẦU BENCHMARK SANDBOX")
    print(f"==========================================")
    print(f"Ngôn ngữ test     : {lang}")
    print(f"Số lượng worker   : {concurrency} (chạy đồng thời)")
    print(f"Tổng số submission: {total_requests}")
    print(f"Đang tiến hành gửi request... Vui lòng đợi!")
    
    results = []
    start_total = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(run_single, i, code, lang) for i in range(total_requests)]
        for i, f in enumerate(concurrent.futures.as_completed(futures)):
            results.append(f.result())
            print(f"Đã xử lý: {i+1}/{total_requests}", end='\r')
            
    end_total = time.time()
    
    # Process results
    successful = [r for r in results if r.get('success')]
    failed = [r for r in results if not r.get('success')]
    
    response_times = [r['time_taken'] for r in results]
    
    avg_time = statistics.mean(response_times) if response_times else 0
    max_time = max(response_times) if response_times else 0
    min_time = min(response_times) if response_times else 0
    
    print("\n\n==========================================")
    print(" KẾT QUẢ BENCHMARK (ĐỂ GHI VÀO BÁO CÁO)")
    print("==========================================")
    print(f"- Tổng thời gian hệ thống xử lý : {end_total - start_total:.2f} giây")
    print(f"- Số submission thành công      : {len(successful)}/{total_requests} ({(len(successful)/total_requests)*100:.1f}%)")
    print(f"- Số submission thất bại/lỗi    : {len(failed)}/{total_requests}")
    if failed:
        print(f"  (Lỗi phổ biến: {failed[0].get('error', 'Unknown')})")
    print(f"------------------------------------------")
    print(f"- Thời gian phản hồi trung bình : {avg_time:.2f} giây/submission")
    print(f"- Thời gian phản hồi lâu nhất   : {max_time:.2f} giây/submission")
    print(f"- Thời gian phản hồi nhanh nhất : {min_time:.2f} giây/submission")
    print("==========================================")
    
    # Export to Excel (CSV format)
    import csv
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ket_qua')
    os.makedirs(output_dir, exist_ok=True)
    filename = f"benchmark_sandbox_{total_requests}req_{lang}.csv"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, mode='w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Thông số", "Giá trị"])
        writer.writerow(["Ngôn ngữ", lang])
        writer.writerow(["Số lượng worker", concurrency])
        writer.writerow(["Tổng số bài nộp", total_requests])
        writer.writerow(["Tổng thời gian xử lý (giây)", f"{end_total - start_total:.2f}"])
        writer.writerow(["Số bài nộp thành công", len(successful)])
        writer.writerow(["Tỷ lệ thành công (%)", f"{(len(successful)/total_requests)*100:.1f}%"])
        writer.writerow(["Thời gian phản hồi TB (giây)", f"{avg_time:.2f}"])
        writer.writerow(["Thời gian phản hồi lớn nhất (giây)", f"{max_time:.2f}"])
        writer.writerow(["Thời gian phản hồi nhỏ nhất (giây)", f"{min_time:.2f}"])
        
        writer.writerow([])
        writer.writerow(["Worker ID", "Trạng thái", "Thời gian phản hồi (s)", "Thời gian Sandbox (s)", "Bộ nhớ (MB)"])
        for r in results:
            writer.writerow([r.get('worker_id'), 'Success' if r.get('success') else 'Failed', f"{r.get('time_taken', 0):.2f}", f"{r.get('sandbox_time', 0):.2f}", f"{r.get('memory_mb', 0):.2f}"])
    print(f"Đã xuất dữ liệu ra file Excel (CSV) tại: {filepath}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load test Docker Sandbox")
    parser.add_argument("-c", "--concurrency", type=int, default=10, help="Số lượng tiến trình chạy đồng thời")
    parser.add_argument("-n", "--requests", type=int, default=10, help="Tổng số bài nộp")
    parser.add_argument("-l", "--lang", type=str, default="python", choices=['python', 'cpp', 'java'], help="Ngôn ngữ lập trình")
    args = parser.parse_args()
    
    code = CODE_CPP if args.lang == "cpp" else CODE_PYTHON
    run_benchmark(args.concurrency, args.requests, args.lang, code)
