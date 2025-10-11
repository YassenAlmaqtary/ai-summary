<template>
  <div class="app-shell" dir="rtl" :data-theme="theme">
    <nav class="top-nav">
      <div class="brand">
        <div class="brand-mark">🎓</div>
        <div class="brand-copy">
          <h1>رفيق الملخصات</h1>
          <p>ذكاء اصطناعي يساعدك على فهم الدروس بسرعة</p>
        </div>
      </div>
      <div class="nav-actions">
        <div class="model-picker">
          <label for="model-select">نموذج الذكاء</label>
          <select id="model-select" v-model="model" :disabled="loading || models.length === 0">
            <option v-if="models.length === 0" disabled>جاري التحميل...</option>
            <option v-for="m in models" :key="m" :value="m">{{ m }}</option>
          </select>
        </div>
        <button class="theme-toggle" @click="toggleTheme" :title="isDark ? 'وضع فاتح' : 'وضع داكن'">
          {{ isDark ? '☀️' : '🌙' }}
        </button>
      </div>
    </nav>

    <main class="workspace">
      <aside class="sidebar">
        <section class="card hero-card">
          <h2>مرحباً بالطلاب</h2>
          <p>ارفع مذكراتك أو ملفات PDF وسنعود إليك بملخص منظم يسهل مراجعته قبل الاختبارات.</p>
          <ul class="hero-list">
            <li>ملخصات مركزة مع نقاط رئيسية</li>
            <li>اقتراحات للمراجعة والتذكر</li>
            <li>واجهة على غرار المحادثة لتتبع أفكارك</li>
          </ul>
        </section>

        <section class="card upload-card">
          <header class="card-head">
            <div>
              <h3>ارفع ملفك</h3>
              <span class="caption">يُدعم PDF حتى 15MB</span>
            </div>
            <span v-if="fileName" class="badge">تم اختيار ملف</span>
          </header>

          <FileUpload @file-selected="setFile" />

          <div class="upload-meta">
            <p v-if="fileName"><strong>الملف:</strong> {{ fileName }}</p>
            <p v-if="loading"><strong>الوقت:</strong> {{ formatElapsed(elapsed) }}</p>
            <p v-if="summary && !loading"><strong>آخر تحديث:</strong> تم إنشاء ملخص جديد</p>
          </div>

          <div class="upload-actions">
            <button class="primary" :disabled="!file || loading" @click="summarize">
              <span v-if="!loading">ابدأ التلخيص</span>
              <span v-else>جاري التلخيص...</span>
            </button>
            <button v-if="loading" class="ghost danger" @click="cancel">إيقاف</button>
            <button v-if="summary && !loading" class="ghost" @click="reset">بدء جلسة جديدة</button>
          </div>

          <div class="status-row" v-if="loading">
            <span class="pulse"></span>
            <span>نقوم بتحليل الملف وإعداد ملخص مناسب لك...</span>
          </div>

          <p v-if="error" class="error-box">{{ error }}</p>
        </section>

        <section class="card tips-card">
          <h3>نصائح للاستفادة</h3>
          <ul>
            <li>قسّم المواد الطويلة إلى أقسام، وارفع ملفاً لكل فصل.</li>
            <li>جرّب أكثر من نموذج لترى أيها يفهم أسلوبك بشكل أفضل.</li>
            <li>انسخ الملخص وأضف ملاحظاتك عليه داخل دفتر الدراسة.</li>
          </ul>
        </section>
      </aside>

      <section class="conversation">
        <header class="conversation-head">
          <div class="head-copy">
            <span class="subtitle">مساحة الملخص</span>
            <h2>محادثة المُلخِّص الذكي</h2>
          </div>
          <div class="head-actions">
            <button class="icon-btn" :disabled="!summary" @click="copySummary" title="نسخ">
              📋
            </button>
            <button class="icon-btn" :disabled="!summary" @click="downloadSummary" title="تنزيل">
              ⬇️
            </button>
          </div>
        </header>

        <div class="chat-area">
          <article v-if="summary" class="assistant-message">
            <div class="message-meta">
              <span class="role-chip">المُلخِّص</span>
              <span class="model-chip">{{ model || 'نموذج' }}</span>
            </div>
            <div class="message-bubble">
              <MarkdownRenderer :source="summary" />
            </div>
          </article>

          <div v-else class="empty-state">
            <div class="empty-icon">💡</div>
            <h3>ابدأ أول تلخيص لك</h3>
            <p>ارفع ملف درس أو محاضرة، واختر النموذج، ثم اضغط على زر التلخيص. سنُظهر النتيجة هنا على هيئة رسالة دردشة سهلة القراءة.</p>
            <div class="steps">
              <span>1. اختر ملف PDF تعليمي.</span>
              <span>2. اضغط على "ابدأ التلخيص".</span>
              <span>3. تابع النقاط المهمة، ودوّن ملاحظاتك.</span>
            </div>
          </div>
        </div>
      </section>
    </main>

    <footer class="site-footer">© {{ year }} مشروع تعليمي لأي طالب • تم التطوير بحب</footer>
    <Toast :show="showToast" :message="toastMessage" :type="toastType" @close="showToast=false" />
  </div>
