<template>
  <div class="app-root" dir="rtl" :data-theme="theme">
    <!-- شريط علوي -->
    <header class="topbar">
      <div class="brand">
        <img class="logo" src="https://cdn-icons-png.flaticon.com/512/337/337946.png" alt="logo" />
        <div class="brand-text">
          <h1>ملخِّص الدروس</h1>
          <span class="tagline">رف  ع سريع • تلخيص ذكي • عربية واضحة</span>
        </div>
      </div>
      <div class="top-actions">
        <select v-model="model" class="model-select" :disabled="loading">
          <option v-for="m in models" :key="m" :value="m">{{ m }}</option>
        </select>
        <div class="layout-modes" role="group" aria-label="اختيار نمط العرض">
          <button :class="{'active': layoutMode==='side'}" @click="layoutMode='side'" title="وضع جانبي">🪟</button>
          <button :class="{'active': layoutMode==='stack'}" @click="layoutMode='stack'" title="وضع متراكم">🧱</button>
          <button :class="{'active': layoutMode==='focus'}" @click="layoutMode='focus'" title="وضع تركيز">🎯</button>
        </div>
        <button class="ghost" @click="toggleTheme" :title="isDark ? 'وضع فاتح' : 'وضع داكن'">{{ isDark ? '☀️' : '🌙' }}</button>
      </div>
    </header>

    <!-- شبكة المحتوى -->
    <div class="layout" :class="layoutClasses">
      <!-- لوحة الرفع والإجراءات -->
      <section v-if="showUploadPanel" class="panel upload-panel" :class="{'floating-focus': layoutMode==='focus' && summary}">
        <h2 class="panel-title">📄 ارفع ملف PDF</h2>
        <p class="hint">اسحب الملف أو اضغط للاختيار (يدعم العربية حتى 15MB)</p>
        <FileUpload @file-selected="setFile" />
        <div class="actions-row">
          <button class="primary" :disabled="!file || loading" @click="summarize">
            <span v-if="!loading">🚀 تلخيص الآن</span>
            <span v-else>⏳ جاري التلخيص {{ formatElapsed(elapsed) }}</span>
          </button>
          <button v-if="loading" class="danger" @click="cancel">إلغاء</button>
          <button v-if="summary && !loading" class="soft" @click="reset">تفريغ</button>
        </div>
        <div v-if="summary && !loading" class="after-actions">
          <button @click="copySummary" class="mini">نسخ</button>
          <button @click="downloadSummary" class="mini">تنزيل</button>
        </div>
        <p v-if="error" class="error-box">{{ error }}</p>
        <div v-if="loading" class="live-indicator">
          <span class="dot"></span>
          <span>يبث التلخيص...</span>
        </div>
      </section>

      <!-- لوحة الملخص (قابلة للطي) -->
      <aside class="panel summary-panel" v-if="summary" :class="{'collapsed-focus': layoutMode==='focus' && !showUploadPanel}">
        <header class="panel-head">
          <h2>📑 الملخص</h2>
          <div class="panel-head-actions">
            <button @click="copySummary" title="نسخ" class="icon-btn">📋</button>
            <button @click="downloadSummary" title="تنزيل" class="icon-btn">⬇️</button>
            <button v-if="layoutMode!=='focus'" @click="collapseSummary = !collapseSummary" :title="collapseSummary ? 'إظهار' : 'إخفاء'" class="icon-btn">{{ collapseSummary ? '⬅️' : '➡️' }}</button>
            <button v-else @click="toggleUploadFocus" :title="showUploadPanel ? 'إخفاء الرفع' : 'إظهار الرفع'" class="icon-btn">{{ showUploadPanel ? '📥' : '📤' }}</button>
          </div>
        </header>
        <transition name="fade">
          <div v-show="!collapseSummary" class="summary-scroll">
             <!-- <Summary :summary="summary" /> -->
            <MarkdownRenderer :source="summary" />
          </div>
        </transition>
      </aside>
    </div>

    <footer class="site-footer">© {{ year }} جميع الحقوق محفوظة • مشروع تعليمي</footer>
    <Toast :show="showToast" :message="toastMessage" :type="toastType" @close="showToast=false" />
  </div>
