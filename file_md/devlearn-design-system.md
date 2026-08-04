# 💻 DevLearn — Design System
> Áp dụng nhất quán cho **mọi trang** của website dạy & học lập trình.  
> Màu gốc: `rgb(19 127 236)` = `#137FEC` · Nền: `#ffffff`

---

## 1. CSS Variables — Dán vào `:root` của mọi trang

```css
:root {
  /* === PRIMARY PALETTE (xoay quanh #137FEC) === */
  --primary-950: #020d1f;   /* nền code dark, footer bg */
  --primary-900: #061a38;   /* heading chính, sidebar dark */
  --primary-800: #0b2d60;   /* hero gradient start */
  --primary-700: #0f4289;   /* hero gradient mid, dark hover */
  --primary-600: #1260c0;   /* hover button, link hover */
  --primary-500: #137fec;   /* ★ MÀU CHÍNH — button, icon, progress */
  --primary-400: #3d9af5;   /* icon phụ, highlight */
  --primary-300: #78bcfa;   /* text trên nền tối */
  --primary-200: #b8d9fd;   /* border nhẹ, divider màu */
  --primary-100: #daeefe;   /* nền badge, focus ring, hover bg */
  --primary-50:  #f0f8ff;   /* nền section xen kẽ, code inline bg */

  /* === ACCENT (Pro / Upgrade / Advanced) === */
  --accent-500: #7c3aed;    /* badge React/Vue, level nâng cao, btn upgrade */
  --accent-400: #8b5cf6;
  --accent-100: #ede9fe;

  /* === SEMANTIC === */
  --success-600: #16a34a;   /* hoàn thành bài, pass test */
  --success-100: #f0fdf4;
  --warning-600: #ea580c;   /* deadline gần, chưa hoàn thành */
  --warning-100: #fff7ed;
  --danger-600:  #dc2626;   /* lỗi, fail test */
  --danger-100:  #fef2f2;

  /* === NEUTRAL === */
  --neutral-900: #0f172a;   /* body text */
  --neutral-700: #334155;   /* label, text phụ */
  --neutral-500: #64748b;   /* muted / caption */
  --neutral-300: #cbd5e1;   /* border input */
  --neutral-100: #f8fafc;   /* nền trang thay thế */
  --white:       #ffffff;   /* nền chính */

  /* === CODE === */
  --code-bg:     #020d1f;   /* nền code block */
  --code-kw:     #7dd3fc;   /* keyword */
  --code-fn:     #bef264;   /* function */
  --code-str:    #fdba74;   /* string */
  --code-num:    #c084fc;   /* number */
  --code-cm:     #475569;   /* comment */
  --code-var:    #e2e8f0;   /* variable, default text */

  /* === SHAPE === */
  --radius-sm:   5px;
  --radius-md:   9px;
  --radius-lg:   14px;
  --radius-xl:   22px;
  --radius-full: 9999px;

  /* === SHADOWS === */
  --shadow-card:  0 1px 3px rgba(19,127,236,0.08), 0 0 0 0.5px rgba(19,127,236,0.10);
  --shadow-btn:   0 2px 8px rgba(19,127,236,0.30);
  --shadow-modal: 0 8px 32px rgba(6,26,56,0.20);

  /* === TYPOGRAPHY === */
  --font-sans: 'Be Vietnam Pro', 'Inter', system-ui, sans-serif;
  --font-mono: 'Cascadia Code', 'Fira Code', 'JetBrains Mono', monospace;
}
```

---

## 2. Màu sắc theo vai trò (Usage Map)

| Vai trò | Token | Hex |
|---|---|---|
| Màu thương hiệu chính | `--primary-500` | `#137fec` |
| Button chính (bắt đầu học, submit) | `--primary-500` | `#137fec` |
| Hover button chính | `--primary-600` | `#1260c0` |
| Button Upgrade / Pro | `--accent-500` | `#7c3aed` |
| Link / text có màu | `--primary-500` | `#137fec` |
| Nền trang | `--white` | `#ffffff` |
| Nền section xen kẽ | `--primary-50` | `#f0f8ff` |
| Nền code inline | `--primary-50` | `#f0f8ff` |
| Nền code block | `--primary-950` | `#020d1f` |
| Nền card | `--white` | `#ffffff` |
| Nền card dark (featured) | `--primary-900` | `#061a38` |
| Border mặc định | `--primary-200` | `#b8d9fd` |
| Border input | `--neutral-300` | `#cbd5e1` |
| Header background | `--white` | `#ffffff` |
| Footer background | `--primary-950` | `#020d1f` |
| Body text | `--neutral-900` | `#0f172a` |
| Text phụ / muted | `--neutral-500` | `#64748b` |
| Progress bar | `--primary-500` | `#137fec` |
| Hoàn thành bài học | `--success-600` | `#16a34a` |