</template>

<script>
import { API_BASE_URL } from './config.js'
import FileUpload from './components/FileUpload.vue'
import MarkdownRenderer from './components/MarkdownRenderer.vue'
import Toast from './components/Toast.vue'

export default {
  components: { FileUpload, MarkdownRenderer, Toast },
  data() {
    return {
      file: null,
      summary: '',
      loading: false,
      error: '',
      year: new Date().getFullYear(),
      elapsed: 0,
      _timer: null,
      _es: null,
      showToast: false,
      toastType: 'info',
      toastMessage: '',
      _toastTimer: null,
      model: '',
      models: [],
      theme: 'light',
      apiBaseUrl: API_BASE_URL
    }
  },
  computed: {
    isDark() {
      return this.theme === 'dark'
    },
    fileName() {
      return this.file ? this.file.name : ''
    }
  },
  mounted() {
    this.theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    document.documentElement.dataset.theme = this.theme
    this.loadModels()
  },
  beforeUnmount() {
    this._clearTimer()
    this._closeES()
  },
  methods: {
    async loadModels() {
      try {
        const res = await fetch(`${this.apiBaseUrl}/models`)
        if (!res.ok) return
        const data = await res.json()
        this.models = data.models || []
        this.model = data.default || this.models[0] || ''
      } catch (e) {
        // ignore
      }
    },
    setFile(file) {
      this.file = file
    },
    toggleTheme() {
      const nextTheme = this.isDark ? 'light' : 'dark'
      this.theme = nextTheme
      document.documentElement.dataset.theme = this.theme
      this.notify(nextTheme === 'dark' ? 'تم تفعيل الوضع الداكن' : 'تم تفعيل الوضع الفاتح', 'success')
    },
    formatElapsed(seconds) {
      const minutes = Math.floor(seconds / 60).toString().padStart(2, '0')
      const remainder = (seconds % 60).toString().padStart(2, '0')
      return `${minutes}:${remainder}`
    },
    async summarize() {
      if (!this.file) {
        this.notify('⚠️ اختر ملف PDF أولاً!', 'error')
        return
      }
      this.summary = ''
      this.error = ''
      this.loading = true
      this.elapsed = 0
      if (this._timer) clearInterval(this._timer)
      this._timer = setInterval(() => {
        this.elapsed++
      }, 1000)

      try {
        const formData = new FormData()
        formData.append('file', this.file)
        const res = await fetch(`${this.apiBaseUrl}/upload`, { method: 'POST', body: formData })
        if (!res.ok) throw new Error('فشل رفع الملف')
        const data = await res.json()
        const sessionId = data.session_id

        const url = `${this.apiBaseUrl}/summarize-gemini?session_id=${encodeURIComponent(sessionId)}&model=${encodeURIComponent(this.model)}`
        const es = new EventSource(url)
        this._es = es

        es.onmessage = event => {
          this.summary += event.data
        }

        es.addEventListener('status', event => {
          if (event.data === 'DONE') {
            this.loading = false
            this._closeES()
            this._clearTimer()
            this.notify('اكتمل التلخيص', 'success')
          }
        })

        es.addEventListener('error', () => {
          this.loading = false
          this._closeES()
          this._clearTimer()
          this.notify('تعذر إكمال التلخيص', 'error')
        })
      } catch (error) {
        this.loading = false
        this._clearTimer()
        this.notify(error.message || 'تعذر رفع الملف', 'error')
      } finally {
        if (!this.loading && this._timer) {
          this._clearTimer()
        }
      }
    },
    cancel() {
      this.loading = false
      this._closeES()
      this._clearTimer()
    },
    _closeES() {
      if (this._es) {
        this._es.close()
        this._es = null
      }
    },
    _clearTimer() {
      if (this._timer) {
        clearInterval(this._timer)
        this._timer = null
      }
    },
    copySummary() {
      if (!this.summary) return
      navigator.clipboard.writeText(this.summary)
      this.notify('تم النسخ', 'success')
    },
    downloadSummary() {
      if (!this.summary) return
      const blob = new Blob([this.summary], { type: 'text/plain;charset=utf-8' })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = 'summary.txt'
      link.click()
      URL.revokeObjectURL(link.href)
      this.notify('تم التنزيل', 'success')
    },
    reset() {
      this.summary = ''
      this.error = ''
      this.file = null
      this.notify('تم بدء جلسة جديدة', 'success')
    },
    notify(message, type = 'info') {
      this.toastMessage = message
      this.toastType = type
      this.showToast = true
      if (type === 'error') {
        this.error = message
      } else {
        this.error = ''
      }
      clearTimeout(this._toastTimer)
      this._toastTimer = setTimeout(() => {
        this.showToast = false
      }, 4000)
    }
  }
}
</script>

