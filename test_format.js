function formatPythonSquashed(code) {
    let s = code.replace(/:\s+/g, ':\n');
    s = s.replace(/\s+(def |if |elif |else:|for |while |return|print|try:|except|with |class |pass|continue|break|a, |b, )/g, '\n$1');
    s = s.replace(/\s*(if __name__ ==)/g, '\n$1');
    
    let lines = s.split('\n').map(l => l.trim()).filter(l => l.length > 0);
    let out = [];
    let indent = 0;
    
    for (let i=0; i<lines.length; i++) {
        let l = lines[i];
        if (l.startsWith('if __name__')) indent = 0;
        
        if (l.startsWith('elif ') || l === 'else:' || l.startsWith('except') || l === 'finally:') {
            indent = Math.max(0, indent - 1);
        }
        
        out.push('    '.repeat(indent) + l);
        
        if (l.endsWith(':')) {
            indent++;
        }
        if (l.startsWith('return ') || l === 'return' || l === 'pass' || l === 'continue' || l === 'break') {
            indent = Math.max(0, indent - 1);
        }
    }
    return out.join('\n');
}

console.log(formatPythonSquashed('def solve(): n = int(input()) if n < 2: print("NO") return'));
console.log("-----");
console.log(formatPythonSquashed("def main(): a, b = map(int, input().split()) print(a + b) if __name__ == '__main__': main()"));
