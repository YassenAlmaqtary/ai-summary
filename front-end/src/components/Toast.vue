<template>
  <transition name="fade">
    <div v-if="show" class="toast" :class="type">
      <span class="msg">{{ message }}</span>
      <button class="close" @click="$emit('close')">×</button>
    </div>
  </transition>
</template>
<script>
export default { props:{ message:String, type:{type:String,default:'info'}, show:Boolean } }
</script>
<style scoped>
.toast { position:fixed; inset-inline-start:50%; top:18px; transform:translateX(-50%); background:#1f2937; color:#fff; padding:12px 18px; border-radius:14px; box-shadow:0 6px 18px rgba(0,0,0,.25); display:flex; gap:12px; align-items:center; z-index:1000; font-size:.95rem; }
.toast.success { background:#065f46; }
.toast.error { background:#b91c1c; }
.close { background:transparent; border:none; color:#fff; font-size:1.1rem; cursor:pointer; }
.fade-enter-active,.fade-leave-active { transition:.25s opacity, .25s transform; }
.fade-enter-from,.fade-leave-to { opacity:0; transform:translate(-50%, -6px); }
</style>