---

## 3. Typography

```css
/* Import font — dán vào <head> */
@import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&family=Fira+Code:wght@400;500&display=swap');

body {
  font-family: var(--font-sans);
  font-size: 15px;
  line-height: 1.65;
  color: var(--neutral-900);
  background: var(--white);
}

/* Scale */
h1 { font-size: 36px; font-weight: 700; color: var(--primary-950); line-height: 1.15; }
h2 { font-size: 26px; font-weight: 700; color: var(--primary-900); line-height: 1.25; }
h3 { font-size: 18px; font-weight: 600; color: var(--primary-700); line-height: 1.35; }
h4 { font-size: 15px; font-weight: 600; color: var(--neutral-700); }

p  { font-size: 14px; color: var(--neutral-700); line-height: 1.65; }

.eyebrow {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--primary-500);
}

.caption { font-size: 12px; color: var(--neutral-500); }

a { color: var(--primary-500); text-decoration: none; }
a:hover { color: var(--primary-600); text-decoration: underline; }

/* Code inline */
code {
  font-family: var(--font-mono);
  font-size: 0.875em;
  background: var(--primary-50);
  color: var(--primary-600);
  border: 0.5px solid var(--primary-200);
  border-radius: var(--radius-sm);
  padding: 2px 6px;
}
```

---

## 4. Buttons

```css
.btn {
  font-family: var(--font-sans);
  font-weight: 500;
  line-height: 1;
  cursor: pointer;
  border: none;
  border-radius: var(--radius-md);
  transition: background 0.14s, transform 0.1s;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.btn:active { transform: scale(0.97); }

/* Primary — hành động chính */
.btn-primary {
  background: var(--primary-500);
  color: var(--white);
  padding: 10px 22px;
  font-size: 14px;
  box-shadow: var(--shadow-btn);
}
.btn-primary:hover { background: var(--primary-600); }

/* Accent — Upgrade, Pro */
.btn-accent {
  background: var(--accent-500);
  color: var(--white);
  padding: 10px 22px;
  font-size: 14px;
}
.btn-accent:hover { background: var(--accent-400); }

/* Dark — GitHub, Terminal */
.btn-dark {
  background: var(--primary-900);
  color: var(--white);
  padding: 10px 22px;
  font-size: 14px;
}
.btn-dark:hover { background: var(--primary-950); }

/* Outline */
.btn-outline {
  background: transparent;
  color: var(--primary-500);
  padding: 9px 20px;
  font-size: 14px;
  border: 1.5px solid var(--primary-500);
}
.btn-outline:hover { background: var(--primary-50); }

/* Ghost */
.btn-ghost {
  background: transparent;
  color: var(--primary-600);
  padding: 9px 16px;
  font-size: 14px;
}
.btn-ghost:hover { background: var(--primary-100); }

/* Small */
.btn-sm {
  background: var(--primary-100);
  color: var(--primary-600);
  padding: 5px 12px;
  font-size: 12px;
  font-weight: 600;
  border-radius: var(--radius-sm);
}

/* Icon */
.btn-icon {
  width: 38px; height: 38px;
  border-radius: 50%;
  background: var(--primary-100);
  color: var(--primary-500);
  display: flex; align-items: center; justify-content: center;
  font-size: 17px;
  border: none; cursor: pointer;
}
```

---

## 5. Header

```css
.site-header {
  background: var(--white);
  border-bottom: 1px solid var(--primary-200);
  position: sticky;
  top: 0;
  z-index: 100;
  height: 60px;
  display: flex;
  align-items: center;
  padding: 0 2rem;
}

.header-inner {
  width: 100%; max-width: 1280px; margin: 0 auto;
  display: flex; align-items: center; justify-content: space-between;
}

/* Logo */
.logo {
  display: flex; align-items: center; gap: 9px;
  text-decoration: none;
}
.logo-icon {
  width: 32px; height: 32px;
  border-radius: var(--radius-sm);
  background: var(--primary-500);
  color: var(--white);
  font-family: var(--font-mono);
  font-weight: 800; font-size: 13px;
  display: flex; align-items: center; justify-content: center;
}
.logo-text {
  font-size: 16px; font-weight: 700;
  color: var(--primary-900);
}
.logo-text .accent { color: var(--primary-500); }

/* Nav */
.nav { display: flex; gap: 24px; }
.nav-link { font-size: 14px; font-weight: 500; color: var(--neutral-700); }
.nav-link:hover, .nav-link.active { color: var(--primary-500); text-decoration: none; }
.nav-link.active { border-bottom: 2px solid var(--primary-500); padding-bottom: 2px; }

/* Search bar trong header */
.header-search {
  display: flex; align-items: center;
  background: var(--neutral-100);
  border: 1px solid var(--neutral-300);
  border-radius: var(--radius-full);
  padding: 6px 14px; gap: 7px;
  font-size: 13px; color: var(--neutral-500);
}
.header-search:focus-within {
  border-color: var(--primary-500);
  box-shadow: 0 0 0 3px var(--primary-100);
}

@media (max-width: 768px) {
  .nav { display: none; }
  .nav.open {
    display: flex; flex-direction: column;
    position: absolute; top: 60px; left: 0; right: 0;
    background: var(--white);
    padding: 1rem 2rem;
    border-bottom: 1px solid var(--primary-200);
    z-index: 99;
  }
}
```

