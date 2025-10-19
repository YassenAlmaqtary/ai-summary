<template>
  <div class="sample" dir="rtl">
    <header class="sample-head">
      <div>
        <span class="sample-tag">مثال ملخص جاهز</span>
        <h2>ملخص درس: أخلاقيات الحاسوب</h2>
      </div>
      <button class="sample-close" type="button" @click="$emit('close')">✕</button>
    </header>
    <section class="sample-body">
      <article class="sample-section">
        <h3>## مفهوم أخلاقيات الحاسوب</h3>
        <p>
          أخلاقيات الحاسوب هي إطار القيم الذي يوجّه استخدام التقنيات الرقمية. تزرع لدى الطلبة ثقافة
          الاستخدام المسؤول وتساعدهم على إدراك أثر أفعالهم الرقمية على المجتمع.
        </p>
        <ul>
          <li>ترسيخ قيم الأمانة الرقمية والخصوصية.</li>
          <li>تحليل المخاطر القانونية والأخلاقية قبل اتخاذ القرار.</li>
          <li>الموازنة بين الابتكار وحماية حقوق الآخرين.</li>
        </ul>
      </article>
      <article class="sample-section">
        <h3>## تهديدات شائعة يجب الانتباه لها</h3>
        <p>
          من أبرز المخاطر التي تواجه المؤسسات: البرمجيات الخبيثة، التصيد الاحتيالي، والهجمات التي تستهدف
          تدمير الخدمة أو سرقة البيانات.
        </p>
        <ul>
          <li><strong>البرمجيات الخبيثة:</strong> فيروسات وديدان تستخدم غالباً لابتزاز الضحايا.</li>
          <li><strong>التصيد الاحتيالي:</strong> رسائل مزيفة تنتحل مؤسسات موثوقة لسرقة كلمات المرور.</li>
          <li><strong>هجمات حجب الخدمة:</strong> إغراق الخوادم بطلبات وهمية لتعطيلها.</li>
        </ul>
      </article>
      <article class="sample-section">
        <h3>## أسئلة وأجوبة</h3>
        <p>- ما أكبر فائدة لتعلم أخلاقيات الحاسوب؟ بناء وعي مجتمعي مسؤول يحمي البيانات والحقوق.</p>
        <p>- كيف أحمي نفسي من التصيد؟ التحقق من الروابط وتفعيل المصادقة الثنائية دائماً.</p>
        <p>- ما قاعدة ذهبية للتعامل مع البيانات؟ لا تشارك معلومات حساسة إلا مع جهات مخوّلة.</p>
      </article>
    </section>
  </div>
</template>

<script>
export default {
  name: 'SampleSummary'
}
</script>

<style scoped>
.sample {
  width: min(680px, 94vw);
  max-height: min(80vh, 720px);
  overflow-y: auto;
  background: var(--surface, #ffffff);
  border-radius: 28px;
  border: 1px solid rgba(var(--accent-rgb, 37 99 235), 0.22);
  box-shadow: 0 32px 68px rgba(15, 23, 42, 0.22);
  padding: 28px 32px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.sample-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.sample-head h2 {
  margin: 10px 0 0;
  font-size: 1.4rem;
}

.sample-tag {
  display: inline-flex;
  padding: 6px 18px;
  background: rgba(var(--accent-rgb, 37 99 235), 0.12);
  border-radius: 999px;
  color: var(--accent, #2563eb);
  font-weight: 700;
  font-size: 0.8rem;
}

.sample-close {
  border: none;
  background: rgba(15, 23, 42, 0.12);
  width: 36px;
  height: 36px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 0.95rem;
}

.sample-body {
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.sample-section h3 {
  margin: 0 0 12px;
  font-size: 1.05rem;
}

.sample-section p {
  color: var(--text, #1f2937);
  line-height: 1.7;
  margin: 0 0 12px;
}

.sample-section ul {
  margin: 0;
  padding-inline-start: 20px;
  color: var(--text, #1f2937);
  line-height: 1.6;
}

@media (max-width: 560px) {
  .sample {
    border-radius: 22px;
    padding: 22px;
  }
}
</style>
