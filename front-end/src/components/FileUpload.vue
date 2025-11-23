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
.uploader { width:100%; border:2px dashed var(--accent); border-radius:18px; padding:28px 22px; background:var(--surface-alt); text-align:center; position:relative; transition:.25s border-color,.25s background,.25s transform; cursor:pointer; }
.uploader:hover { transform:translateY(-1px); }
.uploader.dragging { background:rgba(var(--accent-rgb),0.15); border-color:var(--accent); }
.label { display:flex; flex-direction:column; gap:10px; align-items:center; outline:none; }
.icon { font-size:2.6rem; filter: drop-shadow(0 2px 6px rgba(0,0,0,.12)); }
.texts strong { font-size:1.05rem; color:var(--text); }
.texts small { display:block; margin-top:4px; color:var(--text-soft); font-size:.73rem; }
.choose-btn { margin-top:8px; background:var(--accent); color:#fff; border:none; padding:8px 18px; border-radius:10px; font-size:.85rem; cursor:pointer; box-shadow:0 4px 16px rgba(var(--accent-rgb),.3); transition:.25s transform,.25s box-shadow; }
.choose-btn:hover { transform:translateY(-1px); box-shadow:0 6px 18px rgba(var(--accent-rgb),.28); }
.choose-btn:focus-visible, .uploader:focus-visible { outline:3px solid rgba(var(--accent-rgb),.35); outline-offset:4px; }
@media (max-width:640px){
  .uploader{ padding:18px 14px; }
  .icon{ font-size:2.2rem; }
  .texts strong{ font-size:.98rem; }
  .choose-btn{ width:100%; padding:10px 14px; font-size:.9rem; }
}
</style>
