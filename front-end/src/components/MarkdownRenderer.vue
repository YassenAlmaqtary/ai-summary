<template>
  <div class="markdown-content" v-html="renderedMarkdown"></div>
</template>

<script>
import { marked } from 'marked';

export default {
  props: {
    source: {
      type: String,
      default: ''
    }
  },
  computed: {
    renderedMarkdown() {
        console.log('Rendering markdown:', typeof(this.source), this.source);
      // Configure marked to handle RTL and other options if needed
    //   const renderer = new marked.Renderer();
      // Example: customize heading rendering
    //   renderer.heading = (text, level) => {
    //     return `<h${level} class="md-heading-${level}">${text}</h${level}>`;
    //   };
        return marked.parse(this.source);
    //   return marked(this.source, { renderer });
    }
  }
}
</script>

<style>
.markdown-content {
  line-height: 1.7;
  font-size: 0.9rem;
  color: var(--c-text);
}

.markdown-content h1,
.markdown-content h2,
.markdown-content h3,
.markdown-content h4 {
  font-weight: 700;
  margin-top: 1.5em;
  margin-bottom: 0.8em;
  color: var(--c-text);
}

.markdown-content h1, .md-heading-1 { font-size: 1.4em; }
.markdown-content h2, .md-heading-2 { font-size: 1.25em; border-bottom: 1px solid var(--c-border); padding-bottom: .3em; }
.markdown-content h3, .md-heading-3 { font-size: 1.1em; }

.markdown-content p {
  margin-bottom: 1em;
}

.markdown-content strong {
  font-weight: 700;
}

.markdown-content ul,
.markdown-content ol {
  padding-right: 2rem; /* RTL padding */
  margin-bottom: 1em;
}

.markdown-content li {
  margin-bottom: 0.5em;
}

.markdown-content code {
  background-color: rgba(var(--c-accent-rgb), 0.1);
  padding: 0.2em 0.4em;
  border-radius: 6px;
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.85em;
}

.markdown-content pre {
  background-color: var(--c-surface-alt);
  border: 1px solid var(--c-border);
  padding: 1rem;
  border-radius: var(--radius-m);
  overflow-x: auto;
}

.markdown-content pre code {
  background: none;
  padding: 0;
}

.markdown-content blockquote {
  border-right: 4px solid var(--c-accent); /* RTL border */
  padding-right: 1rem;
  margin-right: 0;
  color: var(--c-text-soft);
}
</style>