---

## 6. Footer

```css
.site-footer {
  background: var(--primary-950);
  color: var(--primary-300);
  padding: 3rem 2rem 1.5rem;
}
.footer-inner { max-width: 1280px; margin: 0 auto; }
.footer-logo { color: var(--white); font-size: 17px; font-weight: 700; }
.footer-logo .mono { font-family: var(--font-mono); color: var(--primary-400); }
.footer-desc { font-size: 13px; color: var(--primary-400); margin-top: 6px; max-width: 320px; }
.footer-heading { font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: .08em; color: var(--primary-300); margin-bottom: 10px; }
.footer-links a { display: block; color: var(--primary-400); font-size: 13px; margin-bottom: 6px; }
.footer-links a:hover { color: var(--white); text-decoration: none; }
.footer-bottom {
  border-top: 0.5px solid rgba(255,255,255,0.08);
  margin-top: 2.5rem; padding-top: 1rem;
  font-size: 12px; color: var(--primary-500);
  display: flex; justify-content: space-between;
}
```

---

## 7. Code Block (Syntax Highlight)

```css
/* Code block — nền tối */
.code-block {
  background: var(--code-bg);
  border-radius: var(--radius-lg);
  padding: 1.25rem 1.5rem;
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.75;
  overflow-x: auto;
  position: relative;
}

/* Header của code block (ngôn ngữ + copy button) */
.code-header {
  background: rgba(255,255,255,0.05);
  border-bottom: 0.5px solid rgba(255,255,255,0.08);
  padding: 6px 1.25rem;
  display: flex; justify-content: space-between;
  font-size: 11px; color: var(--primary-400);
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
}

/* Token colors */
.token-kw  { color: var(--code-kw);  } /* keyword: async, const, return */
.token-fn  { color: var(--code-fn);  } /* function name */
.token-str { color: var(--code-str); } /* string */
.token-num { color: var(--code-num); } /* number, boolean */
.token-cm  { color: var(--code-cm);  } /* comment */
.token-var { color: var(--code-var); } /* variable, default */

/* Code inline */
code {
  font-family: var(--font-mono);
  font-size: 0.875em;
  background: var(--primary-50);
  color: var(--primary-600);
  border: 0.5px solid var(--primary-200);
  border-radius: var(--radius-sm);
  padding: 2px 6px;
}

/* Terminal output */
.terminal {
  background: #0a0e1a;
  border-radius: var(--radius-lg);
  padding: 1rem 1.25rem;
  font-family: var(--font-mono);
  font-size: 13px;
  color: #a3e635;
  line-height: 1.6;
}
.terminal .prompt { color: var(--primary-400); }
.terminal .output { color: #94a3b8; }
```

---

## 8. Course Cards

```css
/* Card khóa học */
.course-card {
  background: var(--white);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  overflow: hidden;
  transition: box-shadow 0.2s, transform 0.2s;
}
.course-card:hover {
  box-shadow: 0 6px 20px rgba(19,127,236,0.15);
  transform: translateY(-2px);
}

/* Thumbnail / cover */
.course-thumb {
  height: 120px;
  background: linear-gradient(135deg, var(--primary-800), var(--primary-500));
  display: flex; align-items: center; justify-content: center;
  font-family: var(--font-mono);
  font-size: 32px; font-weight: 800;
  color: rgba(255,255,255,0.85);
}

.course-body { padding: 1rem 1.1rem; }
.course-meta { display: flex; gap: 6px; margin-bottom: 7px; flex-wrap: wrap; }
.course-title { font-size: 15px; font-weight: 600; color: var(--primary-900); margin-bottom: 4px; }
.course-info  { font-size: 12px; color: var(--neutral-500); }

/* Card stat */
.stat-card {
  background: var(--primary-50);
  border-left: 3px solid var(--primary-500);
  border-radius: var(--radius-md);
  padding: 1rem 1.25rem;
}
.stat-number { font-size: 28px; font-weight: 700; color: var(--primary-500); }
.stat-label  { font-size: 12px; color: var(--neutral-500); }

/* Card nội dung / module */
.lesson-card {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 1rem;
  background: var(--white);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
}
.lesson-num {
  width: 30px; height: 30px; border-radius: 50%;
  background: var(--primary-100); color: var(--primary-600);
  font-size: 12px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.lesson-num.done { background: var(--success-100); color: var(--success-600); }
```