</template>

<script>
import FileUpload from './components/FileUpload.vue'
import Summary from './components/Summary.vue'
import MarkdownRenderer from './components/MarkdownRenderer.vue'
import Toast from './components/Toast.vue'


export default {
  // components: { FileUpload, Summary, Toast },
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
      showToast:false,
      toastType:'info',
      toastMessage:'',
      _toastTimer:null,
      model:'',
      models:[],
      collapseSummary:false,
      theme:'light'
      ,layoutMode:'side'
      ,showUploadPanel:true
    }
  },
  computed:{
    isDark(){ return this.theme==='dark' },
    layoutClasses(){
      return [
        this.summary ? 'with-summary' : '',
        `mode-${this.layoutMode}`
      ]
    }
  },
  mounted(){
    this.theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark':'light'
    document.documentElement.dataset.theme = this.theme
    this.loadModels();
  },
  methods: {
    async loadModels(){
      try {
        const res = await fetch('http://localhost:9000/models');
        if(!res.ok) return;
        const data = await res.json();
        this.models = data.models || [];
        this.model = data.default || this.models[0] || '';
      } catch(e){ /* ignore */ }
    },
    setFile(f){ this.file = f },
    toggleTheme(){
      this.theme = this.isDark ? 'light':'dark'
      document.documentElement.dataset.theme = this.theme
      this.notify(this.isDark ? 'تم تفعيل الوضع الفاتح' : 'تم تفعيل الوضع الداكن','success')
    },
    formatElapsed(s) {
      const m = Math.floor(s / 60).toString().padStart(2, '0')
      const ss = (s % 60).toString().padStart(2, '0')
      return `${m}:${ss}`
    },
    async summarize() {
      if (!this.file) {
        this.notify('⚠️ اختر ملف PDF أولاً!','error')
        return
      }
      this.summary = ''
      this.error = ''
      this.loading = true
      this.elapsed = 0
      if (this._timer) clearInterval(this._timer)
      this._timer = setInterval(() => { this.elapsed++ }, 1000)
      try {
        // 1. ارفع الملف أولاً
        const formData = new FormData();
        formData.append('file', this.file);
        const res = await fetch('http://localhost:9000/upload', { method: 'POST', body: formData });
        if(!res.ok) throw new Error('فشل رفع الملف')
        const data = await res.json();
        const sessionId = data.session_id;
        // 2. افتح EventSource على /summarize-gemini
        const url = `http://localhost:9000/summarize-gemini?session_id=${encodeURIComponent(sessionId)}&model=${encodeURIComponent(this.model)}`;
        const es = new EventSource(url);
        this._es = es;
        es.onmessage = (event) => {
          this.summary += event.data;
        };
        es.addEventListener('status', (e)=>{
          if(e.data === 'DONE') {
            this.loading = false;
            this._closeES();
            this.notify('اكتمل التلخيص','success')
          }
        });
        es.addEventListener('error', ()=>{
          this.loading = false;
          this._closeES();
          this.notify('تعذر إكمال التلخيص','error')
        });
      } catch (e) {
        this.notify(e.message,'error')
      } finally {
        if (!this.loading && this._timer) { clearInterval(this._timer); this._timer = null }
      }
    },
    cancel(){
      this.loading = false;
      this._closeES();
      if (this._timer) { clearInterval(this._timer); this._timer = null }
    },
    _closeES(){ if(this._es){ this._es.close(); this._es=null } },
    copySummary(){ navigator.clipboard.writeText(this.summary); this.notify('تم النسخ','success') },
    downloadSummary(){
      const blob = new Blob([this.summary], {type:'text/plain;charset=utf-8'});
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'summary.txt';
      a.click();
      URL.revokeObjectURL(a.href);
      this.notify('تم التنزيل','success')
    },
    reset(){ this.summary=''; this.error=''; this.file=null; this.collapseSummary=false; this.notify('تم التفريغ','success') },
    toggleUploadFocus(){
      if(this.layoutMode!=='focus') return;
      this.showUploadPanel = !this.showUploadPanel;
    },
    notify(msg,type='info'){
      this.toastMessage = msg;
      if(type==='error') this.error = msg; else this.error='';
      this.toastType=type; this.showToast=true;
      clearTimeout(this._toastTimer);
      this._toastTimer=setTimeout(()=>{ this.showToast=false },4000)
    }
  }
}
</script>

