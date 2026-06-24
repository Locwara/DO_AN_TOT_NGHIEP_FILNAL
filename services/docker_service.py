import subprocess
import tempfile
import os
import time
import shutil
import logging
import re

logger = logging.getLogger(__name__)


class CodeExecutionResult:
    def __init__(self, stdout='', stderr='', exit_code=0, execution_time=0.0, memory_usage=0.0, timed_out=False):
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.execution_time = execution_time
        self.memory_usage = memory_usage
        self.timed_out = timed_out

    @property
    def success(self):
        return self.exit_code == 0 and not self.timed_out


_DOCKER_AVAILABLE = None


def is_docker_available():
    """Check if Docker daemon is running and accessible."""
    global _DOCKER_AVAILABLE
    if _DOCKER_AVAILABLE is not None:
        return _DOCKER_AVAILABLE
    try:
        result = subprocess.run(
            ['docker', 'info'],
            capture_output=True, text=True, timeout=5,
        )
        _DOCKER_AVAILABLE = result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        _DOCKER_AVAILABLE = False
    return _DOCKER_AVAILABLE


def _get_file_extension(language):
    extensions = {
        'python': '.py',
        'python3': '.py',
        'cpp': '.cpp',
        'c': '.c',
        'java': '.java',
        'javascript': '.js',
        'nodejs': '.js',
        'csharp': '.cs',
    }
    return extensions.get(language.lower(), '.txt')


def _get_compile_command(language, filename):
    commands = {
        'cpp': ['g++', '-o', 'solution', filename, '-std=c++17'],
        'c': ['gcc', '-o', 'solution', filename],
        'java': ['javac', filename],
        'csharp': ['mcs', '-out:solution.exe', filename],
    }
    return commands.get(language.lower())


def _get_run_command(language, filename):
    commands = {
        'python': ['python3', filename],
        'python3': ['python3', filename],
        'cpp': ['./solution'],
        'c': ['./solution'],
        'java': ['java', filename.replace('.java', '')],
        'javascript': ['node', filename],
        'nodejs': ['node', filename],
        'csharp': ['mono', 'solution.exe'],
    }
    return commands.get(language.lower(), ['python3', filename])


def _get_default_docker_image(language):
    images = {
        'python': 'python:3.11-alpine',
        'python3': 'python:3.11-alpine',
        'cpp': 'gcc:13-bookworm',
        'c': 'gcc:13-bookworm',
        'java': 'openjdk:17-slim',
        'javascript': 'node:20-alpine',
        'nodejs': 'node:20-alpine',
        'csharp': 'mono:6.12',
    }
    return images.get(language.lower(), 'python:3.11-alpine')


def _build_docker_script(language, filename):
    """Build a shell script that compiles (if needed) and runs the code."""
    compile_cmd = _get_compile_command(language, filename)
    run_cmd = _get_run_command(language, filename)

    lines = ['#!/bin/sh', 'cd /sandbox']
    if compile_cmd:
        lines.append(' '.join(compile_cmd) + ' || exit 1')
    # Use /usr/bin/time -v -o to measure memory and redirect time output to .metrics, preserving program stderr
    # Fallback to cgroup if /usr/bin/time is missing
    lines.append('if [ -x /usr/bin/time ]; then')
    lines.append('    /usr/bin/time -v -o /sandbox/.metrics ' + ' '.join(run_cmd))
    lines.append('    EXIT_CODE=$?')
    lines.append('else')
    lines.append('    ' + ' '.join(run_cmd))
    lines.append('    EXIT_CODE=$?')
    lines.append('    if [ -f /sys/fs/cgroup/memory.peak ]; then')
    lines.append('        cat /sys/fs/cgroup/memory.peak > /sandbox/.metrics_mem')
    lines.append('    elif [ -f /sys/fs/cgroup/memory/memory.max_usage_in_bytes ]; then')
    lines.append('        cat /sys/fs/cgroup/memory/memory.max_usage_in_bytes > /sandbox/.metrics_mem')
    lines.append('    fi')
    lines.append('fi')
    lines.append('exit $EXIT_CODE')
    return '\n'.join(lines)


