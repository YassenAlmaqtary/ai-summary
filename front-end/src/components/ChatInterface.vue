<template>
  <div class="chat-interface" dir="rtl">
    <div class="chat-messages" ref="messagesContainer">
      <div v-if="messages.length === 0" class="empty-chat">
        <div class="empty-icon">💬</div>
        <h3>ابدأ محادثة مع الوكيل الذكي</h3>
        <p>اطرح أسئلة حول الوثيقة المرفوعة أو اطلب ملخصاً</p>
        <div class="suggestions">
          <button
            v-for="suggestion in suggestions"
            :key="suggestion"
            @click="sendMessage(suggestion)"
            class="suggestion-btn"
          >
            {{ suggestion }}
          </button>
        </div>
      </div>

      <div
        v-for="(message, index) in messages"
        :key="index"
        :class="['message', message.role]"
      >
        <div class="message-avatar">
          <span v-if="message.role === 'user'">👤</span>
          <span v-else>🤖</span>
        </div>
        <div class="message-content">
          <div class="message-header">
            <span class="message-role">{{ message.role === 'user' ? 'أنت' : 'الوكيل الذكي' }}</span>
            <span class="message-time">{{ formatTime(message.timestamp) }}</span>
          </div>
          <div class="message-body">
            <MarkdownRenderer v-if="message.role === 'assistant'" :source="message.content" />
            <p v-else>{{ message.content }}</p>
          </div>
        </div>
      </div>

      <div v-if="loading" class="message assistant">
        <div class="message-avatar">🤖</div>
        <div class="message-content">
          <div class="message-header">
            <span class="message-role">الوكيل الذكي</span>
          </div>
          <div class="message-body">
            <div class="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="chat-input-container">
      <form @submit.prevent="handleSubmit" class="chat-input-form">
        <textarea
          v-model="inputMessage"
          @keydown.enter.exact.prevent="handleSubmit"
          @keydown.enter.shift.exact="inputMessage += '\n'"
          placeholder="اكتب سؤالك هنا... (Enter للإرسال، Shift+Enter للسطر الجديد)"
          class="chat-input"
          :disabled="loading || !sessionId"
          rows="1"
          ref="inputRef"
        ></textarea>
        <button
          type="submit"
          class="send-button"
          :disabled="loading || !inputMessage.trim() || !sessionId"
          title="إرسال (Enter)"
        >
          <span v-if="!loading">📤</span>
          <span v-else class="spinner">⏳</span>
        </button>
      </form>
      <div v-if="!sessionId" class="input-hint">
        ⚠️ يرجى رفع ملف PDF أولاً لبدء المحادثة
      </div>
    </div>
  </div>
</template>

<script>
import MarkdownRenderer from './MarkdownRenderer.vue'

export default {
  name: 'ChatInterface',
  components: {
    MarkdownRenderer
  },
  props: {
    sessionId: {
      type: String,
      default: null
    },
    apiBaseUrl: {
      type: String,
      required: true
    },
    model: {
      type: String,
      default: ''
    }
  },
  data() {
    return {
      messages: [],
      inputMessage: '',
      loading: false,
      currentResponse: '',
      currentMessageIndex: null,
      suggestions: [
        'ما هي النقاط الرئيسية في هذه الوثيقة؟',
        'أنشئ ملخصاً شاملاً',
        'اشرح المفاهيم الأساسية',
        'ما هي المعلومات الأكثر أهمية؟'
      ],
      _es: null
    }
  },
  watch: {
    sessionId(newVal) {
      if (!newVal) {
        this.messages = []
        this.currentResponse = ''
      }
    }
  },
  methods: {
    async handleSubmit() {
      if (!this.inputMessage.trim() || this.loading || !this.sessionId) {
        return
      }

      const userMessage = this.inputMessage.trim()
      this.inputMessage = ''
      
      // إضافة رسالة المستخدم
      this.messages.push({
        role: 'user',
        content: userMessage,
        timestamp: Date.now()
      })

      // إضافة رسالة مساعد فارغة
      this.currentMessageIndex = this.messages.length
      this.messages.push({
        role: 'assistant',
        content: '',
        timestamp: Date.now()
      })

      this.loading = true
      this.currentResponse = ''

      try {
        const url = `${this.apiBaseUrl}/chat?session_id=${encodeURIComponent(this.sessionId)}&q=${encodeURIComponent(userMessage)}&model=${encodeURIComponent(this.model || '')}`
        const es = new EventSource(url)
        this._es = es

        es.onmessage = (event) => {
          if (!event.data) return
          this.currentResponse += event.data
          if (this.currentMessageIndex !== null) {
            this.messages[this.currentMessageIndex].content = this.currentResponse
          }
          this.$nextTick(() => {
            this.scrollToBottom()
          })
        }

        es.addEventListener('status', (event) => {
          if (event.data === 'DONE') {
            this.loading = false
            this._closeES()
            this.scrollToBottom()
          }
        })

        es.addEventListener('error', () => {
          this.loading = false
          if (this.currentMessageIndex !== null) {
            this.messages[this.currentMessageIndex].content = 
              this.currentResponse || '❌ حدث خطأ أثناء معالجة طلبك'
          }
          this._closeES()
        })
      } catch (error) {
        this.loading = false
        if (this.currentMessageIndex !== null) {
          this.messages[this.currentMessageIndex].content = 
            '❌ تعذر إرسال الرسالة. يرجى المحاولة مرة أخرى.'
        }
        console.error('Chat error:', error)
      }
    },
    sendMessage(message) {
      this.inputMessage = message
      this.handleSubmit()
    },
    formatTime(timestamp) {
      const date = new Date(timestamp)
      return date.toLocaleTimeString('ar-SA', { 
        hour: '2-digit', 
        minute: '2-digit' 
      })
    },
    scrollToBottom() {
      this.$nextTick(() => {
        const container = this.$refs.messagesContainer
        if (container) {
          container.scrollTop = container.scrollHeight
        }
      })
    },
    _closeES() {
      if (this._es) {
        this._es.close()
        this._es = null
      }
    },
    clearChat() {
      this.messages = []
      this.currentResponse = ''
      this._closeES()
    }
  },
  beforeUnmount() {
    this._closeES()
  }
}
</script>

