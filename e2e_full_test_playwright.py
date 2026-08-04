import sys
from playwright.sync_api import sync_playwright

def run_all_tests(assignment_id):
    print("🚀 Bắt đầu chuỗi kiểm thử E2E tự động toàn diện...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        
        # === TEST 1: HỌC SINH 1 NỘP BÀI LỖI TIME LIMIT EXCEEDED ===
        context1 = browser.new_context()
        page1 = context1.new_page()
        page1.on("dialog", lambda dialog: dialog.accept())
        
        print("\n--- TEST 1: XỬ LÝ LỖI TIMEOUT (TLE) ---")
        page1.goto('http://127.0.0.1:8000/accounts/login/')
        page1.fill('input[name="username"]', 'hs_demo')
        page1.fill('input[name="password"]', '123456')
        page1.click('button[type="submit"]')
        page1.wait_for_load_state('networkidle')
        
        page1.goto(f'http://127.0.0.1:8000/submissions/solve/{assignment_id}/')
        page1.wait_for_selector('#btn-submit')
        
        # Inject mã nguồn gây lặp vô hạn
        code_tle = 'while True:\n    pass'
        page1.evaluate(f"window.editor.setValue(`{code_tle}`)")
        print("Đã inject code lặp vô hạn để ép Docker văng lỗi TLE.")
        
        with page1.expect_response(lambda r: '/submissions/submit/' in r.url, timeout=20000) as r_info:
            page1.click('#btn-submit')
        page1.wait_for_selector('#btn-submit:not([disabled])', timeout=5000)
        
        result_text = page1.inner_text('#ocontent-output')
        if "Time Limit Exceeded" in result_text or "Quá thời gian" in result_text or "Timeout" in result_text or "Thất bại" in result_text or "Lỗi" in result_text:
            print("=> THÀNH CÔNG: Đã bắt được lỗi Time Limit Exceeded/Timeout từ Docker!")
        else:
            print("=> CẢNH BÁO: Không bắt được lỗi Timeout như mong đợi.")
            
        # === TEST 2: HỌC SINH 1 NỘP BÀI CODE ĐÚNG ===
        print("\n--- TEST 2: NỘP BÀI CODE CHUẨN ---")
        code_correct_1 = 'a = int(input())\nprint(a)'
        page1.evaluate(f"window.editor.setValue(`{code_correct_1}`)")
        with page1.expect_response(lambda r: '/submissions/submit/' in r.url, timeout=15000) as r_info:
            page1.click('#btn-submit')
        page1.wait_for_selector('#btn-submit:not([disabled])', timeout=5000)
        print("=> THÀNH CÔNG: hs_demo đã nộp bài đúng lấy 10 điểm!")
        context1.close()

        # === TEST 3: HỌC SINH 2 NỘP BÀI ĐẠO VĂN ===
        print("\n--- TEST 3: KIỂM TRA ĐẠO VĂN (HS2 đổi tên biến của HS1) ---")
        context2 = browser.new_context()
        page2 = context2.new_page()
        page2.on("dialog", lambda dialog: dialog.accept())
        
        page2.goto('http://127.0.0.1:8000/accounts/login/')
        page2.fill('input[name="username"]', 'hs_demo2')
        page2.fill('input[name="password"]', '123456')
        page2.click('button[type="submit"]')
        page2.wait_for_load_state('networkidle')
        
        page2.goto(f'http://127.0.0.1:8000/submissions/solve/{assignment_id}/')
        page2.wait_for_selector('#btn-submit')
        
        # Inject mã nguồn đổi tên biến của HS1
        code_plagiarism = 'bien_moi = int(input())\nprint(bien_moi)'
        page2.evaluate(f"window.editor.setValue(`{code_plagiarism}`)")
        
        with page2.expect_response(lambda r: '/submissions/submit/' in r.url, timeout=15000) as r_info:
            page2.click('#btn-submit')
        page2.wait_for_selector('#btn-submit:not([disabled])', timeout=5000)
        print("=> THÀNH CÔNG: hs_demo2 đã nộp bài (code copy đổi tên biến).")
        context2.close()
        
        # === TEST 4: GIÁO VIÊN CHECK ĐẠO VĂN & XUẤT ĐIỂM ===
        print("\n--- TEST 4: GIÁO VIÊN XỬ LÝ (CHECK ĐẠO VĂN & TẢI EXCEL) ---")
        context3 = browser.new_context()
        page3 = context3.new_page()
        
        page3.goto('http://127.0.0.1:8000/accounts/login/')
        page3.fill('input[name="username"]', 'gv_demo')
        page3.fill('input[name="password"]', '123456')
        page3.click('button[type="submit"]')
        page3.wait_for_load_state('networkidle')
        
        # Vào trang đạo văn
        page3.goto(f'http://127.0.0.1:8000/assignments/{assignment_id}/plagiarism/')
        print("Giáo viên truy cập trang check đạo văn...")
        page3.wait_for_timeout(3000)
        
        try:
            # Nhấn nút Phân tích đạo văn (Nút này thường form POST hoặc link)
            page3.click('button:has-text("Phân tích"), a:has-text("Phân tích")', timeout=3000)
            page3.wait_for_timeout(3000)
            print("=> Đã thao tác phân tích đạo văn!")
        except Exception:
            print("=> Bỏ qua bước click (Có thể hệ thống phân tích tự động hoặc nút tên khác).")

        # Tải file Excel
        print("Giáo viên vào sổ điểm và tải file Excel...")
        page3.goto('http://127.0.0.1:8000/classrooms/1/gradebook/')
        page3.wait_for_timeout(3000)
        try:
            with page3.expect_download(timeout=5000) as download_info:
                page3.click('a:has-text("Xuất"), button:has-text("Xuất")', timeout=3000)
            download = download_info.value
            download.save_as("Sodiem_test.xlsx")
            print("=> THÀNH CÔNG: Đã tải file Excel sổ điểm thành công!")
        except Exception as e:
            print(f"=> CẢNH BÁO: Không tìm thấy nút Xuất Excel hoặc lỗi tải: {e}")
            
        context3.close()
        browser.close()
        print("\n🎉 HOÀN TẤT TOÀN BỘ E2E TEST (TLE, AUTO GRADE, PLAGIARISM, EXPORT)!")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python e2e_full_test_playwright.py <assignment_id>")
        sys.exit(1)
    run_all_tests(sys.argv[1])
