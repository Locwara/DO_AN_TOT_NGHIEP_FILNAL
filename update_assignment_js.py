import re
with open('/home/locwara/DO_AN_TOT_NGHIEP_FINAL/src/Websitedayvahoclaptrinh/templates/assignments/_assignment_form.html', 'r') as f:
    content = f.read()

js_replacement = """        // Multi-language Editor State
        const hiddenInputsContainer = document.getElementById('hidden-code-inputs-container');
        const langSelector = document.getElementById('code-editor-language-selector');
        const currentStarterLang = document.getElementById('current-starter-lang');
        const currentSolutionLang = document.getElementById('current-solution-lang');
        
        let starterCodesData = {};
        let solutionCodesData = {};
        let currentLangEditor = null;
        
        {% if form.instance.pk and form.instance.starter_codes %}
            starterCodesData = {{ form.instance.starter_codes|default:'{}'|safe }};
            solutionCodesData = {{ form.instance.solution_codes|default:'{}'|safe }};
        {% endif %}

        const starterEditor = monaco.editor.create(document.getElementById('monaco-starter-editor'), {
            value: '',
            language: 'python',
            theme: 'vs',
            minimap: { enabled: false },
            fontSize: 14,
            fontFamily: "'Fira Code', 'Consolas', monospace"
        });
        const solutionEditor = monaco.editor.create(document.getElementById('monaco-solution-editor'), {
            value: '',
            language: 'python',
            theme: 'vs-dark',
            minimap: { enabled: false },
            fontSize: 14,
            fontFamily: "'Fira Code', 'Consolas', monospace"
        });

        document.getElementById('btn-format-starter').addEventListener('click', () => formatPythonCode(starterEditor));
        document.getElementById('btn-format-solution').addEventListener('click', () => formatPythonCode(solutionEditor));

        starterEditor.onDidChangeModelContent(() => {
            if(currentLangEditor) {
                starterCodesData[currentLangEditor] = starterEditor.getValue();
                updateHiddenCodeInputs();
            }
        });
        solutionEditor.onDidChangeModelContent(() => {
            if(currentLangEditor) {
                solutionCodesData[currentLangEditor] = solutionEditor.getValue();
                updateHiddenCodeInputs();
            }
        });

        function updateHiddenCodeInputs() {
            hiddenInputsContainer.innerHTML = '';
            for(let lang in starterCodesData) {
                const inputStarter = document.createElement('input');
                inputStarter.type = 'hidden';
                inputStarter.name = 'starter_code_' + lang;
                inputStarter.value = starterCodesData[lang];
                hiddenInputsContainer.appendChild(inputStarter);
            }
            for(let lang in solutionCodesData) {
                const inputSolution = document.createElement('input');
                inputSolution.type = 'hidden';
                inputSolution.name = 'solution_code_' + lang;
                inputSolution.value = solutionCodesData[lang];
                hiddenInputsContainer.appendChild(inputSolution);
            }
        }

        function switchEditorLanguage(lang) {
            currentLangEditor = lang;
            currentStarterLang.textContent = lang;
            currentSolutionLang.textContent = lang;
            
            // Set monaco language model
            let monacoLang = lang.includes('c') ? 'cpp' : lang.includes('java') ? 'java' : 'python';
            monaco.editor.setModelLanguage(starterEditor.getModel(), monacoLang);
            monaco.editor.setModelLanguage(solutionEditor.getModel(), monacoLang);
            
            starterEditor.setValue(starterCodesData[lang] || '');
            solutionEditor.setValue(solutionCodesData[lang] || '');
            
            document.querySelectorAll('.lang-editor-tab').forEach(btn => {
                if(btn.dataset.lang === lang) {
                    btn.classList.add('bg-primary', 'text-white');
                    btn.classList.remove('bg-slate-100', 'text-slate-600');
                } else {
                    btn.classList.remove('bg-primary', 'text-white');
                    btn.classList.add('bg-slate-100', 'text-slate-600');
                }
            });
        }

        function refreshEditorTabs() {
            langSelector.innerHTML = '';
            const checkedLangs = Array.from(document.querySelectorAll('input[name="allowed_languages"]:checked')).map(cb => cb.value);
            
            if(checkedLangs.length === 0) {
                langSelector.innerHTML = '<span class="text-xs text-red-500 italic">Vui lòng chọn ít nhất 1 ngôn ngữ ở mục trên!</span>';
                currentLangEditor = null;
                starterEditor.setValue('');
                solutionEditor.setValue('');
                return;
            }

            checkedLangs.forEach(lang => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'lang-editor-tab px-3 py-1 rounded text-xs font-bold transition-all';
                btn.textContent = 'Chỉnh sửa: ' + lang;
                btn.dataset.lang = lang;
                btn.addEventListener('click', () => switchEditorLanguage(lang));
                langSelector.appendChild(btn);
            });
            
            if(!checkedLangs.includes(currentLangEditor)) {
                switchEditorLanguage(checkedLangs[0]);
            } else {
                switchEditorLanguage(currentLangEditor);
            }
        }
        
        // Listen to checkbox changes
        document.querySelectorAll('input[name="allowed_languages"]').forEach(cb => {
            cb.addEventListener('change', refreshEditorTabs);
        });

        // initial render
        setTimeout(refreshEditorTabs, 500);
"""

# Find where to replace
content = re.sub(r'// Solution Code.*?document\.getElementById\(\'btn-format-starter\'\)\.addEventListener\(\'click\', \(\) => formatPythonCode\(starterEditor\)\);', js_replacement, content, flags=re.DOTALL)

with open('/home/locwara/DO_AN_TOT_NGHIEP_FINAL/src/Websitedayvahoclaptrinh/templates/assignments/_assignment_form.html', 'w') as f:
    f.write(content)
