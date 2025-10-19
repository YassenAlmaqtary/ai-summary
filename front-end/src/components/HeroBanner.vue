<template>
  <header class="hero" dir="rtl">
    <div class="hero-copy">
      <span class="hero-tag">منصة تلخيص ذكية</span>
      <h1>حوّل مذكرات الدراسة إلى ملخصات جاهزة للمراجعة</h1>
      <p>
        ارفع ملفات الدروس بصيغة PDF ودَع "رفيق الملخصات" ينسّق لك أبرز الأفكار، النقاط
        المهمة، والأسئلة المتوقعة في دقائق معدودة.
      </p>
      <div class="hero-actions">
        <button class="hero-cta" type="button" @click="$emit('go-upload')">ابدأ الآن</button>
        <button class="hero-secondary" type="button" @click="$emit('show-sample')">تصفّح ملخص تجريبي</button>
      </div>
    </div>
    <div class="hero-visual">
      <div class="hero-card">
        <h3>لماذا يحبنا الطلاب؟</h3>
        <ul>
          <li>عرض محادثة شبيه بتجربة ChatGPT</li>
          <li>تنسيق Markdown تلقائي جاهز للطباعة</li>
          <li>أسئلة وأجوبة ختامية لاختبار الفهم</li>
        </ul>
      </div>
    </div>
  </header>
</template>

<script>
export default {
  name: 'HeroBanner'
}
</script>

<style scoped>
.hero {
  width: min(1180px, 100% - 32px);
  margin: 32px auto 0;
  padding: clamp(28px, 4vw, 44px);
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: clamp(24px, 4vw, 48px);
  align-items: center;
  background: linear-gradient(
    135deg,
    rgba(var(--accent-rgb, 37 99 235), 0.14),
    rgba(var(--accent-rgb, 37 99 235), 0.06)
  );
  border-radius: 32px;
  border: 1px solid rgba(var(--accent-rgb, 37 99 235), 0.18);
  box-shadow: 0 28px 60px rgba(15, 23, 42, 0.18);
}

.hero-copy h1 {
  margin: 12px 0 16px;
  font-size: clamp(1.6rem, 4vw, 2.35rem);
  line-height: 1.35;
}

.hero-copy p {
  margin: 0;
  color: var(--text-soft, rgba(15, 23, 42, 0.72));
  line-height: 1.8;
  font-size: clamp(0.95rem, 2vw, 1.05rem);
}

.hero-tag {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--surface, #fff);
  color: var(--accent, #2563eb);
  font-weight: 700;
  font-size: 0.85rem;
  border-radius: 999px;
  padding: 6px 16px;
  box-shadow: 0 8px 20px rgba(var(--accent-rgb, 37 99 235), 0.2);
}

.hero-actions {
  margin-top: 24px;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.hero-cta,
.hero-secondary {
  border-radius: 999px;
  padding: 12px 22px;
  font-size: 0.95rem;
  font-weight: 700;
  border: none;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.hero-cta {
  background: linear-gradient(135deg, var(--accent, #2563eb), #4338ca);
  color: #fff;
  box-shadow: 0 20px 36px rgba(var(--accent-rgb, 37 99 235), 0.32);
}

.hero-cta:hover {
  transform: translateY(-2px);
}

.hero-secondary {
  background: rgba(255, 255, 255, 0.75);
  color: var(--text, #1f2937);
  border: 1px solid rgba(var(--accent-rgb, 37 99 235), 0.28);
}

.hero-secondary:hover {
  transform: translateY(-1px);
}

.hero-visual {
  display: flex;
  justify-content: center;
}

.hero-card {
  width: min(320px, 100%);
  background: var(--surface, #ffffff);
  border-radius: 24px;
  padding: 22px;
  border: 1px solid rgba(var(--accent-rgb, 37 99 235), 0.25);
  box-shadow: 0 24px 48px rgba(15, 23, 42, 0.12);
}

.hero-card h3 {
  margin: 0;
  font-size: 1.05rem;
}

.hero-card ul {
  margin: 18px 0 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 10px;
  color: var(--text, rgba(31, 41, 55, 0.9));
  font-size: 0.9rem;
}

.hero-card li {
  position: relative;
  padding-inline-start: 22px;
}

.hero-card li::before {
  content: '✔';
  position: absolute;
  inset-inline-start: 0;
  color: #2563eb;
}

@media (max-width: 640px) {
  .hero {
    border-radius: 24px;
    margin-top: 20px;
    grid-template-columns: 1fr;
    text-align: center;
  }

  .hero-actions {
    justify-content: center;
  }

  .hero-card {
    margin-inline: auto;
  }
}

@media (max-width: 480px) {
  .hero {
    padding: 24px 18px;
    gap: 20px;
  }

  .hero-copy h1 {
    font-size: clamp(1.4rem, 6vw, 1.8rem);
  }

  .hero-copy p {
    font-size: 0.95rem;
  }

  .hero-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .hero-cta,
  .hero-secondary {
    width: 100%;
  }
}
</style>