def _execute_with_docker(code, language, input_data='', timeout_seconds=5,
                         memory_limit_mb=256, docker_image=None, cpu_limit=1.0):
    """Execute code inside a Docker container with resource limits."""
    tmpdir = tempfile.mkdtemp(prefix='learncode_docker_')
    try:
        os.chmod(tmpdir, 0o777)

        ext = _get_file_extension(language)
        filename = 'Main.java' if language.lower() == 'java' else f'solution{ext}'

        filepath = os.path.join(tmpdir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(code)
        os.chmod(filepath, 0o644)

        script = _build_docker_script(language, filename)
        script_path = os.path.join(tmpdir, 'run.sh')
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script)
        os.chmod(script_path, 0o755)

        image = docker_image or _get_default_docker_image(language)

        docker_cmd = [
            'docker', 'run',
            '--rm',
            '-i',
            '--network=none',
            f'--memory={memory_limit_mb}m',
            f'--memory-swap={memory_limit_mb}m',
            f'--cpus={cpu_limit}',
            '--pids-limit=64',
            '--read-only',
            '--tmpfs', '/tmp:rw,noexec,nosuid,size=64m',
            '-v', f'{tmpdir}:/sandbox:rw',
            '-w', '/sandbox',
            '--user', '65534:65534',
            image,
            '/bin/sh', '/sandbox/run.sh',
        ]

        start_time = time.time()
        try:
            result = subprocess.run(
                docker_cmd,
                input=input_data,
                capture_output=True,
                text=True,
                timeout=timeout_seconds + 5,
            )
            execution_time = time.time() - start_time
            
            memory_usage_mb = 0.0
            metrics_path = os.path.join(tmpdir, '.metrics')
            metrics_mem_path = os.path.join(tmpdir, '.metrics_mem')
            if os.path.exists(metrics_path):
                with open(metrics_path, 'r', encoding='utf-8') as f:
                    metrics_content = f.read()
                    # GNU time outputs "Maximum resident set size (kbytes): <num>"
                    match = re.search(r'Maximum resident set size \(kbytes\):\s+(\d+)', metrics_content)
                    if match:
                        memory_usage_mb = round(int(match.group(1)) / 1024.0, 2)
            
            if memory_usage_mb == 0.0 and os.path.exists(metrics_mem_path):
                with open(metrics_mem_path, 'r', encoding='utf-8') as f:
                    try:
                        mem_bytes = int(f.read().strip())
                        memory_usage_mb = round(mem_bytes / (1024.0 * 1024.0), 2)
                    except ValueError:
                        pass

            return CodeExecutionResult(
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                execution_time=round(execution_time * 1000, 2),
                memory_usage=memory_usage_mb,
            )
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            return CodeExecutionResult(
                stderr=f'Time Limit Exceeded ({timeout_seconds}s)',
                exit_code=1,
                execution_time=round(execution_time * 1000, 2),
                timed_out=True,
            )
    except Exception as e:
        logger.exception('Docker execution failed')
        return CodeExecutionResult(
            stderr=f'Docker Error: {str(e)}',
            exit_code=1,
        )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _execute_with_subprocess(code, language, input_data='', timeout_seconds=5,
                             memory_limit_mb=256):
    """Execute code using local subprocess (fallback when Docker is unavailable)."""
    tmpdir = tempfile.mkdtemp(prefix='learncode_')
    try:
        ext = _get_file_extension(language)
        filename = 'Main.java' if language.lower() == 'java' else f'solution{ext}'

        filepath = os.path.join(tmpdir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(code)

        compile_cmd = _get_compile_command(language, filename)
        if compile_cmd:
            try:
                compile_result = subprocess.run(
                    compile_cmd,
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if compile_result.returncode != 0:
                    return CodeExecutionResult(
                        stdout='',
                        stderr=f'Compilation Error:\n{compile_result.stderr}',
                        exit_code=compile_result.returncode,
                    )
            except subprocess.TimeoutExpired:
                return CodeExecutionResult(
                    stderr='Compilation timed out.',
                    exit_code=1,
                    timed_out=True,
                )

        run_cmd = _get_run_command(language, filename)

        start_time = time.time()
        try:
            result = subprocess.run(
                run_cmd,
                cwd=tmpdir,
                input=input_data,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            execution_time = time.time() - start_time

            return CodeExecutionResult(
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                execution_time=round(execution_time * 1000, 2),
                memory_usage=0,
            )
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            return CodeExecutionResult(
                stderr=f'Time Limit Exceeded ({timeout_seconds}s)',
                exit_code=1,
                execution_time=round(execution_time * 1000, 2),
                timed_out=True,
            )
    except Exception as e:
        logger.exception('Local sandbox execution failed')
        return CodeExecutionResult(
            stderr=f'System Error: {str(e)}',
            exit_code=1,
        )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def execute_code(code, language, input_data='', timeout_seconds=5,
                 memory_limit_mb=256, docker_image=None, cpu_limit=1.0):
    """Execute code in a sandboxed environment.

    Uses Docker if available, falls back to direct subprocess execution.
    """
    if is_docker_available():
        return _execute_with_docker(
            code, language, input_data,
            timeout_seconds, memory_limit_mb, docker_image, cpu_limit,
        )
    return _execute_with_subprocess(
        code, language, input_data,
        timeout_seconds, memory_limit_mb,
    )


def _normalize_output_for_display(text):
    """Normalize output text for stable display and storage."""
    if text is None:
        return ''
    normalized = text.replace('\r\n', '\n').replace('\r', '\n')
    normalized = normalized.replace('\u00a0', ' ')
    normalized = normalized.replace('\ufeff', '')
    return normalized.strip()


def _normalize_output_for_compare(text):
    """Normalize output text for judging.

    Compares token-by-token to avoid false WA caused by whitespace-only differences.
    """
    normalized = _normalize_output_for_display(text)
    # Remove zero-width chars often introduced when copy/pasting test data.
    normalized = re.sub(r'[\u200b\u200c\u200d\u2060]', '', normalized)
    return ' '.join(normalized.split())


def run_testcase(code, language, input_data, expected_output,
                 timeout_seconds=5, memory_limit_mb=256,
                 docker_image=None, cpu_limit=1.0):
    """Run code against a single testcase and check output."""
    result = execute_code(
        code, language, input_data,
        timeout_seconds, memory_limit_mb, docker_image, cpu_limit,
    )

    if not result.success:
        if result.timed_out:
            status = 'time_limit_exceeded'
        elif result.stderr and 'Compilation Error' in result.stderr:
            status = 'compilation_error'
        else:
            status = 'runtime_error'
        return {
            'status': status,
            'actual_output': _normalize_output_for_display(result.stdout),
            'expected_output': _normalize_output_for_display(expected_output),
            'execution_time': result.execution_time,
            'memory_usage': result.memory_usage,
            'error_message': result.stderr,
            'passed': False,
        }

    actual = _normalize_output_for_display(result.stdout)
    expected = _normalize_output_for_display(expected_output)
    passed = _normalize_output_for_compare(result.stdout) == _normalize_output_for_compare(expected_output)

    return {
        'status': 'passed' if passed else 'wrong_answer',
        'actual_output': actual,
        'expected_output': expected,
        'execution_time': result.execution_time,
        'memory_usage': result.memory_usage,
        'error_message': '',
        'passed': passed,
    }