---

## 9. Badges, Tags & Level Pills

```css
.badge {
  display: inline-block;
  font-size: 11px; font-weight: 600;
  padding: 3px 9px;
  border-radius: var(--radius-full);
}

/* Tech tags */
.badge-js        { background: #fef9c3; color: #854d0e; }        /* JavaScript */
.badge-ts        { background: var(--primary-100); color: var(--primary-700); } /* TypeScript */
.badge-py        { background: #dbeafe; color: #1d4ed8; }        /* Python */
.badge-react     { background: var(--accent-100); color: var(--accent-500); }   /* React/Vue */
.badge-html      { background: var(--warning-100); color: var(--warning-600); } /* HTML/CSS */
.badge-node      { background: var(--success-100); color: var(--success-600); } /* Node/Go */
.badge-general   { background: var(--primary-100); color: var(--primary-600); } /* generic */
.badge-dark      { background: var(--primary-900); color: var(--white); }

/* Level pill */
.level { display: inline-flex; align-items: center; gap: 4px; padding: 3px 9px; border-radius: var(--radius-full); font-size: 11px; font-weight: 600; }
.level::before { content: '●'; font-size: 8px; }
.level-beginner    { background: var(--success-100); color: var(--success-600); }
.level-intermediate{ background: var(--primary-100); color: var(--primary-600); }
.level-advanced    { background: var(--accent-100);  color: var(--accent-500); }
```

---

## 10. Progress Bar — Tiến độ học

```css
.progress-label {
  display: flex; justify-content: space-between;
  font-size: 13px; margin-bottom: 5px;
}
.progress-label .pct { color: var(--primary-500); font-weight: 600; }

.progress-track {
  height: 7px;
  background: var(--primary-100);
  border-radius: var(--radius-full);
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  border-radius: var(--radius-full);
  background: var(--primary-500);
  transition: width 0.4s ease;
}
.progress-fill.done { background: var(--success-600); }

/* XP Bar */
.xp-bar { height: 10px; background: var(--primary-100); border-radius: var(--radius-full); overflow: hidden; }
.xp-fill { height: 100%; border-radius: var(--radius-full); background: linear-gradient(90deg, var(--primary-500), var(--accent-400)); }
```

---

## 11. Hero Section

```css
.hero {
  background: linear-gradient(135deg, var(--primary-950) 0%, var(--primary-700) 60%, var(--primary-600) 100%);
  padding: 6rem 2rem;
  color: var(--white);
  position: relative;
  overflow: hidden;
}

/* Trang trí nền: ký tự code */
.hero::before {
  content: '{ }';
  position: absolute; right: 8%; top: 50%; transform: translateY(-50%);
  font-family: var(--font-mono);
  font-size: 140px; font-weight: 800;
  color: rgba(255,255,255,0.04);
  pointer-events: none;
}

.hero .eyebrow { color: var(--primary-300); }
.hero h1 { color: var(--white); font-size: 48px; }
.hero p  { color: var(--primary-200); font-size: 16px; max-width: 580px; }
.hero-actions { display: flex; gap: 12px; margin-top: 2rem; flex-wrap: wrap; }

/* Hero trên nền trắng (kiểu nhẹ hơn) */
.hero-light {
  background: var(--primary-50);
  border-bottom: 1px solid var(--primary-200);
  padding: 4rem 2rem;
}
.hero-light h1 { color: var(--primary-950); }
.hero-light p  { color: var(--neutral-700); }
```

---

## 12. Form Inputs