<style>
:root {
  --bg: #eef3ff;
  --surface: #ffffff;
  --surface-alt: #f3f6ff;
  --border: #d6def5;
  --text: #1f2534;
  --text-soft: #5c6580;
  --accent: #2563eb;
  --accent-rgb: 37 99 235;
  --danger: #dc2626;
  --danger-soft: rgba(220, 38, 38, 0.14);
  --danger-border: rgba(220, 38, 38, 0.35);
  --shadow: 0 28px 50px rgba(15, 23, 42, 0.12);
  --radius-lg: 28px;
  --radius-md: 18px;
  --radius-sm: 12px;
  --transition: 0.2s ease;
}

[data-theme='dark'] {
  --bg: #0f172a;
  --surface: #111827;
  --surface-alt: #1f2937;
  --border: #273245;
  --text: #f1f5f9;
  --text-soft: #9aa2b6;
  --accent: #60a5fa;
  --accent-rgb: 96 165 250;
  --danger: #f87171;
  --danger-soft: rgba(248, 113, 113, 0.18);
  --danger-border: rgba(248, 113, 113, 0.35);
  --shadow: 0 28px 60px rgba(15, 23, 42, 0.45);
}

*,
*::before,
*::after {
  box-sizing: border-box;
}

html,
body,
#app,
.app-shell {
  margin: 0;
  padding: 0;
  min-height: 100%;
  font-family: 'Cairo', 'Tajawal', system-ui, sans-serif;
  color: var(--text);
}

body {
  background: linear-gradient(140deg, var(--bg), rgba(255, 255, 255, 0.6));
  background-attachment: fixed;
}

img,
video {
  max-width: 100%;
  height: auto;
}

.app-shell {
  display: flex;
  flex-direction: column;
}

.top-nav {
  width: min(1180px, 100% - 32px);
  margin: 24px auto 0;
  padding: 18px 26px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 18px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow);
}

.brand {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
}

.brand-mark {
  width: 54px;
  height: 54px;
  border-radius: 18px;
  background: rgba(var(--accent-rgb), 0.1);
  display: grid;
  place-items: center;
  font-size: 28px;
}

.brand-copy h1 {
  margin: 0;
  font-size: clamp(1.1rem, 2vw, 1.5rem);
  font-weight: 800;
}

.brand-copy p {
  margin: 4px 0 0;
  font-size: 0.8rem;
  color: var(--text-soft);
}

