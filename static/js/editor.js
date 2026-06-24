document.addEventListener('DOMContentLoaded', () => {
    const uploadInput = document.getElementById('upload-code');
    const langSelect = document.getElementById('language-select');

    if (uploadInput && langSelect) {
        uploadInput.addEventListener('change', async (e) => {
            if (!window.editor) {
                alert('Trình soạn thảo chưa được khởi tạo.');
                return;
            }

            const file = e.target.files[0];
            if (!file) return;

            // Validate file size (<= 200KB)
            if (file.size > 200_000) {
                alert('File quá lớn (>200KB). Vui lòng chọn file nhỏ hơn.');
                uploadInput.value = ''; // Reset input
                return;
            }

            // Get extension
            const ext = file.name.split('.').pop().toLowerCase();
            const langMap = {
                'py': 'python',
                'cpp': 'cpp',
                'c': 'c',
                'java': 'java',
                'js': 'javascript',
                'cs': 'csharp'
            };

            const targetLang = langMap[ext];
            
            if (!targetLang) {
                alert('Định dạng file không được hỗ trợ. Các định dạng cho phép: .py, .cpp, .c, .java, .js, .cs');
                uploadInput.value = '';
                return;
            }
            
            // Check if language is allowed in the assignment (exists in the dropdown)
            let langExists = false;
            for (let i = 0; i < langSelect.options.length; i++) {
                if (langSelect.options[i].value === targetLang) {
                    langExists = true;
                    break;
                }
            }

            if (!langExists) {
                alert(`Ngôn ngữ của file (.${ext}) không được phép trong bài tập này.`);
                uploadInput.value = '';
                return;
            }

            try {
                const text = await file.text();
                // Set editor content
                window.editor.setValue(text);
                
                // Switch language dropdown and trigger change event
                langSelect.value = targetLang;
                langSelect.dispatchEvent(new Event('change'));
                
                alert(`Đã nạp thành công file ${file.name}`);
            } catch (err) {
                alert('Có lỗi xảy ra khi đọc file: ' + err.message);
            }
            
            uploadInput.value = ''; // Reset after successful/failed read
        });
    }
});