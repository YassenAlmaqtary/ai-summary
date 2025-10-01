<!-- <template>
  <div v-if="summary" class="mt-6 p-4 border rounded bg-gray-50">
    <h2 class="font-semibold mb-2">📌 الملخص:</h2>
    <pre class="whitespace-pre-wrap">{{ summary }}</pre>
  </div>
</template>

<script>
export default {
  props: ['summary'],
};
</script> -->


<template>
  <div class="summary-box" v-if="cleanBlocks.length">
    <header class="header-line">
      <h3>📑 الملخص</h3>
      <div class="inline-actions">
        <button @click="copyAll" title="نسخ">نسخ</button>
        <button @click="downloadTxt" title="تنزيل">تنزيل</button>
      </div>
    </header>
    <div class="summary-content">
      <component
        v-for="(blk,i) in cleanBlocks"
        :key="i"
        :is="blk.type==='ul' ? 'ul' : blk.type==='ol' ? 'ol' : blk.type==='h' ? 'h4':'p'"
        class="blk"
      >
        <template v-if="blk.type==='ul'">
          <li v-for="(li,j) in blk.items" :key="j">{{ li }}</li>
        </template>
        <template v-else-if="blk.type==='ol'">
          <li v-for="(li,j) in blk.items" :key="j">{{ li }}</li>
        </template>
        <template v-else>{{ blk.text }}</template>
      </component>
    </div>
  </div>
</template>

<script>
export default {
  props: ['summary'],
  computed: {
    lines(){
      return this.summary.split(/\n+/).map(l=>l.trim()).filter(Boolean)
    },
    cleanBlocks(){
      const blocks=[]
      let buf=[]
      const flushPara=()=>{ if(buf.length){ blocks.push({type:'p', text: buf.join(' ') }); buf=[] } }
      let listMode=null // 'ul' | 'ol'
      let listItems=[]
      const flushList=()=>{ if(listMode && listItems.length){ blocks.push({type:listMode, items:[...listItems]}); listItems=[]; listMode=null } }
      for(const raw of this.lines){
        // Heading pattern (**عنوان:** أو عنوان:)
        if(/^(\*\*?)?\s*[^:]{2,20}\s*:\s*$/.test(raw)){ flushPara(); flushList(); const title= raw.replace(/^[*\s]+/,'').replace(/[:\s]+$/,''); blocks.push({type:'h', text:title}); continue }
        // Bullet patterns (- أو * أو •)
        if(/^[-*•]\s+/.test(raw)){ flushPara(); if(listMode && listMode!=='ul') flushList(); listMode='ul'; listItems.push(raw.replace(/^[-*•]\s+/,'')); continue }
        // Numbered list (1. أو 1-)
        if(/^\d+[\.-]\s+/.test(raw)){ flushPara(); if(listMode && listMode!=='ol') flushList(); listMode='ol'; listItems.push(raw.replace(/^\d+[\.-]\s+/,'')); continue }
        // Separator
        if(/^[-_*]{3,}$/.test(raw)){ flushPara(); flushList(); continue }
        // Normal line
        if(raw){ buf.push(raw) }
      }
      flushPara(); flushList();
      return blocks
    }
  },
  methods:{
    copyAll(){ navigator.clipboard.writeText(this.summary) },
    downloadTxt(){
      const blob = new Blob([this.summary],{type:'text/plain;charset=utf-8'});
      const a=document.createElement('a');
      a.href=URL.createObjectURL(blob); a.download='summary.txt'; a.click(); URL.revokeObjectURL(a.href);
    }
  }
}
</script>

<style>
 .summary-box { background:#fff; border-radius:16px; padding:20px 24px; max-width:760px; width:100%; margin:20px auto; box-shadow:0 8px 28px rgba(0,0,0,0.1); text-align:right; line-height:1.7; }
 .header-line { display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:6px; }
 .header-line h3 { margin:0; font-size:1.25rem; font-weight:700; color:#1f2937; }
 .inline-actions button { background:#1f2937; color:#fff; border:none; padding:6px 12px; border-radius:8px; font-size:.7rem; cursor:pointer; margin-inline-start:6px; }
 .inline-actions button:hover { filter:brightness(1.15); }
 .summary-content { font-size:1.02rem; color:#374151; word-wrap:break-word; max-height:420px; overflow-y:auto; padding-inline-end:8px; }
 .summary-content::-webkit-scrollbar { width:6px; }
 .summary-content::-webkit-scrollbar-thumb { background:#9ca3af; border-radius:8px; }
 .blk { margin:0 0 10px; }
 h4.blk { font-size:1.05rem; margin-top:18px; margin-bottom:8px; font-weight:700; color:#111827; position:relative; }
 h4.blk:before { content:""; position:absolute; right:0; top:100%; width:60px; height:2px; background:#e5e7eb; }
 ul.blk, ol.blk { padding:0 1rem 0 0; margin:0 0 14px; }
 ul.blk li { list-style:square; margin:0 0 4px; }
 ol.blk { counter-reset:item; }
 ol.blk li { list-style:decimal; margin:0 0 4px; }
 @media (prefers-color-scheme: dark){
  .summary-box { background:#1f2937; box-shadow:0 4px 18px rgba(0,0,0,0.5); }
  .summary-content { color:#e5e7eb; }
  .header-line h3 { color:#f3f4f6; }
  h4.blk { color:#f9fafb; }
  .inline-actions button { background:#334155; }
 }
</style>

