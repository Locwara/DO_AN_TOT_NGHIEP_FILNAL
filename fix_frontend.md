# fix_frontend.md — DevLearn Frontend Refactor Guide
> Dành cho **Codex / AI Agent** thực thi. Đọc kỹ từng phase trước khi bắt đầu.  
> Thi công theo thứ tự Phase 1 → 8. Sau mỗi phase: **đánh dấu ☑ và review** trước khi tiếp tục.  
> Màu brand gốc: `#137FEC` · Font chính: `Be Vietnam Pro` · Font code: `Fira Code`

---

## Mục lục

- [Phase 1 — CSS Foundation](#phase-1--css-foundation)
- [Phase 2 — Base Layout (`base.html`)](#phase-2--base-layout-basehtml)
- [Phase 3 — Navbar & Footer](#phase-3--navbar--footer)
- [Phase 4 — Shared Components](#phase-4--shared-components)
- [Phase 5 — Page Structure & Breadcrumbs](#phase-5--page-structure--breadcrumbs)
- [Phase 6 — Admin Layout](#phase-6--admin-layout)
- [Phase 7 — IDE Page](#phase-7--ide-page-solve_problemhtml)
- [Phase 8 — Accessibility & Final Polish](#phase-8--accessibility--final-polish)

---

## Checklist tổng quan

```
[x] Phase 1 — CSS Foundation
[x] Phase 2 — Base Layout
[x] Phase 3 — Navbar & Footer
[x] Phase 4 — Shared Components
[x] Phase 5 — Page Structure & Breadcrumbs
[x] Phase 6 — Admin Layout
[x] Phase 7 — IDE Page
[x] Phase 8 — Accessibility & Final Polish
```

---

## GHI CHÚ TƯƠNG THÍCH VỚI PROJECT HIỆN TẠI

Trước khi thực thi các phase bên dưới, agent phải giữ các ràng buộc thực tế của repo này:

1. **Profile relation đang là `user.profiles`, không phải `user.profile`.**  
   Trong template hiện tại dùng `user.profiles.role` và `user.profiles.avatar_url`. Không đổi sang `user.profile.*` nếu không sửa model/context.

2. **Namespace admin đang là `administation` và phải giữ nguyên.**  
   Đây là namespace đang hoạt động trong URL template, dù tên bị sai chính tả.

3. **Tailwind đang chạy bằng CDN:**  
   `https://cdn.tailwindcss.com?plugins=forms,container-queries` trong `base.html`. Không thêm `plugins: [tailwindcss_forms, ...]` vì các biến plugin đó không tồn tại trong setup CDN hiện tại.

4. **Breakpoint mobile của navbar là `900px`.**  
   CSS hiện tại ẩn `.nav` ở `max-width: 900px`, nên hamburger/drawer cũng phải hiện ở `<= 900px`. Không dùng `md:hidden` cho hamburger nếu chưa đồng bộ Tailwind screens, vì `md` mặc định là `768px`.

5. **Loading overlay hiện được `main.js` điều khiển qua `#global-loading`, `.global-loading__title`, class `.is-active`.**  
   Nếu tách `loading.html`, phải giữ markup/class này hoặc sửa `main.js` và `base.css` cùng lúc.

6. **Admin layout hiện dùng biến `current_page`.**  
   Khi tách sidebar, ưu tiên truyền `current_page=current_page` vào include, không đổi sang `admin_active_section` nếu không cần.

7. **Breadcrumb/page-header có thể cần sửa view để truyền context.**  
   Quy tắc "chỉ sửa template/static" chỉ áp dụng cho phase không cần context mới. Với breadcrumb hoặc admin active state, nếu view đã có `current_page` thì tận dụng; nếu chưa có `breadcrumbs`, được phép thêm context nhỏ, không đụng model/business logic.

8. **Không copy-paste snippet máy móc.**  
   Mỗi snippet là mẫu triển khai. Trước khi dán, đối chiếu với template thật để giữ link, permission, notification badge, avatar, CodeMirror/IDE script và block Django đang dùng.

---

## VẤN ĐỀ HIỆN TẠI (Tóm tắt chẩn đoán)

Giảng viên nhận xét "hơi rối mắt" — dưới đây là các nguyên nhân gốc rễ:

| # | Vấn đề | Tác động |
|---|--------|----------|
| 1 | CSS variables khai báo **2 lần**: trong `<style>` inline của `base.html` VÀ trong `base.css` | Giá trị có thể bị ghi đè lẫn nhau, khó debug |
| 2 | **Ba hệ thống CSS cùng tồn tại**: Tailwind CDN utility + `.btn/.card` custom + inline style riêng từng trang | Không nhất quán, class trùng tên, specificity xung đột |
| 3 | Navbar mobile chỉ **ẩn `.nav`**, không có hamburger / drawer | Người dùng mobile mất navigation |
| 4 | Không có **breadcrumb** và **page-header** dùng chung | Mỗi trang tự làm kiểu khác nhau → rối mắt |
| 5 | Admin sidebar **không được tách** thành include riêng | Admin pages dài, khó đọc, khó bảo trì |
| 6 | Toast và loading overlay **nằm inline** trong `base.html` | base.html quá dài, khó maintain |
| 7 | IDE page (`solve_problem.html`) không kế thừa `base.html` nhưng **định nghĩa lại CSS variables** lần nữa | Drift khỏi design system |
| 8 | Thiếu **`aria-label`**, skip link, focus ring rõ ràng | Accessibility yếu, không đạt WCAG AA |
| 9 | `font-family: 'Fira Code'` nhưng design system mới dùng `'Cascadia Code', 'Fira Code'` | Không đồng bộ giữa các file |
| 10 | Tailwind config `theme.extend` thiếu một số token (radius, shadow) — phải hardcode | Không tận dụng được Tailwind |

---

## QUYỀN LỢI SAU KHI FIX

- **Một nguồn sự thật duy nhất** cho màu sắc, typography, spacing
- Navbar mobile hoạt động đúng
- Mọi trang đều dùng chung page-header, breadcrumb, toast
- Admin có sidebar component sạch
- IDE giữ được design system nhưng vẫn full-screen
- Đạt WCAG AA cơ bản

---

---

# Phase 1 — CSS Foundation

> **Mục tiêu:** Một file CSS duy nhất làm nguồn sự thật. Xóa trùng lặp, thống nhất tokens.  
> **Files cần chỉnh:** `static/css/base.css`, `templates/base.html` (`<style>` block), `tailwind.config` trong head.

---

### 1.1 Consolidate CSS Variables

**VẤN ĐỀ:** `:root { }` đang tồn tại trong cả `<style>` của `base.html` lẫn `base.css`. Khi một giá trị thay đổi ở một nơi, nơi kia không cập nhật.

**FIX:** Xóa hoàn toàn khối `:root { }` trong `<style>` inline của `base.html`. Chỉ giữ một nơi duy nhất là đầu file `static/css/base.css`.

Nội dung `:root` chuẩn (dán vào đầu `base.css`, thay thế mọi định nghĩa cũ):

```css
/* ============================================================
   DEVLEARN — CSS VARIABLES (Single Source of Truth)
   Tuyệt đối KHÔNG khai báo lại ở nơi khác.
   ============================================================ */
:root {
  /* PRIMARY */
  --primary-950: #020d1f;
  --primary-900: #061a38;
  --primary-800: #0b2d60;
  --primary-700: #0f4289;
  --primary-600: #1260c0;
  --primary-500: #137fec;   /* ★ BRAND CHÍNH */
  --primary-400: #3d9af5;
  --primary-300: #78bcfa;
  --primary-200: #b8d9fd;
  --primary-100: #daeefe;
  --primary-50:  #f0f8ff;

  /* ACCENT */
  --accent-500: #7c3aed;
  --accent-400: #8b5cf6;
  --accent-100: #ede9fe;

  /* SEMANTIC */
  --success-600: #16a34a;
  --success-100: #f0fdf4;
  --warning-600: #ea580c;
  --warning-100: #fff7ed;
  --danger-600:  #dc2626;
  --danger-100:  #fef2f2;

  /* NEUTRAL */
  --neutral-900: #0f172a;
  --neutral-700: #334155;
  --neutral-500: #64748b;
  --neutral-300: #cbd5e1;
  --neutral-100: #f8fafc;
  --white:       #ffffff;

  /* CODE SYNTAX */
  --code-bg:  #020d1f;
  --code-kw:  #7dd3fc;
  --code-fn:  #bef264;
  --code-str: #fdba74;
  --code-num: #c084fc;
  --code-cm:  #475569;
  --code-var: #e2e8f0;

  /* SHAPE */
  --radius-sm:   5px;
  --radius-md:   9px;
  --radius-lg:   14px;
  --radius-xl:   22px;
  --radius-full: 9999px;

  /* SHADOWS */
  --shadow-card:  0 1px 3px rgba(19,127,236,0.08), 0 0 0 0.5px rgba(19,127,236,0.10);
  --shadow-btn:   0 2px 8px rgba(19,127,236,0.30);
  --shadow-modal: 0 8px 32px rgba(6,26,56,0.20);

  /* TYPOGRAPHY */
  --font-sans: 'Be Vietnam Pro', 'Inter', system-ui, sans-serif;
  --font-mono: 'Cascadia Code', 'Fira Code', 'JetBrains Mono', monospace;

  /* LAYOUT */
  --header-h: 60px;
  --sidebar-w: 260px;
}
```

> ⚠️ Lưu ý: thêm `--header-h` và `--sidebar-w` vào `:root` để dùng thống nhất thay vì hardcode `60px`, `260px` rải rác.

---

### 1.2 Cập nhật `tailwind.config` trong `base.html`

Thay thế block `tailwind.config` hiện tại bằng version đồng bộ với CSS variables, nhưng **giữ cách dùng Tailwind CDN hiện tại**:

```html
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
```

Không thêm `plugins: [tailwindcss_forms, tailwindcss_containerQueries]` vào config vì repo không build Tailwind bằng npm. Nếu cần breakpoint riêng cho navbar, thêm `screens.nav = '900px'` hoặc dùng CSS thuần cho hamburger.

```html
<script>
tailwind.config = {
  theme: {
    extend: {
      colors: {
        primary: {
          50:  '#f0f8ff', 100: '#daeefe', 200: '#b8d9fd',
          300: '#78bcfa', 400: '#3d9af5', 500: '#137fec',
          600: '#1260c0', 700: '#0f4289', 800: '#0b2d60',
          900: '#061a38', 950: '#020d1f',
        },
        accent: { 100: '#ede9fe', 400: '#8b5cf6', 500: '#7c3aed' },
        success: { 100: '#f0fdf4', 600: '#16a34a' },
        warning: { 100: '#fff7ed', 600: '#ea580c' },
        danger:  { 100: '#fef2f2', 600: '#dc2626' },
        neutral: {
          100: '#f8fafc', 300: '#cbd5e1', 500: '#64748b',
          700: '#334155', 900: '#0f172a',
        },
      },
      fontFamily: {
        sans: ['Be Vietnam Pro', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['Cascadia Code', 'Fira Code', 'JetBrains Mono', 'monospace'],
      },
      borderRadius: {
        sm: '5px', DEFAULT: '9px', md: '9px',
        lg: '14px', xl: '22px', full: '9999px',
      },
      boxShadow: {
        card:  '0 1px 3px rgba(19,127,236,0.08), 0 0 0 0.5px rgba(19,127,236,0.10)',
        btn:   '0 2px 8px rgba(19,127,236,0.30)',
        modal: '0 8px 32px rgba(6,26,56,0.20)',
      },
      screens: {
        nav: '900px',
      },
    },
  },
}
</script>
```

> Bây giờ Tailwind utility class như `bg-primary-500`, `text-accent-500`, `rounded-md`, `shadow-card` sẽ dùng đúng token của design system.

---

### 1.3 Cập nhật Google Fonts import

Trong `base.html`, đổi `<link>` Google Fonts thành:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
```

> Lý do `preconnect`: giảm thời gian tải font (giảng viên sẽ thấy trang load nhanh hơn).

---

### 1.4 Giảm hardcode hex trong `base.css`

Sau khi `base.css` đã có `:root`, duyệt toàn file và:
- Thay mọi `#137fec` → `var(--primary-500)`
- Thay mọi `#1260c0` → `var(--primary-600)`
- Thay mọi `#020d1f` → `var(--primary-950)`
- Thay mọi `#16a34a` → `var(--success-600)`
- Thay mọi `#ea580c` → `var(--warning-600)`
- Thay mọi `#dc2626` → `var(--danger-600)`
- Thay mọi `#7c3aed` → `var(--accent-500)`

Không thay máy móc các màu semantic nhạt đang dùng cho trạng thái riêng nếu token hiện tại chưa có màu tương đương. Ví dụ: màu nền badge, highlight testcase, trạng thái warning/success có thể giữ lại tạm thời hoặc bổ sung token trước rồi mới đổi.

---

### ✅ Checklist Phase 1

```
[x] 1.1 — Xóa :root khỏi <style> inline trong base.html
[x] 1.1 — Dán :root đầy đủ vào đầu base.css (thêm --header-h, --sidebar-w)
[x] 1.2 — Cập nhật tailwind.config với đầy đủ tokens
[x] 1.3 — Thêm preconnect cho Google Fonts
[x] 1.4 — Thay hardcode hex theme chính bằng CSS variables trong base.css; giữ lại màu semantic/editor đặc thù theo ghi chú tương thích
[x] REVIEW: Mở trang chủ, inspect element, kiểm tra các màu đúng không
[x] REVIEW: Không còn :root nào ngoài base.css
```

---

---

# Phase 2 — Base Layout (`base.html`)

> **Mục tiêu:** `base.html` gọn gàng, cấu trúc rõ ràng, tách toast và loading ra include riêng.  
> **Files cần chỉnh:** `templates/base.html`, tạo mới `templates/includes/toast.html`, `templates/includes/loading.html`

---

### 2.1 Tách Toast ra `includes/toast.html`

Tạo file `templates/includes/toast.html`:

```html
{# includes/toast.html — Django messages / toast notifications #}
{% if messages %}
<div
  id="toast-container"
  class="fixed top-[calc(var(--header-h)+12px)] right-4 z-[200] flex flex-col gap-2 max-w-sm w-full"
  role="region"
  aria-label="Thông báo hệ thống"
  aria-live="polite"
>
  {% for message in messages %}
  <div
    class="toast toast-{{ message.tags|default:'info' }} flex items-center gap-3 px-4 py-3 rounded-md text-sm shadow-modal transition-all duration-300"
    role="alert"
    data-autohide="5000"
  >
    {# Icon theo loại #}
    {% if message.tags == 'success' %}
      <span class="material-symbols-outlined text-[18px] shrink-0" aria-hidden="true">check_circle</span>
    {% elif message.tags == 'error' or message.tags == 'danger' %}
      <span class="material-symbols-outlined text-[18px] shrink-0" aria-hidden="true">error</span>
    {% elif message.tags == 'warning' %}
      <span class="material-symbols-outlined text-[18px] shrink-0" aria-hidden="true">warning</span>
    {% else %}
      <span class="material-symbols-outlined text-[18px] shrink-0" aria-hidden="true">info</span>
    {% endif %}

    <span class="flex-1">{{ message }}</span>

    <button
      type="button"
      class="btn-icon w-6 h-6 text-[14px] shrink-0 opacity-60 hover:opacity-100"
      onclick="this.closest('[role=alert]').remove()"
      aria-label="Đóng thông báo"
    >
      <span class="material-symbols-outlined" aria-hidden="true">close</span>
    </button>
  </div>
  {% endfor %}
</div>
{% endif %}
```

> Thêm CSS cho các class `.toast-*` vào `base.css` (xem Phase 4.5).

---

### 2.2 Tách Loading Overlay ra `includes/loading.html`

Tạo file `templates/includes/loading.html`:

```html
{# includes/loading.html — Global loading overlay #}
<div id="global-loading" class="global-loading" role="status" aria-live="polite" aria-hidden="true">
  <div class="global-loading__card">
    <div class="global-loading__spinner" aria-hidden="true"></div>
    <div>
      <div class="global-loading__title">Đang xử lý</div>
      <div class="global-loading__hint">Vui lòng chờ trong giây lát...</div>
    </div>
  </div>
</div>
```

> Markup này cố ý giữ class hiện tại vì `static/js/main.js` đang cập nhật `.global-loading__title` và bật/tắt class `.is-active`.

---

### 2.3 Tạo Skip Link (accessibility)

Thêm **đầu tiên** trong `<body>` của `base.html`, trước mọi thứ khác:

```html
<a
  href="#main-content"
  class="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2
         focus:z-[9999] focus:bg-primary-500 focus:text-white focus:px-4
         focus:py-2 focus:rounded-md focus:text-sm focus:font-medium"
>
  Chuyển đến nội dung chính
</a>
```

---

### 2.4 Cấu trúc `<body>` chuẩn sau khi refactor

```html
<body class="bg-background-light font-display text-slate-900 min-h-screen">

  {# 1. Skip link (accessibility) #}
  <a href="#main-content" class="sr-only focus:not-sr-only ...">Chuyển đến nội dung chính</a>

  <div class="relative flex min-h-screen w-full flex-col overflow-x-hidden">
    <div class="layout-container flex h-full grow flex-col">
      {# 2. Navbar #}
      {% include "includes/navbar.html" %}

      {# 3. Toast notifications #}
      {% include "includes/toast.html" %}

      {# 4. Main content #}
      <main id="main-content" class="flex-1" tabindex="-1">
        {% block content %}{% endblock %}
      </main>

      {# 5. Footer #}
      {% include "includes/footer.html" %}
    </div>
  </div>

  {# 6. Loading overlay #}
  {% include "includes/loading.html" %}

  {# 7. Scripts #}
  <script src="{% static 'js/main.js' %}" defer></script>
  {% block extra_js %}{% endblock %}

</body>
```

> **Lưu ý:** `<main id="main-content" tabindex="-1">` — `tabindex="-1"` cho phép skip link focus vào main mà không thêm nó vào tab order.

---

### 2.5 Tailwind safelist

Với Tailwind CDN hiện tại, safelist không quan trọng như setup build/purge. Ưu tiên viết style toast bằng CSS thật trong `base.css`:

```css
.toast-success { ... }
.toast-error { ... }
.toast-warning { ... }
.toast-info { ... }
```

Nếu sau này chuyển sang build Tailwind bằng npm, lúc đó mới thêm safelist:

```js
safelist: [
  'toast-success', 'toast-error', 'toast-warning', 'toast-info', 'toast-danger',
  'bg-primary-500', 'bg-accent-500',
],
```

---

### ✅ Checklist Phase 2

```
[x] 2.1 — Tạo templates/includes/toast.html với icon + auto-hide attribute
[x] 2.2 — Tạo templates/includes/loading.html với spinner animation
[x] 2.3 — Thêm skip link đầu <body>
[x] 2.4 — Refactor <body> base.html theo thứ tự đúng
[x] 2.5 — Toast style nằm trong base.css; safelist chỉ cần nếu chuyển sang Tailwind build
[x] REVIEW: Thử Django message (success/error/warning) — toast render đúng class màu
[x] REVIEW: Thử click link — loading overlay xuất hiện rồi biến mất không?
[x] REVIEW: Dùng Tab key — skip link xuất hiện khi focus vào không?
```

---

---

# Phase 3 — Navbar & Footer

> **Mục tiêu:** Navbar có hamburger menu hoạt động trên mobile. Footer nhất quán.  
> **Files cần chỉnh:** `templates/includes/navbar.html`, `templates/includes/footer.html`

---

### 3.1 Hamburger Menu cho Navbar Mobile

**VẤN ĐỀ hiện tại:** Khi viewport <= 900px, `.nav` ẩn đi hoàn toàn. Người dùng mobile không có cách nào dùng navigation.

**FIX:** Thêm hamburger button và mobile drawer.

#### 3.1.1 Thêm hamburger button vào phần actions bên phải của navbar:

```html
{# Hamburger — chỉ hiện trên mobile #}
<button
  id="nav-hamburger"
  class="btn-icon mobile-menu-trigger"
  aria-label="Mở menu điều hướng"
  aria-expanded="false"
  aria-controls="mobile-drawer"
>
  <span class="material-symbols-outlined" id="hamburger-icon" aria-hidden="true">menu</span>
</button>
```

Thêm CSS để đồng bộ với breakpoint thật của repo:

```css
.mobile-menu-trigger { display: none; }
@media (max-width: 900px) {
  .mobile-menu-trigger { display: inline-flex; }
}
```

#### 3.1.2 Thêm Mobile Drawer ngay sau `</header>` trong navbar.html:

```html
{# Mobile Navigation Drawer #}
<div
  id="mobile-drawer"
  class="fixed inset-0 z-[150] hidden"
  aria-hidden="true"
>
  {# Overlay backdrop #}
  <div
    id="drawer-backdrop"
    class="absolute inset-0 bg-primary-950/60 backdrop-blur-sm"
  ></div>

  {# Drawer panel #}
  <nav
    class="absolute top-0 right-0 h-full w-72 bg-white shadow-modal
           flex flex-col pt-[var(--header-h)] overflow-y-auto"
    aria-label="Menu điều hướng di động"
  >
    {# Close button #}
    <button
      id="drawer-close"
      class="absolute top-3 right-4 btn-icon"
      aria-label="Đóng menu"
    >
      <span class="material-symbols-outlined" aria-hidden="true">close</span>
    </button>

    <div class="flex flex-col gap-1 px-4 py-4">
      {% if user.is_authenticated %}
        {# Avatar + tên #}
        <div class="flex items-center gap-3 mb-4 pb-4 border-b border-primary-100">
          {% if user.profiles.avatar_url %}
            <div class="w-9 h-9 rounded-full bg-center bg-cover border border-primary-100"
                 style="background-image: url('{{ user.profiles.avatar_url }}');"
                 aria-hidden="true"></div>
          {% else %}
            <div class="w-9 h-9 rounded-full bg-primary-500 text-white text-sm font-bold flex items-center justify-center">
              {{ user.first_name|first|default:user.username|first|upper }}
            </div>
          {% endif %}
          <div>
            <p class="text-sm font-semibold text-neutral-900">{{ user.get_full_name|default:user.username }}</p>
            <p class="text-xs text-neutral-500">{{ user.email }}</p>
          </div>
        </div>

        {# Nav links theo role #}
        {% if user.is_superuser or user.profiles.role == 'admin' %}
          <a href="{% url 'administation:dashboard' %}" class="drawer-link">
            <span class="material-symbols-outlined" aria-hidden="true">admin_panel_settings</span>
            Dashboard Admin
          </a>
        {% elif user.profiles.role == 'teacher' %}
          <a href="{% url 'accounts:teacher_dashboard' %}" class="drawer-link">
            <span class="material-symbols-outlined" aria-hidden="true">school</span>
            Dashboard Giáo viên
          </a>
          <a href="{% url 'classrooms:create' %}" class="drawer-link">
            <span class="material-symbols-outlined" aria-hidden="true">add_circle</span>
            Tạo lớp
          </a>
        {% else %}
          <a href="{% url 'accounts:student_dashboard' %}" class="drawer-link">
            <span class="material-symbols-outlined" aria-hidden="true">dashboard</span>
            Dashboard Học sinh
          </a>
        {% endif %}

        <a href="{% url 'classrooms:classroom_list' %}" class="drawer-link">
          <span class="material-symbols-outlined" aria-hidden="true">class</span>
          Lớp học
        </a>
        <a href="{% url 'assignments:calendar' %}" class="drawer-link">
          <span class="material-symbols-outlined" aria-hidden="true">calendar_month</span>
          Lịch
        </a>
        <a href="{% url 'notifications:list' %}" class="drawer-link">
          <span class="material-symbols-outlined" aria-hidden="true">notifications</span>
          Thông báo
        </a>

        <div class="border-t border-primary-100 my-2"></div>

        <a href="{% url 'accounts:profile' %}" class="drawer-link">
          <span class="material-symbols-outlined" aria-hidden="true">person</span>
          Hồ sơ
        </a>
        <a href="{% url 'accounts:logout' %}" class="drawer-link text-danger-600 hover:bg-danger-100">
          <span class="material-symbols-outlined" aria-hidden="true">logout</span>
          Đăng xuất
        </a>

      {% else %}
        <a href="#features" class="drawer-link">Tính năng</a>
        <a href="#ide" class="drawer-link">IDE</a>
        <a href="#community" class="drawer-link">Cộng đồng</a>
        <div class="border-t border-primary-100 my-2"></div>
        <a href="{% url 'accounts:login' %}" class="btn btn-outline w-full justify-center">Đăng nhập</a>
        <a href="{% url 'accounts:register' %}" class="btn btn-primary w-full justify-center mt-2">Đăng ký</a>
      {% endif %}
    </div>
  </nav>
</div>
```

#### 3.1.3 Thêm CSS cho `.drawer-link` vào `base.css`:

```css
.drawer-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 500;
  color: var(--neutral-700);
  text-decoration: none;
  transition: background 0.14s, color 0.14s;
}
.drawer-link:hover {
  background: var(--primary-50);
  color: var(--primary-600);
  text-decoration: none;
}
.drawer-link .material-symbols-outlined {
  font-size: 20px;
  color: var(--neutral-500);
}
```

#### 3.1.4 Thêm JS điều khiển drawer vào `main.js`:

```js
// ============================================================
// Mobile Navigation Drawer
// ============================================================
function openMobileDrawer() {
  const drawer = document.getElementById('mobile-drawer');
  const hamburger = document.getElementById('nav-hamburger');
  const icon = document.getElementById('hamburger-icon');
  if (!drawer) return;
  drawer.classList.remove('hidden');
  drawer.setAttribute('aria-hidden', 'false');
  hamburger.setAttribute('aria-expanded', 'true');
  icon.textContent = 'close';
  document.body.style.overflow = 'hidden';  // Khóa scroll
}

function closeMobileDrawer() {
  const drawer = document.getElementById('mobile-drawer');
  const hamburger = document.getElementById('nav-hamburger');
  const icon = document.getElementById('hamburger-icon');
  if (!drawer) return;
  drawer.classList.add('hidden');
  drawer.setAttribute('aria-hidden', 'true');
  hamburger.setAttribute('aria-expanded', 'false');
  icon.textContent = 'menu';
  document.body.style.overflow = '';
}

document.getElementById('nav-hamburger')?.addEventListener('click', openMobileDrawer);
document.getElementById('drawer-backdrop')?.addEventListener('click', closeMobileDrawer);
document.getElementById('drawer-close')?.addEventListener('click', closeMobileDrawer);

// Đóng drawer khi nhấn Escape
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeMobileDrawer();
});
```

> `main.js` hiện đang bọc nhiều logic trong IIFE. Có thể đặt block drawer này sau IIFE, hoặc nếu đặt trong IIFE thì không dùng inline `onclick`; chỉ dùng event listener như snippet trên.

---

### 3.2 Chuẩn hóa Desktop Navbar

Đảm bảo header desktop dùng đúng class:

```html
<header class="site-header" role="banner">
  <div class="header-inner">
    {# Logo #}
    <a href="{% url 'home' %}" class="logo" aria-label="DevLearn - Về trang chủ">
      <span class="logo-icon" aria-hidden="true">&lt;/&gt;</span>
      <span class="logo-text">Dev<span>Learn</span></span>
    </a>

    {# Desktop nav — base.css tự ẩn ở <= 900px #}
    <nav class="nav" aria-label="Điều hướng chính">
      {# ... các link nav ... #}
    </nav>

    {# Actions #}
    <div class="header-actions">
      {# ... buttons + notifications + avatar ... #}
      {# Hamburger button (3.1.1) #}
    </div>
  </div>
</header>
```

---

### 3.3 Footer — chuẩn hóa grid

Đảm bảo footer dùng đúng grid responsive:

```html
<footer class="bg-primary-950 text-primary-300" role="contentinfo">
  <div class="container py-12">
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8 mb-10">
      {# Cột 1: Logo + mô tả #}
      {# Cột 2: Sản phẩm #}
      {# Cột 3: Học tập #}
      {# Cột 4: Tài khoản #}
    </div>
    <div class="divider-dark"></div>
    <div class="flex flex-col sm:flex-row items-center justify-between gap-2 pt-6 text-xs text-primary-400">
      <p>© 2026 DevLearn. Học lập trình, không giới hạn.</p>
      <p>Made with ❤️ in Vietnam</p>
    </div>
  </div>
</footer>
```

---

### ✅ Checklist Phase 3

```
[x] 3.1.1 — Thêm hamburger button vào navbar (hiện ở <= 900px)
[x] 3.1.2 — Thêm mobile drawer HTML vào navbar.html
[x] 3.1.3 — Thêm .drawer-link CSS vào base.css
[x] 3.1.4 — Thêm openMobileDrawer/closeMobileDrawer vào main.js
[x] 3.2 — Navbar desktop dùng role="banner", aria-label đúng
[x] 3.3 — Footer dùng grid-cols-4 trên lg, 1 cột trên mobile
[x] REVIEW: Thu nhỏ viewport < 900px — hamburger xuất hiện không?
[x] REVIEW: Click hamburger — drawer mở ra từ phải không?
[x] REVIEW: Nhấn Escape — drawer đóng không?
[x] REVIEW: Tab qua các link trong drawer hoạt động không?
```

---

---

# Phase 4 — Shared Components

> **Mục tiêu:** Mọi component (button, card, badge, form, toast) dùng CSS variables, không hardcode. Thống nhất class naming.  
> **Files cần chỉnh:** `static/css/base.css`

---

### 4.1 Buttons — chuẩn hóa

Đảm bảo tất cả button class trong `base.css` khớp chính xác với design system:

```css
/* ============================================================
   BUTTONS
   ============================================================ */
.btn {
  font-family: var(--font-sans);
  font-size: 14px;
  font-weight: 500;
  line-height: 1;
  cursor: pointer;
  border: none;
  border-radius: var(--radius-md);
  transition: background 0.14s, transform 0.1s, box-shadow 0.14s;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  text-decoration: none;
  white-space: nowrap;
}
.btn:active { transform: scale(0.97); }
.btn:focus-visible {
  outline: 3px solid var(--primary-300);
  outline-offset: 2px;
}

.btn-primary {
  background: var(--primary-600);
  color: var(--white);
  padding: 10px 22px;
  box-shadow: var(--shadow-btn);
}
.btn-primary:hover { background: var(--primary-700); color: var(--white); text-decoration: none; }

.btn-accent {
  background: var(--accent-500);
  color: var(--white);
  padding: 10px 22px;
}
.btn-accent:hover { background: var(--accent-400); color: var(--white); text-decoration: none; }

.btn-dark {
  background: var(--primary-900);
  color: var(--white);
  padding: 10px 22px;
}
.btn-dark:hover { background: var(--primary-950); color: var(--white); text-decoration: none; }

.btn-outline {
  background: transparent;
  color: var(--primary-500);
  padding: 9px 20px;
  border: 1.5px solid var(--primary-500);
}
.btn-outline:hover { background: var(--primary-50); text-decoration: none; }

.btn-ghost {
  background: transparent;
  color: var(--primary-600);
  padding: 9px 16px;
}
.btn-ghost:hover { background: var(--primary-100); text-decoration: none; }

.btn-sm {
  background: var(--primary-100);
  color: var(--primary-600);
  padding: 5px 12px;
  font-size: 12px;
  font-weight: 600;
  border-radius: var(--radius-sm);
}

.btn-danger {
  background: var(--danger-600);
  color: var(--white);
  padding: 9px 18px;
}
.btn-danger:hover { background: #b91c1c; color: var(--white); text-decoration: none; }

.btn-icon {
  width: 38px; height: 38px;
  border-radius: 50%;
  background: var(--primary-100);
  color: var(--primary-500);
  display: flex; align-items: center; justify-content: center;
  font-size: 17px;
  border: none;
  cursor: pointer;
  transition: background 0.14s;
  flex-shrink: 0;
}
.btn-icon:hover { background: var(--primary-200); }
.btn-icon:focus-visible { outline: 3px solid var(--primary-300); outline-offset: 2px; }
```

---

### 4.2 Cards

```css
/* ============================================================
   CARDS
   ============================================================ */
.card {
  background: var(--white);
  border: 1px solid var(--primary-100);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  padding: 1.25rem;
}

/* Card khóa học */
.course-card {
  background: var(--white);
  border: 1px solid var(--primary-100);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: transform 0.2s, box-shadow 0.2s;
}
.course-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(19,127,236,0.15);
}
.course-card-body { padding: 1rem 1.25rem; flex: 1; }
.course-card-footer {
  padding: 0.75rem 1.25rem;
  border-top: 1px solid var(--primary-50);
  background: var(--neutral-100);
}

/* Card thống kê */
.stat-card {
  background: var(--primary-50);
  border-left: 3px solid var(--primary-500);
  border-radius: var(--radius-md);
  padding: 1rem 1.25rem;
}
.stat-number { font-size: 28px; font-weight: 700; color: var(--primary-500); line-height: 1; }
.stat-label  { font-size: 12px; color: var(--neutral-500); margin-top: 4px; }

/* Card success (bài đã hoàn thành) */
.stat-card.success {
  border-left-color: var(--success-600);
  background: var(--success-100);
}
.stat-card.success .stat-number { color: var(--success-600); }

/* Card warning */
.stat-card.warning {
  border-left-color: var(--warning-600);
  background: var(--warning-100);
}
.stat-card.warning .stat-number { color: var(--warning-600); }
```

---

### 4.3 Badges & Level Pills

```css
/* ============================================================
   BADGES & LEVEL PILLS
   ============================================================ */
.badge {
  display: inline-flex;
  align-items: center;
  font-size: 11px;
  font-weight: 600;
  padding: 3px 9px;
  border-radius: var(--radius-full);
  white-space: nowrap;
  line-height: 1.4;
}

/* Tech language badges */
.badge-js      { background: #fef9c3; color: #854d0e; }
.badge-ts      { background: var(--primary-100); color: var(--primary-700); }
.badge-py      { background: #dbeafe; color: #1d4ed8; }
.badge-react   { background: var(--accent-100); color: var(--accent-500); }
.badge-html    { background: var(--warning-100); color: var(--warning-600); }
.badge-node    { background: var(--success-100); color: var(--success-600); }
.badge-general { background: var(--primary-100); color: var(--primary-600); }
.badge-dark    { background: var(--primary-900); color: var(--white); }

/* Status badges */
.badge-success { background: var(--success-100); color: var(--success-600); }
.badge-warning { background: var(--warning-100); color: var(--warning-600); }
.badge-danger  { background: var(--danger-100);  color: var(--danger-600); }
.badge-info    { background: var(--primary-100); color: var(--primary-700); }

/* Level pill */
.level {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 10px;
  border-radius: var(--radius-full);
  font-size: 11px;
  font-weight: 600;
}
.level::before { content: '●'; font-size: 7px; line-height: 1; }
.level-beginner     { background: var(--success-100); color: var(--success-600); }
.level-intermediate { background: var(--primary-100); color: var(--primary-600); }
.level-advanced     { background: var(--accent-100);  color: var(--accent-500); }
```

---

### 4.4 Form Inputs

```css
/* ============================================================
   FORMS
   ============================================================ */
.form-group   { display: flex; flex-direction: column; gap: 5px; }
.form-label   { font-size: 13px; font-weight: 500; color: var(--neutral-700); }
.form-hint    { font-size: 12px; color: var(--neutral-500); margin-top: 3px; }
.form-error   { font-size: 12px; color: var(--danger-600); margin-top: 3px; display: flex; align-items: center; gap: 4px; }

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
.form-input::placeholder,
.form-textarea::placeholder { color: var(--neutral-500); }
.form-input.error,
.form-select.error,
.form-textarea.error {
  border-color: var(--danger-600);
  box-shadow: 0 0 0 3px var(--danger-100);
}

/* Search input */
.search-input {
  border-radius: var(--radius-full);
  padding: 9px 18px 9px 40px;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2364748b'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: 14px center;
  background-size: 16px;
}
```

---

### 4.5 Toast CSS (dùng với `includes/toast.html` ở Phase 2.1)

```css
/* ============================================================
   TOASTS
   ============================================================ */
.toast {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 11px 15px;
  border-radius: var(--radius-md);
  font-size: 13px;
  border-left: 3px solid transparent;
  box-shadow: var(--shadow-modal);
}
.toast-success { background: var(--success-100); color: #166534; border-color: var(--success-600); }
.toast-info    { background: var(--primary-100); color: var(--primary-700); border-color: var(--primary-500); }
.toast-warning { background: var(--warning-100); color: #9a3412; border-color: var(--warning-600); }
.toast-error,
.toast-danger  { background: var(--danger-100); color: #991b1b; border-color: var(--danger-600); }
.toast-xp {
  background: var(--primary-900);
  color: var(--white);
  border-left-color: var(--primary-400);
}
```

---

### 4.6 Progress Bars

```css
/* ============================================================
   PROGRESS BARS
   ============================================================ */
.progress-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  margin-bottom: 6px;
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
  transition: width 0.5s ease;
}
.progress-fill.done  { background: var(--success-600); }
.progress-fill.warn  { background: var(--warning-600); }

/* XP Bar */
.xp-bar  { height: 10px; background: var(--primary-100); border-radius: var(--radius-full); overflow: hidden; }
.xp-fill { height: 100%; border-radius: var(--radius-full); background: linear-gradient(90deg, var(--primary-500), var(--accent-400)); }
```

---

### ✅ Checklist Phase 4

```
[x] 4.1 — Cập nhật toàn bộ .btn* trong base.css, thêm focus-visible
[x] 4.2 — Cập nhật .card, .course-card, .stat-card với stat-card.success/warning
[x] 4.3 — Cập nhật badges: thêm .badge-success/warning/danger/info
[x] 4.4 — Cập nhật form inputs, thêm .form-input.error state
[x] 4.5 — Thêm CSS toast vào base.css
[x] 4.6 — Thêm progress bar CSS vào base.css
[x] REVIEW: Mở trang có button — kiểm tra hover, focus ring, active scale
[x] REVIEW: Mở trang có form — kiểm tra focus state xanh rõ ràng
[x] REVIEW: Mở trang có badge — kiểm tra badge-success/warning/danger đúng màu
```

---

---

# Phase 5 — Page Structure & Breadcrumbs

> **Mục tiêu:** Mọi trang nội dung dùng page-header và breadcrumb nhất quán.  
> **Files:** Tạo `templates/includes/page_header.html`, `templates/includes/breadcrumb.html`, cập nhật `base.css`

---

### 5.1 Tạo `includes/breadcrumb.html`

```html
{#
  includes/breadcrumb.html
  Usage:
    {% include "includes/breadcrumb.html" with crumbs=breadcrumbs %}
  
  breadcrumbs là list of dict: [{'label': 'Lớp học', 'url': '/classrooms/'}, {'label': 'Lớp A'}]
  Item cuối cùng (không có url) là trang hiện tại.
#}
{% if crumbs %}
<nav aria-label="Đường dẫn điều hướng" class="breadcrumb-nav">
  <ol class="breadcrumb" role="list">
    <li class="breadcrumb-item">
      <a href="{% url 'home' %}" aria-label="Trang chủ">
        <span class="material-symbols-outlined" aria-hidden="true" style="font-size:16px">home</span>
      </a>
    </li>
    {% for crumb in crumbs %}
    <li class="breadcrumb-item {% if forloop.last %}breadcrumb-current{% endif %}">
      <span class="breadcrumb-sep" aria-hidden="true">/</span>
      {% if crumb.url and not forloop.last %}
        <a href="{{ crumb.url }}">{{ crumb.label }}</a>
      {% else %}
        <span aria-current="page">{{ crumb.label }}</span>
      {% endif %}
    </li>
    {% endfor %}
  </ol>
</nav>
{% endif %}
```

**CSS cho breadcrumb** (thêm vào `base.css`):

```css
/* ============================================================
   BREADCRUMB
   ============================================================ */
.breadcrumb-nav {
  padding: 0.5rem 0;
  margin-bottom: 0.5rem;
}
.breadcrumb {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  list-style: none;
  margin: 0;
  padding: 0;
}
.breadcrumb-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--neutral-500);
}
.breadcrumb-item a {
  color: var(--neutral-500);
  text-decoration: none;
  transition: color 0.14s;
}
.breadcrumb-item a:hover { color: var(--primary-500); text-decoration: none; }
.breadcrumb-current span { color: var(--neutral-700); font-weight: 500; }
.breadcrumb-sep { color: var(--neutral-300); font-size: 12px; }
```

---

### 5.2 Tạo `includes/page_header.html`

```html
{#
  includes/page_header.html
  Usage:
    {% include "includes/page_header.html" with
        title="Danh sách lớp học"
        subtitle="Tham gia hoặc tạo lớp học mới"
        breadcrumbs=breadcrumbs
        action_url=create_url
        action_label="Tạo lớp"
        action_icon="add"
    %}

  Lưu ý: Django include không phù hợp để override block action bên trong file include.
  Nếu cần action phức tạp, đặt action HTML bên dưới page-header trong template con,
  hoặc mở rộng include bằng các biến action_url/action_label/action_icon.
#}
<div class="page-header">
  <div class="container">
    {% if breadcrumbs %}
      {% include "includes/breadcrumb.html" with crumbs=breadcrumbs %}
    {% endif %}
    <div class="page-header-inner">
      <div class="page-header-text">
        {% if eyebrow %}
          <p class="eyebrow">{{ eyebrow }}</p>
        {% endif %}
        <h1 class="page-title">{{ title }}</h1>
        {% if subtitle %}
          <p class="page-subtitle">{{ subtitle }}</p>
        {% endif %}
      </div>
      {% if action_url and action_label %}
        <a href="{{ action_url }}" class="btn btn-primary">
          {% if action_icon %}
            <span class="material-symbols-outlined" aria-hidden="true">{{ action_icon }}</span>
          {% endif %}
          {{ action_label }}
        </a>
      {% endif %}
    </div>
  </div>
</div>
```

**CSS cho page-header** (thêm vào `base.css`):

```css
/* ============================================================
   PAGE HEADER (dùng chung cho mọi trang nội dung)
   ============================================================ */
.page-header {
  background: var(--white);
  border-bottom: 1px solid var(--primary-100);
  padding: 1.5rem 0;
}

.page-header-inner {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.page-header-text { flex: 1; min-width: 0; }

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--primary-950);
  line-height: 1.2;
  margin: 0;
}

.page-subtitle {
  font-size: 14px;
  color: var(--neutral-500);
  margin: 4px 0 0;
}

/* Trang section xen kẽ (dashboard, danh sách dài) */
.page-header.alt {
  background: var(--primary-50);
  border-bottom-color: var(--primary-200);
}

/* Container content chính dưới page header */
.page-body {
  padding: 2rem 0;
}

/* ============================================================
   HERO SECTION (trang chủ và landing pages)
   ============================================================ */
.hero {
  background: linear-gradient(135deg, var(--primary-950) 0%, var(--primary-700) 60%, var(--primary-600) 100%);
  padding: 6rem 2rem;
  color: var(--white);
  position: relative;
  overflow: hidden;
}
.hero::before {
  content: '{ }';
  position: absolute;
  right: 8%; top: 50%;
  transform: translateY(-50%);
  font-family: var(--font-mono);
  font-size: 140px;
  font-weight: 800;
  color: rgba(255,255,255,0.04);
  pointer-events: none;
  user-select: none;
}
.hero h1   { color: var(--white); font-size: 48px; }
.hero p    { color: var(--primary-200); font-size: 16px; max-width: 580px; }
.hero-actions { display: flex; gap: 12px; margin-top: 2rem; flex-wrap: wrap; }

.hero-light {
  background: var(--primary-50);
  border-bottom: 1px solid var(--primary-200);
  padding: 3rem 2rem;
}
.hero-light h1 { color: var(--primary-950); }
.hero-light p  { color: var(--neutral-700); }
```

---

### 5.3 Hướng dẫn dùng page-header trong template con

**TRƯỚC (mỗi trang tự làm kiểu khác nhau):**
```html
{# classrooms/list.html — kiểu 1 #}
<div style="background:#f0f8ff; padding:24px 0; border-bottom:1px solid #b8d9fd">
  <div class="container" style="display:flex; justify-content:space-between">
    <h1 style="color:#020d1f">Danh sách lớp học</h1>
    <a href="..." class="btn btn-primary">Tạo lớp</a>
  </div>
</div>
```

**SAU (nhất quán, sạch):**
```html
{# classrooms/list.html #}
{% extends 'base.html' %}
{% block content %}

{% include "includes/page_header.html" with
    title="Danh sách lớp học"
    subtitle="Tham gia hoặc tạo lớp học mới"
    breadcrumbs=breadcrumbs
    action_url=create_url
    action_label="Tạo lớp"
    action_icon="add"
%}
{# breadcrumbs được set trong view:
   context['breadcrumbs'] = [{'label': 'Lớp học'}]
   create_url có thể set trong view hoặc dùng {% url ... as create_url %} trước include.
#}

<div class="page-body">
  <div class="container">
    {# ... nội dung trang ... #}
  </div>
</div>

{% endblock %}
```

> **Lưu ý cho developer:** Thêm `breadcrumbs` vào context dict trong mỗi Django view để breadcrumb tự động render.

---

### ✅ Checklist Phase 5

```
[x] 5.1 — Tạo templates/includes/breadcrumb.html
[x] 5.1 — Thêm CSS breadcrumb vào base.css
[x] 5.2 — Tạo templates/includes/page_header.html
[x] 5.2 — Thêm CSS page-header, page-body, hero vào base.css
[x] 5.3 — Cập nhật ít nhất 5 trang tiêu biểu dùng page_header include:
         [x] classrooms/list.html
         [x] classrooms/detail.html
         [x] assignments/list.html
         [x] accounts/student_dashboard.html
         [x] accounts/teacher_dashboard.html
[x] REVIEW: 5 trang trên có page-header thống nhất về chiều cao, font, màu không?
[x] REVIEW: Breadcrumb hiển thị đúng, link hoạt động không?
```

---

---

# Phase 6 — Admin Layout

> **Mục tiêu:** Sidebar admin thành include riêng, `base_admin.html` gọn, mọi trang admin nhất quán.  
> **Files:** Tạo `templates/includes/admin_sidebar.html`, cập nhật `templates/administration/base_admin.html`

---

### 6.1 Tách Admin Sidebar ra `includes/admin_sidebar.html`

```html
{#
  includes/admin_sidebar.html
  Dùng trong: administration/base_admin.html
  current_page: dùng lại biến hiện có trong admin views.
  Ví dụ: 'dashboard', 'analytics', 'user_management', 'student_management',
         'teacher_management', 'classroom_management', 'subject_approvals',
         'languages', 'sandboxes', 'sandbox_monitor', 'metrics',
         'exam_events', 'logs', 'settings'
#}
<aside
  class="admin-sidebar"
  aria-label="Điều hướng quản trị"
>
  <nav>
    {# Dashboard #}
    <div class="admin-sidebar-section">
      <p class="admin-sidebar-label">Tổng quan</p>
      <a href="{% url 'administation:dashboard' %}"
         class="admin-sidebar-link {% if current_page == 'dashboard' %}active{% endif %}">
        <span class="material-symbols-outlined" aria-hidden="true">dashboard</span>
        Dashboard
      </a>
      <a href="{% url 'administation:analytics' %}"
         class="admin-sidebar-link {% if current_page == 'analytics' %}active{% endif %}">
        <span class="material-symbols-outlined" aria-hidden="true">bar_chart</span>
        Analytics
      </a>
    </div>

    {# Người dùng #}
    <div class="admin-sidebar-section">
      <p class="admin-sidebar-label">Người dùng</p>
      <a href="{% url 'administation:user_management' %}"
         class="admin-sidebar-link {% if current_page == 'user_management' %}active{% endif %}">
        <span class="material-symbols-outlined" aria-hidden="true">group</span>
        Người dùng
      </a>
      <a href="{% url 'administation:teacher_management' %}"
         class="admin-sidebar-link {% if current_page == 'teacher_management' %}active{% endif %}">
        <span class="material-symbols-outlined" aria-hidden="true">how_to_reg</span>
        Giáo viên
      </a>
    </div>

    {# Lớp học & Nội dung #}
    <div class="admin-sidebar-section">
      <p class="admin-sidebar-label">Lớp học & Nội dung</p>
      <a href="{% url 'administation:classroom_management' %}"
         class="admin-sidebar-link {% if current_page == 'classroom_management' %}active{% endif %}">
        <span class="material-symbols-outlined" aria-hidden="true">class</span>
        Lớp học
      </a>
      <a href="{% url 'administation:subject_approvals' %}"
         class="admin-sidebar-link {% if current_page == 'subject_management' or current_page == 'subject_approvals' %}active{% endif %}">
        <span class="material-symbols-outlined" aria-hidden="true">menu_book</span>
        Môn học
      </a>
    </div>

    {# Hệ thống #}
    <div class="admin-sidebar-section">
      <p class="admin-sidebar-label">Hệ thống</p>
      <a href="{% url 'administation:languages' %}"
         class="admin-sidebar-link {% if current_page == 'languages' %}active{% endif %}">
        <span class="material-symbols-outlined" aria-hidden="true">code</span>
        Ngôn ngữ
      </a>
      <a href="{% url 'administation:sandboxes' %}"
         class="admin-sidebar-link {% if current_page == 'sandboxes' %}active{% endif %}">
        <span class="material-symbols-outlined" aria-hidden="true">dns</span>
        Sandboxes
      </a>
      <a href="{% url 'administation:sandbox_monitor' %}"
         class="admin-sidebar-link {% if current_page == 'sandbox_monitor' %}active{% endif %}">
        <span class="material-symbols-outlined" aria-hidden="true">monitor_heart</span>
        Sandbox Monitor
      </a>
      <a href="{% url 'administation:metrics' %}"
         class="admin-sidebar-link {% if current_page == 'metrics' %}active{% endif %}">
        <span class="material-symbols-outlined" aria-hidden="true">speed</span>
        Server Metrics
      </a>
    </div>

    {# Giám sát & Cài đặt #}
    <div class="admin-sidebar-section">
      <p class="admin-sidebar-label">Giám sát & Cài đặt</p>
      <a href="{% url 'administation:activity_logs' %}"
         class="admin-sidebar-link {% if current_page == 'logs' %}active{% endif %}">
        <span class="material-symbols-outlined" aria-hidden="true">history</span>
        Activity Logs
      </a>
      <a href="{% url 'administation:exam_events' %}"
         class="admin-sidebar-link {% if current_page == 'exam_events' %}active{% endif %}">
        <span class="material-symbols-outlined" aria-hidden="true">videocam</span>
        Exam Events
      </a>
      <a href="{% url 'administation:system_settings' %}"
         class="admin-sidebar-link {% if current_page == 'settings' %}active{% endif %}">
        <span class="material-symbols-outlined" aria-hidden="true">settings</span>
        Cài đặt hệ thống
      </a>
    </div>
  </nav>
</aside>
```

---

### 6.2 CSS Admin Layout (thêm vào `base.css`)

```css
/* ============================================================
   ADMIN LAYOUT
   ============================================================ */
.admin-layout {
  display: grid;
  grid-template-columns: var(--sidebar-w) 1fr;
  min-height: calc(100vh - var(--header-h));
  align-items: start;
}
@media (max-width: 900px) {
  .admin-layout { grid-template-columns: 1fr; }
}

/* Sidebar */
.admin-sidebar {
  position: sticky;
  top: var(--header-h);
  height: calc(100vh - var(--header-h));
  overflow-y: auto;
  background: var(--primary-950);
  padding: 1.25rem 0;
  border-right: 1px solid rgba(255,255,255,0.06);
}
@media (max-width: 900px) {
  .admin-sidebar { display: none; }  /* Ẩn trên mobile — dùng hamburger */
}

.admin-sidebar-section {
  margin-bottom: 0.25rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.admin-sidebar-section:last-child { border-bottom: none; }

.admin-sidebar-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--primary-400);
  padding: 0 1rem;
  margin: 0 0 6px;
}

.admin-sidebar-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 1rem;
  font-size: 13px;
  font-weight: 500;
  color: var(--primary-300);
  text-decoration: none;
  border-left: 3px solid transparent;
  transition: background 0.14s, color 0.14s, border-color 0.14s;
}
.admin-sidebar-link:hover {
  background: rgba(19,127,236,0.12);
  color: var(--white);
  text-decoration: none;
}
.admin-sidebar-link.active {
  background: rgba(19,127,236,0.18);
  color: var(--white);
  border-left-color: var(--primary-400);
  font-weight: 600;
}
.admin-sidebar-link .material-symbols-outlined {
  font-size: 18px;
  opacity: 0.8;
  flex-shrink: 0;
}
.admin-sidebar-link.active .material-symbols-outlined { opacity: 1; }

/* Admin content area */
.admin-content {
  padding: 2rem;
  min-height: calc(100vh - var(--header-h));
  background: var(--neutral-100);
}
@media (max-width: 900px) {
  .admin-content { padding: 1rem; }
}

/* Admin page header */
.admin-page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}
.admin-page-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--primary-950);
  margin: 0;
}
```

---

### 6.3 Cập nhật `administration/base_admin.html`

```html
{# administration/base_admin.html #}
{% extends 'base.html' %}

{% block content %}
<div class="admin-layout">
  {# Sidebar #}
  {% include "includes/admin_sidebar.html" with current_page=current_page %}

  {# Main content #}
  <main class="admin-content" id="admin-main">
    {% block admin_content %}{% endblock %}
  </main>
</div>
{% endblock %}
```

**Dùng trong trang admin:**
```html
{# administration/user_management.html #}
{% extends 'administration/base_admin.html' %}
{% block admin_content %}

<div class="admin-page-header">
  <h1 class="admin-page-title">Quản lý người dùng</h1>
  <div class="flex gap-2">
    <a href="..." class="btn btn-primary btn-sm">Tạo tài khoản</a>
    {% include "includes/csv_dropdown.html" %}
  </div>
</div>

{# ... nội dung ... #}

{% endblock %}
```

> Repo hiện tại đã dùng `current_page` trong nhiều admin view. Chỉ thêm/sửa context nếu trang admin nào chưa truyền `current_page`.

---

### ✅ Checklist Phase 6

```
[x] 6.1 — Tạo templates/includes/admin_sidebar.html với đủ các link
[x] 6.2 — Thêm CSS admin-layout, admin-sidebar, admin-content vào base.css
[x] 6.3 — Cập nhật administration/base_admin.html
[x] 6.3 — Kiểm tra mọi admin view có `current_page` phù hợp
[x] REVIEW: Mở admin dashboard — sidebar hiện đúng màu tối không?
[x] REVIEW: Link active trong sidebar highlight đúng trang hiện tại không?
[x] REVIEW: Mở viewport < 900px — sidebar ẩn, content full width không?
[x] REVIEW: Sidebar scroll độc lập khi content dài không?
```

---

---

# Phase 7 — IDE Page (`solve_problem.html`)

> **Mục tiêu:** IDE giữ full-screen nhưng dùng đúng CSS variables từ design system, không bị drift.  
> **Files:** `templates/submissions/solve_problem.html`

---

### 7.1 Vấn đề hiện tại

`solve_problem.html` là trang độc lập (không kế thừa `base.html`), nhưng tự định nghĩa lại CSS variables riêng → dễ bị lệch với design system khi `base.css` được cập nhật.

---

### 7.2 Fix: Import `base.css` trong IDE page

Không thay toàn bộ `<head>` một cách máy móc vì `solve_problem.html` đang có Tailwind CDN, CodeMirror/IDE script và dữ liệu bài làm riêng. Chỉ bổ sung `{% load static %}` nếu chưa có, import `base.css`, rồi tách phần CSS riêng sang `ide.css`.

```html
{% load static %}
<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}IDE — DevLearn{% endblock %}</title>

  {# Fonts (giống base.html) #}
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">

  {# Material Symbols #}
  <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined" rel="stylesheet">

  {# Design system — CSS variables từ nguồn duy nhất.
     Đặt trước ide.css để ide.css override layout riêng khi cần. #}
  <link rel="stylesheet" href="{% static 'css/base.css' %}">

  {# ❌ KHÔNG khai báo lại :root ở đây — đã có trong base.css #}

  {# IDE-specific styles #}
  <link rel="stylesheet" href="{% static 'css/ide.css' %}">  {# Tách riêng style IDE #}
</head>
```

> Nếu import toàn bộ `base.css` làm ảnh hưởng layout IDE, giữ `base.css` chỉ để lấy token/global primitive, sau đó override rõ ràng trong `ide.css`. Không xóa các script CodeMirror/chạy code/nộp bài hiện có.

---

### 7.3 Tách IDE-specific CSS ra `static/css/ide.css`

Tạo `static/css/ide.css` chứa style chỉ dùng trong IDE, KHÔNG ở nơi nào khác:

```css
/* ============================================================
   IDE PAGE — Styles riêng cho solve_problem.html
   Dùng CSS variables từ base.css — KHÔNG hardcode hex
   ============================================================ */

/* Layout IDE full-screen */
.ide-root {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--code-bg);
  color: var(--code-var);
  font-family: var(--font-sans);
  overflow: hidden;
}

/* IDE Header bar */
.ide-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 50px;
  padding: 0 1rem;
  background: var(--primary-900);
  border-bottom: 1px solid rgba(255,255,255,0.08);
  flex-shrink: 0;
  gap: 1rem;
}

.ide-header-logo {
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--primary-300);
  text-decoration: none;
  flex-shrink: 0;
}

.ide-problem-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--white);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  text-align: center;
}

/* Workspace — chia đôi ngang */
.ide-workspace {
  display: grid;
  grid-template-columns: 1fr 1fr;
  flex: 1;
  overflow: hidden;
}

/* Instructions panel (trái) */
.ide-instructions {
  background: var(--primary-950);
  border-right: 1px solid rgba(255,255,255,0.08);
  overflow-y: auto;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.ide-instructions h1,
.ide-instructions h2,
.ide-instructions h3 {
  color: var(--white);
}

.ide-instructions p { color: var(--primary-200); font-size: 14px; }

/* Editor panel (phải) */
.ide-editor-panel {
  display: flex;
  flex-direction: column;
  background: var(--code-bg);
  overflow: hidden;
}

/* Toolbar trên editor */
.ide-editor-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--primary-900);
  border-bottom: 1px solid rgba(255,255,255,0.08);
  flex-shrink: 0;
}

/* CodeMirror editor area */
.ide-codemirror {
  flex: 1;
  overflow: hidden;
}

/* Output panel (bottom) */
.ide-output {
  background: var(--primary-900);
  border-top: 1px solid rgba(255,255,255,0.10);
  overflow-y: auto;
  flex-shrink: 0;
  min-height: 180px;
  max-height: 35vh;
  padding: 0.75rem 1rem;
}

.ide-output-tab {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 600;
  padding: 5px 12px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--primary-300);
  transition: background 0.14s, color 0.14s;
}
.ide-output-tab.active {
  background: var(--primary-800);
  color: var(--white);
}

/* Testcase result items */
.testcase-item {
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  margin-bottom: 6px;
  font-family: var(--font-mono);
  font-size: 13px;
}
.testcase-item.pass { background: rgba(22,163,74,0.15); border-left: 3px solid var(--success-600); }
.testcase-item.fail { background: rgba(220,38,38,0.15); border-left: 3px solid var(--danger-600); }
.testcase-item.pending { background: rgba(19,127,236,0.10); border-left: 3px solid var(--primary-400); }

/* Responsive: <= 900px — stack dọc */
@media (max-width: 900px) {
  .ide-workspace { grid-template-columns: 1fr; grid-template-rows: 36vh 1fr; }
  .ide-instructions { height: 36vh; border-right: none; border-bottom: 1px solid rgba(255,255,255,0.08); }
  .ide-editor-panel { min-height: 62vh; }
  .ide-output { max-height: 220px; }
}
```

---

### ✅ Checklist Phase 7

```
[x] 7.2 — IDE page import base.css thay vì khai báo lại :root
[x] 7.3 — Tạo static/css/ide.css với style riêng cho IDE
[x] 7.3 — IDE page link tới ide.css
[x] REVIEW: Mở IDE page — màu sắc đúng với design system không?
[ ] REVIEW: Không còn hardcode hex theme chính trong solve_problem.html không? Màu syntax/theme đặc thù của editor có thể chuyển dần sang ide.css.
[x] REVIEW: Responsive: thu nhỏ < 900px — workspace stack dọc không?
[x] REVIEW: Output panel resize đúng chiều cao không?
```

---

---

# Phase 8 — Accessibility & Final Polish

> **Mục tiêu:** Đạt WCAG 2.1 AA cơ bản. Hoàn thiện chi tiết cuối.  
> **Files:** Toàn bộ templates, `base.css`, `main.js`

---

### 8.1 Focus Ring toàn cục

Thêm vào đầu `base.css`:

```css
/* ============================================================
   FOCUS MANAGEMENT — Accessibility
   ============================================================ */

/* Ẩn focus ring khi dùng chuột, hiện khi dùng bàn phím */
:focus:not(:focus-visible) { outline: none; }
:focus-visible {
  outline: 3px solid var(--primary-400);
  outline-offset: 3px;
  border-radius: var(--radius-sm);
}

/* Focus ring tối hơn cho nền sáng */
.bg-dark :focus-visible,
.admin-sidebar :focus-visible,
.ide-root :focus-visible {
  outline-color: var(--primary-300);
}
```

---

### 8.2 ARIA Labels cho các thành phần động

Kiểm tra và đảm bảo tất cả các thành phần sau có ARIA đúng:

| Thành phần | Attribute cần có |
|---|---|
| Notification badge | `aria-label="X thông báo chưa đọc"` |
| Avatar dropdown | `aria-haspopup="true"` `aria-expanded="false/true"` |
| Notification dropdown | `aria-haspopup="true"` `aria-expanded` |
| Form submit button | Rõ nghĩa, không chỉ là icon |
| Loading overlay | `aria-hidden="true"` khi ẩn, `aria-live="polite"` |
| Toast container | `aria-live="polite"` `role="region"` |
| Data table | `<caption>` hoặc `aria-label` |
| Pagination | `aria-label="Phân trang"` `aria-current="page"` |
| Hamburger | `aria-expanded` `aria-controls` |
| Modal (nếu có) | `role="dialog"` `aria-modal="true"` `aria-labelledby` |

---

### 8.3 Table Accessibility (Admin tables)

```html
{# Mọi bảng dữ liệu admin phải có caption hoặc aria-label #}
<div class="table-wrapper" role="region" aria-label="Danh sách người dùng" tabindex="0">
  <table class="data-table">
    <caption class="sr-only">Danh sách người dùng — {{ total }} kết quả</caption>
    <thead>
      <tr>
        <th scope="col">
          <input type="checkbox" aria-label="Chọn tất cả">
        </th>
        <th scope="col">Tên</th>
        <th scope="col">Email</th>
        <th scope="col">Vai trò</th>
        <th scope="col">Trạng thái</th>
        <th scope="col"><span class="sr-only">Hành động</span></th>
      </tr>
    </thead>
    {# ... #}
  </table>
</div>
```

**CSS bổ sung:**

```css
/* ============================================================
   DATA TABLES
   ============================================================ */
.table-wrapper {
  overflow-x: auto;
  border-radius: var(--radius-lg);
  border: 1px solid var(--primary-100);
  box-shadow: var(--shadow-card);
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  background: var(--white);
}

.data-table th {
  background: var(--primary-50);
  color: var(--neutral-700);
  font-weight: 600;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 10px 14px;
  text-align: left;
  border-bottom: 1px solid var(--primary-100);
  white-space: nowrap;
}

.data-table td {
  padding: 10px 14px;
  border-bottom: 1px solid var(--neutral-100);
  color: var(--neutral-700);
  vertical-align: middle;
}

.data-table tr:last-child td { border-bottom: none; }
.data-table tbody tr:hover { background: var(--primary-50); }

/* Checkbox column */
.data-table td:first-child,
.data-table th:first-child {
  width: 40px;
  padding-left: 1rem;
  padding-right: 0.5rem;
}
```

---

### 8.4 Color Contrast Check

Kiểm tra các cặp màu quan trọng đạt tương phản tối thiểu **4.5:1** (WCAG AA):

| Foreground | Background | Ratio | ✓/✗ |
|---|---|---|---|
| `#137fec` (primary-500) | `#ffffff` | 3.5:1 | ⚠️ Chỉ dùng cho large text/icon |
| `#1260c0` (primary-600) | `#ffffff` | 5.3:1 | ✅ |
| `#0f172a` (neutral-900) | `#ffffff` | 17:1 | ✅ |
| `#334155` (neutral-700) | `#ffffff` | 8.5:1 | ✅ |
| `#ffffff` | `#137fec` | 3.5:1 | ⚠️ Button text — OK (large) |
| `#ffffff` | `#0f4289` (primary-700) | 7.5:1 | ✅ |

> **Action cần làm:** Với text trắng trên nền `--primary-500`, contrast chỉ khoảng 3.5:1 nên chưa đạt AA cho text thường.  
> **Fix ưu tiên:** đổi `.btn-primary` sang nền `--primary-600` (#1260c0) và hover dùng `--primary-700`. Không dựa vào `font-weight: 600` để hợp thức hóa contrast.

---

### 8.5 Smooth Scroll & Animation Preferences

```css
/* ============================================================
   MOTION PREFERENCES
   ============================================================ */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}

html { scroll-behavior: smooth; }
```

---

### 8.6 Toast Auto-hide JS (cập nhật `main.js`)

```js
// ============================================================
// Toast Auto-hide
// ============================================================
function initToasts() {
  const toasts = document.querySelectorAll('[data-autohide], .site-toast');
  toasts.forEach(toast => {
    const delay = parseInt(toast.dataset.autohide || '5000', 10);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(20px)';
      setTimeout(() => toast.remove(), 300);
    }, delay);
  });
}

document.addEventListener('DOMContentLoaded', initToasts);
```

> Sau khi chuyển sang `initToasts()` trong `main.js`, xóa script auto-hide inline trong `base.html` để tránh chạy trùng.

---

### 8.7 Print Styles (cho trang báo cáo, không kế thừa layout)

`late_report_print.html` là trang in độc lập. Đảm bảo nó có:

```html
<head>
  {# Chỉ import CSS variables — không import toàn bộ base.css #}
  <style>
    /* Inline chỉ các variables cần thiết để print.
       Đây là ngoại lệ vì late_report_print.html là trang standalone. */
    :root {
      --primary-950: #020d1f;
      --primary-500: #137fec;
      --neutral-900: #0f172a;
      --neutral-700: #334155;
      --font-sans: 'Be Vietnam Pro', sans-serif;
    }
    body { font-family: var(--font-sans); color: var(--neutral-900); }
    @media print { .no-print { display: none !important; } }
  </style>
</head>
```

> `late_report_print.html` được phép inline variables vì nó KHÔNG kế thừa base.html — đây là ngoại lệ hợp lệ duy nhất.

---

### ✅ Checklist Phase 8

```
[x] 8.1 — Thêm :focus/:focus-visible global vào đầu base.css
[x] 8.2 — Audit ARIA labels: notification badge, dropdowns, hamburger, toast
[x] 8.3 — Thêm aria-label/caption cho mọi data-table trong admin
[x] 8.3 — Thêm CSS .table-wrapper/.data-table vào base.css
[x] 8.4 — Kiểm tra contrast — đổi button primary sang dùng font-weight 600
[x] 8.5 — Thêm prefers-reduced-motion vào base.css
[x] 8.6 — Cập nhật toast auto-hide trong main.js
[x] 8.7 — Fix late_report_print.html dùng variables inline (ngoại lệ hợp lệ)
[ ] REVIEW CUỐI: Dùng axe DevTools hoặc Lighthouse — Accessibility score >= 85
[x] REVIEW CUỐI: Tab qua toàn bộ trang — focus ring luôn rõ ràng
[ ] REVIEW CUỐI: Mở trên mobile thật — hamburger, drawer, form hoạt động OK
[ ] REVIEW CUỐI: Lighthouse Performance — không bị giảm sau refactor
```

---

---

## Tổng kết — Checklist Master

```
[x] Phase 1 — CSS Foundation (CSS variables, Tailwind sync, fonts, remove hardcode)
[x] Phase 2 — Base Layout (toast.html, loading.html, skip link, body structure)
[x] Phase 3 — Navbar & Footer (hamburger, mobile drawer, footer grid)
[x] Phase 4 — Shared Components (buttons, cards, badges, forms, toasts, progress)
[x] Phase 5 — Page Structure (breadcrumb.html, page_header.html, hero CSS)
[x] Phase 6 — Admin Layout (admin_sidebar.html, admin CSS, base_admin refactor)
[x] Phase 7 — IDE Page (import base.css, tách ide.css)
[x] Phase 8 — Accessibility (focus ring, ARIA, tables, contrast, print)
```

---

## Quy tắc bất biến cho Agent

1. **Không hardcode hex cho màu theme/chung** — ưu tiên `var(--token-name)`. Nếu là màu syntax editor, trạng thái rất riêng hoặc print standalone, được giữ tạm và ghi chú lý do.
2. **Không khai báo `:root` ở bất cứ đâu ngoài `base.css`** — ngoại lệ duy nhất là `late_report_print.html`.
3. **Mọi thành phần tương tác đều có `aria-label`** nếu text không đủ mô tả.
4. **Kiểm tra sau mỗi phase** trước khi chuyển sang phase tiếp theo.
5. **Ưu tiên chỉ sửa template/static.** Được sửa view ở mức context nhỏ cho `breadcrumbs`, `current_page`, `create_url` nếu template include cần dữ liệu; không sửa model/business logic trong đợt frontend refactor.
6. **Namespace URL `administation`** (sai chính tả nhưng giữ nguyên) — không đổi.
7. **`solve_problem.html` và `late_report_print.html`** là standalone — không ép kế thừa `base.html`.

---

*fix_frontend.md · DevLearn v1.0 · Generated for Codex/AI Agent execution*  
*Màu brand: #137FEC · Font: Be Vietnam Pro · Phân tích dựa trên cau_truc_frontend.md + devlearn-design-system.md*