.nav-actions {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.model-picker {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.78rem;
  color: var(--text-soft);
}

.model-picker select {
  min-width: 200px;
  background: var(--surface-alt);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 10px;
  font-family: inherit;
  font-size: 0.9rem;
  color: var(--text);
}

.model-picker select:focus {
  outline: none;
  border-color: rgba(var(--accent-rgb), 0.5);
  box-shadow: 0 0 0 4px rgba(var(--accent-rgb), 0.18);
}

.theme-toggle {
  width: 46px;
  height: 46px;
  border-radius: 50%;
  border: 1px solid var(--border);
  background: var(--surface-alt);
  cursor: pointer;
  font-size: 1.1rem;
  transition: var(--transition);
}

.theme-toggle:hover {
  background: rgba(var(--accent-rgb), 0.12);
}

.workspace {
  width: min(1180px, 100% - 32px);
  margin: 32px auto 40px;
  display: grid;
  grid-template-columns: minmax(260px, 320px) minmax(0, 1fr);
  gap: 26px;
  align-items: start;
}

.sidebar {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 24px;
  box-shadow: var(--shadow);
  transition: var(--transition);
}

.card:hover {
  transform: translateY(-2px);
}

.hero-card h2 {
  margin: 0;
  font-size: 1.2rem;
}

.hero-card p {
  margin: 12px 0 18px;
  color: var(--text-soft);
  line-height: 1.6;
}

.hero-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  color: var(--text);
  font-size: 0.9rem;
}

.hero-list li::before {
  content: '•';
  margin-inline-start: 8px;
  color: var(--accent);
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
}

.card-head h3 {
  margin: 0;
  font-size: 1.05rem;
}

.caption {
  display: block;
  margin-top: 6px;
  font-size: 0.75rem;
  color: var(--text-soft);
}

.badge {
  background: rgba(var(--accent-rgb), 0.12);
  color: var(--accent);
  border-radius: 999px;
  padding: 6px 14px;
  font-size: 0.75rem;
}

.upload-meta {
  margin: 18px 0 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 0.85rem;
  color: var(--text-soft);
}

.upload-meta strong {
  color: var(--text);
  font-weight: 700;
}

.upload-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px dashed rgba(var(--accent-rgb), 0.18);
}

button {
  font-family: inherit;
  cursor: pointer;
}

.primary {
  width: 100%;
  background: linear-gradient(140deg, #2563eb, #4338ca);
  color: #ffffff;
  border: none;
  border-radius: var(--radius-sm);
  padding: 12px 20px;
  font-weight: 700;
  letter-spacing: 0.4px;
  box-shadow: 0 14px 28px rgba(37, 99, 235, 0.32);
  transition: var(--transition);
  min-height: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
}

.primary:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  box-shadow: none;
  background: linear-gradient(140deg, rgba(37, 99, 235, 0.45), rgba(67, 56, 202, 0.45));
}

.primary:not(:disabled):hover {
  filter: brightness(1.03);
  transform: translateY(-1px);
}

.ghost {
  background: transparent;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 12px 18px;
  color: var(--text);
  transition: var(--transition);
  width: 100%;
  min-height: 48px;
}

.ghost:hover {
  border-color: rgba(var(--accent-rgb), 0.4);
  color: var(--accent);
}

.ghost.danger {
  color: var(--danger);
  border-color: var(--danger);
}

.ghost.danger:hover {
  background: var(--danger-soft);
}

.status-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 16px;
  font-size: 0.8rem;
  color: var(--text-soft);
}

.pulse {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: rgba(var(--accent-rgb), 0.9);
  animation: beat 1.2s infinite;
}

@keyframes beat {
  0%,
  100% {
    transform: scale(1);
    opacity: 0.9;
  }
  50% {
    transform: scale(0.7);
    opacity: 0.4;
  }
}

.error-box {
  margin-top: 16px;
  background: var(--danger-soft);
  color: var(--danger);
  border: 1px solid var(--danger-border);
  border-radius: var(--radius-sm);
  padding: 10px 14px;
  font-size: 0.82rem;
}

.tips-card ul {
  padding-inline-start: 18px;
  margin: 12px 0 0;
  color: var(--text-soft);
  line-height: 1.7;
  font-size: 0.85rem;
}

.conversation {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
  min-height: 520px;
}

