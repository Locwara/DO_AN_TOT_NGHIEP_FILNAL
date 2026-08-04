import sys
import time
from playwright.sync_api import sync_playwright

def run_test(assignment_id):
    print("Starting Playwright End-to-End Test...")
    with sync_playwright() as p:
        # Bật hiển thị trình duyệt bằng cách đặt headless=False, có thể thêm slow_mo để nhìn rõ hơn
        browser = p.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context()
        page = context.new_page()
        
        # Tự động đồng ý khi có popup xác nhận (VD: "Bạn có chắc muốn nộp bài?")
        page.on("dialog", lambda dialog: dialog.accept())

        print("1. Logging in as hs_demo...")
        page.goto('http://127.0.0.1:8000/accounts/login/')
        page.fill('input[name="username"]', 'hs_demo')
        page.fill('input[name="password"]', '123456')
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')
        print("=> Logged in successfully!")

        print(f"2. Navigating to Assignment {assignment_id}...")
        page.goto(f'http://127.0.0.1:8000/submissions/solve/{assignment_id}/')
        page.wait_for_selector('#btn-submit')

        print("3. Injecting python code via Monaco Editor / JS...")
        code = 'print(input())'
        page.evaluate(f"window.editor.setValue(`{code}`)")

        print("4. Submitting code...")
        
        # Đợi request gửi lên server trả về kết quả
        with page.expect_response(lambda response: '/submissions/submit/' in response.url, timeout=15000) as response_info:
            page.click('#btn-submit')
            print("5. Waiting for results from Docker...")
        
        # Đợi UI xử lý xong data từ response (Nút submit được bật lại)
        page.wait_for_selector('#btn-submit:not([disabled])', timeout=5000)
        
        # In ra nội dung kết quả
        result_text = page.inner_text('#ocontent-output')
        print("=> Result found:", result_text)
        
        if "Nộp bài thành công" in result_text or "Thất bại" in result_text or "Hoàn thành" in result_text:
            print("=> Submission completed successfully!")
        else:
            print("=> Hmm, couldn't find expected result text. Might need to check screenshot.")

        # Chụp ảnh màn hình để chứng minh
        page.screenshot(path="test_result.png")
        print("=> Saved screenshot to test_result.png")
        
        # Dừng lại 3 giây để bạn kịp nhìn trước khi đóng web
        page.wait_for_timeout(3000)
        browser.close()
        
        browser.close()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python e2e_test_playwright.py <assignment_id>")
        sys.exit(1)
    run_test(sys.argv[1])
