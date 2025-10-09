<template>
  <div class="uploader" :class="{ dragging }" @dragover.prevent="dragging=true" @dragleave.prevent="dragging=false" @drop.prevent="onDrop">
    <input ref="fileInput" id="file" type="file" accept="application/pdf" @change="onFileChange" hidden />
    <label for="file" class="label" @keydown.enter.prevent="trigger" @keydown.space.prevent="trigger" tabindex="0">
      <div class="icon">📄</div>
      <div class="texts">
        <strong v-if="!fileName">اسحب ملف PDF هنا أو اضغط للاختيار</strong>
        <strong v-else>{{ fileName }}</strong>
        <small>الحد الأقصى 15MB - يدعم العربية</small>
      </div>
      <button type="button" class="choose-btn" @click.stop="trigger">اختيار ملف</button>
    </label>
  </div>
</template>

<script>
export default {
  emits: ['file-selected'],
  data(){
    return { dragging:false, fileName:'' }
  },
  methods: {
    trigger(){ this.$refs.fileInput.click() },
    onFileChange(e){
      const f=e.target.files[0];
      if(!f) return;
      this.fileName = f.name;
      this.$emit('file-selected', f)
    },
    onDrop(e){
      this.dragging=false;
      const f = e.dataTransfer.files && e.dataTransfer.files[0];
      if(!f) return;
      if(f.type!== 'application/pdf') { alert('الرجاء رفع ملف PDF'); return; }
      this.fileName = f.name;
      this.$emit('file-selected', f)
    }
  }
}
</script>

<style scoped>
.uploader { width:100%; border:2px dashed #6366f1; border-radius:18px; padding:28px 22px; background:#ffffff; text-align:center; position:relative; transition:.25s border-color,.25s background; cursor:pointer; }
.uploader.dragging { background:#eef2ff; border-color:#4f46e5; }
.label { display:flex; flex-direction:column; gap:10px; align-items:center; outline:none; }
.icon { font-size:2.6rem; filter: drop-shadow(0 2px 6px rgba(0,0,0,.15)); }
.texts strong { font-size:1.05rem; color:#1f2937; }
.texts small { display:block; margin-top:4px; color:#6b7280; font-size:.73rem; }
.choose-btn { margin-top:8px; background:#4f46e5; color:#fff; border:none; padding:8px 18px; border-radius:8px; font-size:.85rem; cursor:pointer; box-shadow:0 4px 14px rgba(79,70,229,.3); }
.choose-btn:focus-visible, .uploader:focus-visible { outline:3px solid #6366f1; outline-offset:4px; }
@media (max-width:640px){
  .uploader{ padding:18px 14px; }
  .icon{ font-size:2.2rem; }
  .texts strong{ font-size:.98rem; }
  .choose-btn{ width:100%; padding:10px 14px; font-size:.9rem; }
}
</style>
