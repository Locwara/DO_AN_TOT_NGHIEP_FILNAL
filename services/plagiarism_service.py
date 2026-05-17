"""Code plagiarism detection service.

Uses structural similarity analysis:
1. Normalize whitespace, comments, and variable names
2. Compare token streams using SequenceMatcher
3. Return a similarity score (0.0 – 1.0)
"""
import ast
import re
import difflib
import logging
from collections import Counter

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Language-specific comment / string strippers
# ---------------------------------------------------------------------------

def _strip_python_comments(code):
    """Remove comments and docstrings from Python code."""
    lines = []
    in_docstring = False
    docstring_char = None
    for line in code.split('\n'):
        stripped = line.strip()
        if in_docstring:
            if docstring_char in stripped:
                in_docstring = False
            continue
        if stripped.startswith('"""') or stripped.startswith("'''"):
            docstring_char = stripped[:3]
            if stripped.count(docstring_char) == 1:
                in_docstring = True
            continue
        if '#' in line:
            line = line[:line.index('#')]
        if line.strip():
            lines.append(line)
    return '\n'.join(lines)


def _strip_c_style_comments(code):
    """Remove // and /* */ comments from C/C++/Java/JS code."""
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    code = re.sub(r'//[^\n]*', '', code)
    return code


def _strip_comments(code, language):
    lang = language.lower()
    if lang in ('python', 'python3'):
        return _strip_python_comments(code)
    if lang in ('cpp', 'c', 'java', 'javascript', 'nodejs'):
        return _strip_c_style_comments(code)
    return code


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

def _normalize_whitespace(code):
    """Collapse all whitespace into single spaces and strip blank lines."""
    lines = []
    for line in code.split('\n'):
        normalized = ' '.join(line.split())
        if normalized:
            lines.append(normalized)
    return '\n'.join(lines)


def _normalize_python_identifiers(code):
    """Attempt to rename local variable names to generic placeholders."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code

    names = {}
    counter = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            if node.id not in names:
                names[node.id] = f'_v{counter}'
                counter += 1

    result = code
    for original, replacement in sorted(names.items(), key=lambda x: -len(x[0])):
        result = re.sub(r'\b' + re.escape(original) + r'\b', replacement, result)
    return result


def _tokenize_generic(code):
    """Split code into a list of meaningful tokens."""
    return re.findall(r'[a-zA-Z_]\w*|\d+|[^\s\w]', code)


def normalize_code(code, language):
    """Produce a normalised form of the code for comparison."""
    code = _strip_comments(code, language)
    code = _normalize_whitespace(code)
    if language.lower() in ('python', 'python3'):
        code = _normalize_python_identifiers(code)
    return code


# ---------------------------------------------------------------------------
# Similarity scoring
# ---------------------------------------------------------------------------

def text_similarity(code_a, code_b):
    """Raw text similarity using SequenceMatcher (0.0–1.0)."""
    return difflib.SequenceMatcher(None, code_a, code_b).ratio()


def token_similarity(code_a, code_b):
    """Token-level similarity using SequenceMatcher (0.0–1.0)."""
    tokens_a = _tokenize_generic(code_a)
    tokens_b = _tokenize_generic(code_b)
    if not tokens_a and not tokens_b:
        return 1.0
    if not tokens_a or not tokens_b:
        return 0.0
    return difflib.SequenceMatcher(None, tokens_a, tokens_b).ratio()


def structural_similarity(code_a, code_b):
    """Bag-of-tokens cosine-like similarity (0.0–1.0)."""
    tokens_a = Counter(_tokenize_generic(code_a))
    tokens_b = Counter(_tokenize_generic(code_b))
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = sum((tokens_a & tokens_b).values())
    magnitude = (sum(tokens_a.values()) * sum(tokens_b.values())) ** 0.5
    if magnitude == 0:
        return 0.0
    return intersection / magnitude


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_similarity(code_a, code_b, language='python'):
    """Compare two pieces of code and return a detailed similarity report.

    Returns:
        dict with keys:
            similarity_score  – weighted average (0.0–1.0)
            text_score        – raw text similarity
            token_score       – token-level similarity
            structural_score  – bag-of-tokens similarity
            is_suspicious     – True if score >= 0.85
    """
    norm_a = normalize_code(code_a, language)
    norm_b = normalize_code(code_b, language)

    t_score = text_similarity(norm_a, norm_b)
    tk_score = token_similarity(norm_a, norm_b)
    s_score = structural_similarity(norm_a, norm_b)

    weighted = 0.3 * t_score + 0.4 * tk_score + 0.3 * s_score

    return {
        'similarity_score': round(weighted, 4),
        'text_score': round(t_score, 4),
        'token_score': round(tk_score, 4),
        'structural_score': round(s_score, 4),
        'is_suspicious': weighted >= 0.85,
    }


def check_plagiarism_batch(submissions, language='python'):
    """Compare all submissions pairwise and return suspicious pairs.

    Args:
        submissions: list of dicts with keys 'id', 'student_id', 'code'
        language: programming language

    Returns:
        list of dicts with keys:
            submission_a, submission_b, student_a, student_b,
            similarity_score, is_suspicious
    """
    results = []
    n = len(submissions)
    for i in range(n):
        for j in range(i + 1, n):
            a = submissions[i]
            b = submissions[j]
            if a['student_id'] == b['student_id']:
                continue
            report = check_similarity(a['code'], b['code'], language)
            results.append({
                'submission_a': a['id'],
                'submission_b': b['id'],
                'student_a': a['student_id'],
                'student_b': b['student_id'],
                'similarity_score': report['similarity_score'],
                'text_score': report['text_score'],
                'token_score': report['token_score'],
                'structural_score': report['structural_score'],
                'is_suspicious': report['is_suspicious'],
            })
    results.sort(key=lambda r: r['similarity_score'], reverse=True)
    return results
