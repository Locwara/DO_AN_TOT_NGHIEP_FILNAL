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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load test Docker Sandbox")
    parser.add_argument("-c", "--concurrency", type=int, default=10, help="Số lượng tiến trình chạy đồng thời")
    parser.add_argument("-n", "--requests", type=int, default=10, help="Tổng số bài nộp")
    parser.add_argument("-l", "--lang", type=str, default="python", choices=['python', 'cpp', 'java'], help="Ngôn ngữ lập trình")
    args = parser.parse_args()
    
    code = CODE_CPP if args.lang == "cpp" else CODE_PYTHON
    run_benchmark(args.concurrency, args.requests, args.lang, code)
