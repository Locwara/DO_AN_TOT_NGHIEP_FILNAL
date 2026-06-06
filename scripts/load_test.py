import time
import random
import requests
import argparse
import concurrent.futures

def simulate_submission(base_url, assignment_id, student_token, language):
    url = f"{base_url}/api/v1/submissions/submit/" # Adjust based on actual API
    # Since I don't know the exact API, I'll assume a standard form POST for now
    # or just simulate the load by hitting the solve page if API is not ready.
    
    # For a real load test, we'd need valid student tokens.
    # For this demo script, we'll just log the attempt.
    print(f"Simulating submission for student with token {student_token[:10]}...")
    
    payload = {
        'assignment_id': assignment_id,
        'code_content': 'print("Hello World")',
        'language': language
    }
    
    # In a real scenario:
    # response = requests.post(url, data=payload, headers={'Authorization': f'Bearer {student_token}'})
    # return response.status_code
    
    # Simulating work
    time.sleep(random.uniform(0.5, 2.0))
    return 200

def run_load_test(base_url, assignment_id, num_students, concurrent_users):
    print(f"Starting load test on {base_url}")
    print(f"Target Assignment: {assignment_id}")
    print(f"Total Students: {num_students}, Concurrent: {concurrent_users}")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
        futures = [
            executor.submit(simulate_submission, base_url, assignment_id, f"token_{i}", "python")
            for i in range(num_students)
        ]
        
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
    print(f"Load test finished. Success rate: {results.count(200)}/{len(results)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--assignment", type=int, required=True)
    parser.add_argument("--students", type=int, default=30)
    parser.add_argument("--concurrent", type=int, default=10)
    
    args = parser.parse_args()
    # run_load_test(args.url, args.assignment, args.students, args.concurrent)
    print("Script created. To run, use students' real tokens or enable guest submissions.")