.conversation-head {
  padding: 26px 28px 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.head-copy h2 {
  margin: 6px 0 0;
  font-size: 1.2rem;
}

.subtitle {
  font-size: 0.75rem;
  color: var(--text-soft);
  letter-spacing: 0.6px;
}

.head-actions {
  display: flex;
  gap: 10px;
}

.icon-btn {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  border: 1px solid var(--border);
  background: var(--surface-alt);
  display: grid;
  place-items: center;
  font-size: 1rem;
  cursor: pointer;
  transition: var(--transition);
}

.icon-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.icon-btn:not(:disabled):hover {
  background: rgba(var(--accent-rgb), 0.14);
}

.chat-area {
  flex: 1 1 auto;
  padding: 24px 28px 32px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.assistant-message {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message-meta {
  display: flex;
  gap: 10px;
  align-items: center;
  font-size: 0.75rem;
}

.role-chip,
.model-chip {
  padding: 6px 14px;
  background: rgba(var(--accent-rgb), 0.12);
  border-radius: 999px;
  color: var(--accent);
}

.model-chip {
  background: var(--surface-alt);
  color: var(--text-soft);
}

.message-bubble {
  background: rgba(var(--accent-rgb), 0.08);
  border-radius: 24px;
  padding: 22px;
  border: 1px solid rgba(var(--accent-rgb), 0.16);
  backdrop-filter: blur(4px);
}

.message-bubble .markdown-content {
  margin: 0;
  padding: 0;
  font-size: 0.95rem;
  line-height: 1.8;
}

.empty-state {
  margin: auto;
  max-width: 420px;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 14px;
  color: var(--text-soft);
}

.empty-icon {
  font-size: 2.4rem;
}

.empty-state h3 {
  margin: 0;
  color: var(--text);
}

.steps {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.85rem;
}

.steps span {
  background: var(--surface-alt);
  border-radius: var(--radius-sm);
  padding: 10px;
}

.markdown-content h1,
.markdown-content h2,
.markdown-content h3,
.markdown-content h4 {
  margin-top: 1.4em;
  margin-bottom: 0.6em;
  color: var(--text);
}

.markdown-content h1 {
  font-size: 1.35em;
}

.markdown-content h2 {
  font-size: 1.2em;
  border-bottom: 1px solid var(--border);
  padding-bottom: 0.3em;
}

.markdown-content h3 {
  font-size: 1.1em;
}

.markdown-content p,
.markdown-content li {
  color: var(--text);
}

.markdown-content blockquote {
  border-right: 4px solid rgba(var(--accent-rgb), 0.4);
  padding-right: 1rem;
  margin: 0.8rem 0;
  color: var(--text-soft);
}

.markdown-content code {
  background: rgba(var(--accent-rgb), 0.15);
  border-radius: 8px;
  padding: 2px 6px;
}

.markdown-content pre {
  background: var(--surface-alt);
  border: 1px solid rgba(var(--accent-rgb), 0.18);
  border-radius: var(--radius-md);
  padding: 16px;
  overflow-x: auto;
}

.site-footer {
  margin: 0 auto 32px;
  width: min(1180px, 100% - 32px);
  text-align: center;
  font-size: 0.75rem;
  color: var(--text-soft);
  padding: 18px 0;
}

@media (max-width: 1024px) {
  .workspace {
    grid-template-columns: 1fr;
  }

  .sidebar {
    order: 2;
  }

  .conversation {
    order: 1;
  }
}

@media (max-width: 720px) {
  .top-nav {
    flex-direction: column;
    align-items: flex-start;
  }

  .nav-actions {
    width: 100%;
    justify-content: space-between;
  }

  .model-picker select {
    width: 100%;
  }

  .workspace {
    margin: 24px auto 32px;
  }

  .conversation-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .head-actions {
    align-self: flex-end;
  }

  .upload-actions {
    flex-direction: column;
    align-items: stretch;
  }
}

@media (max-width: 500px) {
  .top-nav,
  .workspace,
  .site-footer {
    width: calc(100% - 24px);
  }

  .card {
    border-radius: var(--radius-md);
    padding: 20px;
  }

  .conversation {
    border-radius: var(--radius-md);
  }

  .message-bubble {
    border-radius: 18px;
  }
}

@media (min-width: 900px) {
  .upload-actions {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .primary {
    flex: 1 1 180px;
    font-size: 0.95rem;
  }

  .ghost {
    width: auto;
    min-height: 44px;
  }
}
</style>