<style>
/* ========== المتغيرات (سمة خفيفة) ========== */
:root {
      --bg-gradient: linear-gradient(130deg,#5b21b6,#2563eb 55%,#0ea5e9);
      --c-bg: #f8fafc;
      --c-surface: #ffffffcc;
      --c-surface-alt:#ffffffee;
      --c-border:#e2e8f0;
      --c-text:#1e293b;
      --c-text-soft:#475569;
      --c-accent:#6366f1;
      --c-accent-rgb:99 102 241;
      --c-danger:#dc2626;
      --radius-l:26px;
      --radius-m:16px;
      --shadow-soft:0 4px 16px rgba(15,23,42,.08),0 2px 6px rgba(0,0,0,.05);
      --shadow-focus:0 0 0 3px rgba(99,102,241,.35);
      --transition: .18s cubic-bezier(.4,.2,.2,1);
    }
    [data-theme='dark'] {
      --bg-gradient: linear-gradient(120deg,#0f172a,#312e81 55%,#1e3a8a);
      --c-bg:#0f172a;
      --c-surface:#1e293bcc;
      --c-surface-alt:#1e293bee;
      --c-border:#334155;
      --c-text:#f1f5f9;
      --c-text-soft:#94a3b8;
      --c-accent:#818cf8;
      --c-accent-rgb:129 140 248;
      --c-danger:#f87171;
      --shadow-soft:0 4px 18px rgba(0,0,0,.55),0 2px 6px rgba(0,0,0,.35);
    }

    /* ========== إعادة ضبط بسيطة ========== */
    *,*::before,*::after{box-sizing:border-box;}
    html,body,#app,.app-root{margin:0;padding:0;min-height:100%;font-family:'Cairo',system-ui,sans-serif;}
    body{background:var(--bg-gradient);background-attachment:fixed;color:var(--c-text);}

    /* ========== الشريط العلوي ========== */
    .topbar{display:flex;align-items:center;justify-content:space-between;padding:0.9rem 1.4rem;margin:clamp(.6rem,1.2vh,1.2rem) auto 0;max-width:1180px;background:var(--c-surface);backdrop-filter:blur(8px);border:1px solid var(--c-border);border-radius:var(--radius-m);box-shadow:var(--shadow-soft);}
    .brand{display:flex;align-items:center;gap:.85rem;}
    .logo{width:54px;height:54px;object-fit:contain;filter:drop-shadow(0 4px 10px rgba(0,0,0,.15));}
  .brand-text h1{font-size:1.55rem;margin:0;font-weight:800;letter-spacing:-.5px;background:linear-gradient(90deg,#4338ca,#2563eb,#0ea5e9);background-clip:text;-webkit-background-clip:text;color:transparent;}
    .tagline{font-size:.7rem;color:var(--c-text-soft);font-weight:500;display:block;margin-top:2px;letter-spacing:.5px}
  .top-actions{display:flex;align-items:center;gap:.6rem;}
  .layout-modes{display:flex;align-items:center;gap:.25rem;background:var(--c-surface-alt);padding:.25rem .45rem;border:1px solid var(--c-border);border-radius:12px;}
  .layout-modes button{background:transparent;border:none;cursor:pointer;font-size:.85rem;padding:.35rem .45rem;border-radius:8px;transition:var(--transition);}
  .layout-modes button.active,.layout-modes button:hover{background:rgba(var(--c-accent-rgb)/.15)}
    .model-select{padding:.55rem .9rem;border:1px solid var(--c-border);border-radius:12px;background:var(--c-surface-alt);font-family:inherit;font-size:.9rem;cursor:pointer;min-width:140px;}
    .model-select:focus{outline:none;box-shadow:var(--shadow-focus);}
    .ghost{background:var(--c-surface-alt);border:1px solid var(--c-border);padding:.55rem .9rem;border-radius:12px;cursor:pointer;font-size:1rem;transition:var(--transition);}
    .ghost:hover{background:rgba(var(--c-accent-rgb)/.1)}

    /* ========== تخطيط المحتوى ========== */
  /* الشبكة: افتراضي عمود واحد، وعند وجود ملخص تصبح عمودين */
  .layout{max-width:1180px;margin:1.2rem auto 2rem;display:grid;grid-template-columns:1fr;gap:1.4rem;align-items:start;padding:0 1rem;justify-items:center;}
  .layout.with-summary.mode-side{grid-template-columns:minmax(0,440px) minmax(0,1fr);justify-items:stretch;}
  .layout.with-summary.mode-stack{grid-template-columns:1fr;}
  .layout.with-summary.mode-focus{grid-template-columns:minmax(0,340px) 1fr;}
  .layout:not(.with-summary){max-width:820px;}
  .mode-stack .summary-panel{order:2;}
  .mode-stack .upload-panel{order:1;}
  .mode-focus .upload-panel.floating-focus{position:sticky;top:6.2rem;align-self:start;max-height:calc(100dvh - 8rem);overflow:auto;}
  .mode-focus .summary-panel{grid-column:2/-1;}
  .mode-focus .summary-panel.collapsed-focus{grid-column:1/-1;}
    @media (max-width:1100px){.layout,.layout.with-summary{grid-template-columns:1fr;}}

    /* ========== اللوحات العامة ========== */
  .panel{background:var(--c-surface);backdrop-filter:blur(10px);border:1px solid var(--c-border);border-radius:var(--radius-l);padding:1.8rem 2rem 2.2rem;box-shadow:var(--shadow-soft);position:relative;overflow:hidden;width:100%;max-width:820px;transition:background .25s ease,border-color .25s ease;}
  .panel:before{content:"";position:absolute;inset:0;background:radial-gradient(circle at 78% 28%,rgba(var(--c-accent-rgb)/0.10),transparent 65%);pointer-events:none;}
    .panel-title{margin:0 0 .4rem;font-size:1.2rem;font-weight:700;}
    .hint{margin:.1rem 0 1.1rem;font-size:.75rem;color:var(--c-text-soft);font-weight:500;letter-spacing:.3px}

    /* ========== لوحة الرفع ========== */
    .upload-panel{display:flex;flex-direction:column;gap:1.4rem;}

    /* ========== لوحة الملخّص ========== */
  .summary-panel{display:flex;flex-direction:column;gap:1rem;max-height:calc(100dvh - 9rem);position:sticky;top:6.2rem;align-self:start;}
  .layout.with-summary .summary-panel{max-width:420px;}
    .panel-head{display:flex;align-items:center;justify-content:space-between;margin:-.3rem 0 .2rem;}
    .panel-head h2{margin:0;font-size:1.05rem;font-weight:700;letter-spacing:.5px;}
    .panel-head-actions{display:flex;align-items:center;gap:.4rem;}
    .icon-btn{background:var(--c-surface-alt);border:1px solid var(--c-border);padding:.45rem .6rem;border-radius:10px;cursor:pointer;transition:var(--transition);font-size:.85rem;}
    .icon-btn:hover{background:rgba(var(--c-accent-rgb)/.15)}
    .summary-scroll{max-height:520px;overflow:auto;padding:.4rem .2rem .6rem;}
  .summary-panel .summary-scroll{max-height:100%;padding-inline-start:.2rem;}
    .summary-scroll::-webkit-scrollbar{width:6px;}
    .summary-scroll::-webkit-scrollbar-thumb{background:rgba(var(--c-accent-rgb)/.4);border-radius:10px;}

    /* ========== الأزرار العامة ========== */
    button{font-family:inherit;}
    .actions-row{display:flex;flex-wrap:wrap;gap:.8rem;align-items:center;}
    .primary{background:linear-gradient(90deg,#10b981,#059669);color:#fff;border:none;padding:.85rem 1.6rem;font-size:.95rem;font-weight:600;border-radius:14px;cursor:pointer;box-shadow:0 6px 18px rgba(16,185,129,.35);transition:var(--transition);}
    .primary:disabled{opacity:.55;cursor:not-allowed;filter:grayscale(.4);} 
    .primary:not(:disabled):hover{filter:brightness(1.05);transform:translateY(-2px);} 
    .danger{background:#dc2626;color:#fff;border:none;padding:.7rem 1.2rem;border-radius:12px;font-size:.8rem;cursor:pointer;box-shadow:0 4px 12px rgba(220,38,38,.4);}
    .danger:hover{background:#b91c1c}
    .soft{background:var(--c-surface-alt);border:1px solid var(--c-border);padding:.7rem 1.2rem;border-radius:12px;font-size:.8rem;cursor:pointer;}
    .soft:hover{background:rgba(var(--c-accent-rgb)/.12)}
    .mini{background:var(--c-accent);color:#fff;border:none;padding:.45rem .9rem;border-radius:10px;font-size:.7rem;cursor:pointer;font-weight:500;}
    .mini:hover{filter:brightness(1.06)}

    /* ========== التغذية الحية ========== */
    .live-indicator{display:inline-flex;align-items:center;gap:.55rem;font-size:.75rem;color:var(--c-text-soft);font-weight:600;letter-spacing:.5px;margin-top:.4rem;}
    .dot{width:9px;height:9px;border-radius:50%;background:radial-gradient(circle at 30% 30%,#10b981,#047857);animation:pulse 1.1s infinite ease-in-out;box-shadow:0 0 0 4px rgba(16,185,129,.25);}
    @keyframes pulse{50%{transform:scale(.55);box-shadow:0 0 0 2px rgba(16,185,129,.35)}}

    /* ========== أخطاء وتنبيهات ========== */
    .error-box{background:#fee2e2;color:#b91c1c;border:1px solid #fecaca;padding:.65rem .9rem;font-size:.7rem;border-radius:10px;font-weight:500;}
    [data-theme='dark'] .error-box{background:#7f1d1d;color:#fecaca;border-color:#fecaca33;}

    /* ========== التذييل ========== */
    .site-footer{text-align:center;font-size:.65rem;color:var(--c-text-soft);padding:1.4rem 0 1.6rem;margin-top:1rem;}

  /* تخصيص مظهر الملخص داخل اللوحة ليصبح بدون خلفية مزدوجة */
  .summary-panel .summary-box{background:transparent;box-shadow:none;margin:0;padding:0;max-width:100%;}
  .summary-panel .summary-box .summary-content{max-height:unset;padding:0;}
  .summary-panel .summary-box .header-line{display:none;}

    /* ========== انتقالات ========== */
    .fade-enter-active,.fade-leave-active{transition:opacity .25s ease;}
    .fade-enter-from,.fade-leave-to{opacity:0;}

    @media (max-width:640px){
      .topbar{padding:.75rem 1rem;}
      .brand-text h1{font-size:1.25rem;}
      .panel{padding:1.5rem 1.2rem 1.9rem;}
      .layout{padding:0 .5rem;margin-top:.8rem;}
      .summary-scroll{max-height:420px;}
  }
</style>
