import csv
import io
import pandas as pd
from docx import Document
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from .models import Assignments, QuizQuestions, QuizChoices
from core.decorators import teacher_required

@login_required
@teacher_required
def download_quiz_template_view(request, format):
    """Xuất file mẫu trắc nghiệm (csv, xlsx, docx)."""
    sample_data = [
        {
            'question': 'Kiểu dữ liệu nào trong Python là immutable?',
            'type': 'single_choice',
            'points': 1.0,
            'choice_1': 'list',
            'choice_2': 'dict',
            'choice_3': 'tuple',
            'choice_4': 'set',
            'correct_index': 3,
            'explanation': 'Tuple không thể thay đổi sau khi tạo.'
        }
    ]

    if format == 'csv':
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=sample_data[0].keys())
        writer.writeheader()
        writer.writerows(sample_data)
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="quiz_template.csv"'
        return response

    elif format == 'xlsx':
        df = pd.DataFrame(sample_data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        response = HttpResponse(output.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="quiz_template.xlsx"'
        return response

    elif format == 'docx':
        doc = Document()
        doc.add_heading('Mẫu Import Câu hỏi Trắc nghiệm', 0)
        doc.add_paragraph('Vui lòng nhập theo cấu trúc bên dưới. Mỗi câu hỏi bắt đầu bằng [QUESTION].')
        
        for item in sample_data:
            doc.add_paragraph(f"[QUESTION]: {item['question']}")
            doc.add_paragraph(f"[TYPE]: {item['type']}")
            doc.add_paragraph(f"[POINTS]: {item['points']}")
            doc.add_paragraph(f"[A]: {item['choice_1']}")
            doc.add_paragraph(f"[B]: {item['choice_2']}")
            doc.add_paragraph(f"[C]: {item['choice_3']}")
            doc.add_paragraph(f"[D]: {item['choice_4']}")
            doc.add_paragraph(f"[CORRECT]: C")
            doc.add_paragraph(f"[EXPLANATION]: {item['explanation']}")
            doc.add_paragraph("-" * 20)

        output = io.BytesIO()
        doc.save(output)
        response = HttpResponse(output.getvalue(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = 'attachment; filename="quiz_template.docx"'
        return response

    return HttpResponse("Định dạng không hỗ trợ", status=400)

def process_quiz_import(file_obj, assignment):
    """Xử lý parse file và lưu vào database."""
    filename = file_obj.name.lower()
    rows = []

    try:
        # 1. Đọc toàn bộ dữ liệu từ file vào list rows trước để đếm số câu
        if filename.endswith('.csv'):
            stream = io.StringIO(file_obj.read().decode('utf-8'))
            reader = csv.DictReader(stream)
            rows = list(reader)

        elif filename.endswith('.xlsx'):
            df = pd.read_excel(file_obj)
            rows = [row.to_dict() for _, row in df.iterrows()]

        elif filename.endswith('.docx'):
            doc = Document(file_obj)
            current_q = {}
            for para in doc.paragraphs:
                text = para.text.strip()
                if not text: continue
                if text.startswith('[QUESTION]:'): current_q['question'] = text.replace('[QUESTION]:', '').strip()
                elif text.startswith('[TYPE]:'): current_q['type'] = text.replace('[TYPE]:', '').strip()
                elif text.startswith('[A]:'): current_q['choice_1'] = text.replace('[A]:', '').strip()
                elif text.startswith('[B]:'): current_q['choice_2'] = text.replace('[B]:', '').strip()
                elif text.startswith('[C]:'): current_q['choice_3'] = text.replace('[C]:', '').strip()
                elif text.startswith('[D]:'): current_q['choice_4'] = text.replace('[D]:', '').strip()
                elif text.startswith('[CORRECT]:'): 
                    val = text.replace('[CORRECT]:', '').strip().upper()
                    mapping = {'A': 1, 'B': 2, 'C': 3, 'D': 4}
                    current_q['correct_index'] = mapping.get(val, 1)
                elif text.startswith('[EXPLANATION]:'): current_q['explanation'] = text.replace('[EXPLANATION]:', '').strip()
                
                if 'explanation' in current_q and len(current_q) >= 7:
                    rows.append(current_q)
                    current_q = {}

        # 2. Tính toán điểm mỗi câu để tổng luôn là 100
        total_questions = len(rows)
        if total_questions == 0:
            return False, "File không chứa câu hỏi hợp lệ."
        
        points_per_question = round(100.0 / total_questions, 2)
        
        # 3. Tiến hành lưu vào database
        for row in rows:
            row['points'] = points_per_question # Ghi đè điểm tự động
            _create_question_from_row(row, assignment)

        return True, total_questions
    except Exception as e:
        return False, str(e)

def _create_question_from_row(row, assignment):
    """Helper để lưu câu hỏi và đáp án."""
    q = QuizQuestions.objects.create(
        assignment=assignment,
        question_text=row.get('question') or row.get('question_text'),
        question_type=row.get('type') or 'single_choice',
        points=float(row.get('points') or 1.0),
        explanation=row.get('explanation', ''),
        is_active=True
    )
    
    # Tạo đáp án (giả định mẫu có 4 lựa chọn)
    for i in range(1, 5):
        choice_text = row.get(f'choice_{i}') or row.get(f'option_{i}')
        if choice_text:
            QuizChoices.objects.create(
                question=q,
                choice_text=choice_text,
                is_correct=(int(row.get('correct_index') or 0) == i),
                order_index=i
            )