<style scoped>
.chat-interface {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--surface);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.empty-chat {
  margin: auto;
  text-align: center;
  color: var(--text-soft);
  max-width: 500px;
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 16px;
}

.empty-chat h3 {
  margin: 0 0 12px;
  color: var(--text);
  font-size: 1.2rem;
}

.empty-chat p {
  margin: 0 0 24px;
  line-height: 1.6;
}

.suggestions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: center;
}

.suggestion-btn {
  background: var(--surface-alt);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 12px 20px;
  color: var(--text);
  cursor: pointer;
  transition: var(--transition);
  font-size: 0.9rem;
  width: 100%;
  max-width: 400px;
}

.suggestion-btn:hover {
  background: rgba(var(--accent-rgb), 0.1);
  border-color: rgba(var(--accent-rgb), 0.3);
  color: var(--accent);
}

.message {
  display: flex;
  gap: 12px;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: rgba(var(--accent-rgb), 0.1);
  display: grid;
  place-items: center;
  font-size: 1.2rem;
  flex-shrink: 0;
}

.message.user .message-avatar {
  background: rgba(var(--accent-rgb), 0.2);
}

.message-content {
  flex: 1;
  min-width: 0;
}

.message.user .message-content {
  text-align: right;
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  font-size: 0.75rem;
  color: var(--text-soft);
}

.message.user .message-header {
  flex-direction: row-reverse;
}

.message-role {
  font-weight: 600;
  color: var(--text);
}

.message-time {
  opacity: 0.7;
}

.message-body {
  background: var(--surface-alt);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 14px 18px;
  line-height: 1.7;
  word-wrap: break-word;
}

.message.user .message-body {
  background: rgba(var(--accent-rgb), 0.1);
  border-color: rgba(var(--accent-rgb), 0.2);
}

.message-body p {
  margin: 0;
}

.typing-indicator {
  display: flex;
  gap: 6px;
  padding: 8px 0;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-soft);
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.7;
  }
  30% {
    transform: translateY(-10px);
    opacity: 1;
  }
}

.chat-input-container {
  border-top: 1px solid var(--border);
  padding: 18px 24px;
  background: var(--surface-alt);
}

.chat-input-form {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.chat-input {
  flex: 1;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 12px 16px;
  font-family: inherit;
  font-size: 0.95rem;
  color: var(--text);
  resize: none;
  min-height: 48px;
  max-height: 120px;
  line-height: 1.6;
}

.chat-input:focus {
  outline: none;
  border-color: rgba(var(--accent-rgb), 0.5);
  box-shadow: 0 0 0 4px rgba(var(--accent-rgb), 0.1);
}

.chat-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.send-button {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  border: none;
  background: linear-gradient(140deg, #2563eb, #4338ca);
  color: white;
  cursor: pointer;
  display: grid;
  place-items: center;
  font-size: 1.2rem;
  transition: var(--transition);
  flex-shrink: 0;
}

.send-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.send-button:not(:disabled):hover {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
}

.spinner {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.input-hint {
  margin-top: 10px;
  font-size: 0.8rem;
  color: var(--text-soft);
  text-align: center;
}

@media (max-width: 720px) {
  .chat-messages {
    padding: 18px;
    gap: 16px;
  }

  .chat-input-container {
    padding: 14px 18px;
  }

  .message-avatar {
    width: 36px;
    height: 36px;
    font-size: 1rem;
  }

  .message-body {
    padding: 12px 14px;
    font-size: 0.9rem;
  }
}
</style>