```css
.form-group { display: flex; flex-direction: column; gap: 5px; }
.form-label { font-size: 13px; font-weight: 500; color: var(--neutral-700); }

.form-input,
.form-select,
.form-textarea {
  font-family: var(--font-sans);
  font-size: 14px;
  color: var(--neutral-900);
  background: var(--white);
  border: 1.5px solid var(--neutral-300);
  border-radius: var(--radius-md);
  padding: 10px 14px;
  width: 100%;
  outline: none;
  transition: border-color 0.14s, box-shadow 0.14s;
}
.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  border-color: var(--primary-500);
  box-shadow: 0 0 0 3px var(--primary-100);
}
.form-input::placeholder { color: var(--neutral-500); }
.form-error { font-size: 12px; color: var(--danger-600); margin-top: 3px; }
.form-hint  { font-size: 12px; color: var(--neutral-500); margin-top: 3px; }

/* Input search */
.search-input {
  border-radius: var(--radius-full);
  padding: 9px 18px 9px 40px; /* chừa chỗ icon search */
}
```

---

## 13. Notifications / Toasts

```css
.toast {
  display: flex; align-items: center; gap: 9px;
  padding: 11px 15px;
  border-radius: var(--radius-md);
  font-size: 13px;
  border-left: 3px solid transparent;
}
.toast-success { background: var(--success-100); color: #166534; border-color: var(--success-600); }
.toast-info    { background: var(--primary-100); color: var(--primary-700); border-color: var(--primary-500); }
.toast-warning { background: var(--warning-100); color: #9a3412; border-color: var(--warning-600); }
.toast-error   { background: var(--danger-100);  color: #991b1b; border-color: var(--danger-600); }

/* Achievement toast */
.toast-xp {
  background: var(--primary-900);
  color: var(--white);
  border-left: 3px solid var(--primary-400);
}
```

---

## 14. Spacing & Layout

```css
/* Max-width container */
.container        { max-width: 1280px; margin: 0 auto; padding: 0 1.5rem; }
.container-md     { max-width: 860px;  margin: 0 auto; padding: 0 1.5rem; }
.container-narrow { max-width: 640px;  margin: 0 auto; padding: 0 1.5rem; }

/* Section */
.section    { padding: 5rem 0; }
.section-sm { padding: 3rem 0; }

/* Grid */
.grid-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; }
.grid-3 { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 1.25rem; }
.grid-4 { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 1rem; }

/* Divider */
.divider       { height: 0.5px; background: var(--primary-200); margin: 2rem 0; }
.divider-dark  { height: 0.5px; background: rgba(255,255,255,0.08); }

/* Nền xen kẽ */
.bg-alt        { background: var(--primary-50); }
.bg-dark       { background: var(--primary-950); }
.bg-dark-mid   { background: var(--primary-900); }

/* Sidebar layout */
.layout-sidebar {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 2rem;
  align-items: start;
}
@media (max-width: 900px) {
  .layout-sidebar { grid-template-columns: 1fr; }
}
```

---

## 15. Quy tắc dành cho AI Agent

Khi sinh code cho bất kỳ trang nào của website, **bắt buộc** tuân theo:

1. **Luôn dùng CSS variables** thay vì hardcode hex. Ví dụ: `color: var(--primary-500)` thay vì `color: #137fec`.
2. **Nền trang mặc định là trắng** (`var(--white)`). Dùng `var(--primary-50)` cho section xen kẽ.
3. **Button hành động chính** (bắt đầu học, đăng ký, submit) dùng `btn-primary` (xanh `#137fec`).
4. **Button Upgrade/Pro** dùng `btn-accent` (tím `#7c3aed`) — phân biệt rõ hành động trả phí.
5. **Button liên quan GitHub / Terminal** dùng `btn-dark` (xanh đêm `#061a38`).
6. **Header** luôn sticky, nền trắng, border-bottom `var(--primary-200)`. Logo có icon monospace `</>`.
7. **Footer** luôn nền `var(--primary-950)` (xanh đen gần tối).
8. **Code block** luôn dùng nền `var(--primary-950)` với syntax highlight. Code inline dùng nền `var(--primary-50)`.
9. **Level badge**: cơ bản = xanh lá, trung cấp = xanh primary, nâng cao = tím accent.
10. **Progress bar** học viên: fill `var(--primary-500)`. Khi hoàn thành 100% chuyển `var(--success-600)`.
11. **Tech tag badges**: mỗi công nghệ có màu riêng biệt (JS = vàng, Python = xanh dương, React = tím...).
12. **Font chính**: `Be Vietnam Pro` — phù hợp tiếng Việt, hiện đại. **Font code**: `Fira Code` hoặc `JetBrains Mono`.
13. **Hero section**: nền gradient tối `primary-950 → primary-600`, trang trí bằng ký tự `{ }` hoặc `</>`.
14. **Tuyệt đối không dùng màu tím accent làm màu brand chính** — chỉ dùng cho Pro/Upgrade/React badge.

---

*Design System v1.0 — DevLearn Website · Màu gốc rgb(19 127 236) = #137FEC*
