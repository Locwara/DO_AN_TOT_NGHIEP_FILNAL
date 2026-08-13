import re

with open('/home/locwara/DO_AN_TOT_NGHIEP_FINAL/src/Websitedayvahoclaptrinh/templates/assignments/_assignment_form.html', 'r') as f:
    content = f.read()

# Replace the single textareas with hidden inputs container
code_section = """                        <div data-code-only class="hidden space-y-6">
                        <div id="code-editor-language-selector" class="flex gap-2 mb-4">
                            <!-- Language tabs injected via JS -->
                        </div>
                        <div id="hidden-code-inputs-container"></div>
                        
                        <label for="assignment-starter-code" class="block text-sm font-semibold text-slate-700 mb-2">Mã nguồn khởi tạo (<span id="current-starter-lang" class="text-primary"></span>)</label>
                        <div class="relative border border-slate-200 rounded-lg overflow-hidden group mb-6">
                            <div class="absolute top-2 right-2 z-10 flex gap-2">
                                <button type="button" id="btn-format-starter" class="bg-white/80 backdrop-blur-sm border border-slate-200 text-primary hover:bg-primary hover:text-white px-3 py-1.5 rounded text-xs font-bold shadow-sm transition-all flex items-center gap-1">
                                    <span class="material-symbols-outlined text-[14px]">format_align_left</span>
                                    Format
                                </button>
                            </div>
                            <div id="monaco-starter-editor" style="height: 250px; width: 100%;"></div>
                        </div>

                        <label for="assignment-solution-code" class="block text-sm font-semibold text-slate-700 mb-2">Mã nguồn mẫu (<span id="current-solution-lang" class="text-primary"></span>) *</label>
                        <div class="relative border border-slate-200 rounded-lg overflow-hidden group">
                            <div class="absolute top-2 right-2 z-10 flex gap-2">
                                <button type="button" id="btn-format-solution" class="bg-white/80 backdrop-blur-sm border border-slate-200 text-primary hover:bg-primary hover:text-white px-3 py-1.5 rounded text-xs font-bold shadow-sm transition-all flex items-center gap-1">
                                    <span class="material-symbols-outlined text-[14px]">format_align_left</span>
                                    Format
                                </button>
                            </div>
                            <div id="monaco-solution-editor" style="height: 350px; width: 100%;"></div>
                        </div>
                        <!-- END -->"""

content = re.sub(r'<div data-code-only class="hidden space-y-6">.*?<!-- Integrated Testcase Manager -->', code_section + '\n                        <!-- Integrated Testcase Manager -->', content, flags=re.DOTALL)

with open('/home/locwara/DO_AN_TOT_NGHIEP_FINAL/src/Websitedayvahoclaptrinh/templates/assignments/_assignment_form.html', 'w') as f:
    f.write(content)
