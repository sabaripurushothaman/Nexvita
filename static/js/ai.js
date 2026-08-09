/* ============================================================
   NexVita — ai.js
   AI Chatbot: real-time chat, markdown rendering, typing indicator,
   suggestion chips, copy buttons, clear chat, auto-scroll.
   Requires: marked.js (loaded in template)
   ============================================================ */

'use strict';

let chatEndpoint   = '';
let clearEndpoint  = '';
let userInitial    = 'U';
let isAtBottom     = true;
let _isRequesting  = false;  // lock: prevents duplicate simultaneous requests

/* ── Initialise ─────────────────────────────────────────────── */
function initChatbot(endpoint, clearEp, initial) {
  chatEndpoint  = endpoint;
  clearEndpoint = clearEp;
  userInitial   = initial;

  const form    = document.getElementById('chatForm');
  const input   = document.getElementById('chatInput');
  const msgs    = document.getElementById('chatMessages');
  const sendBtn = document.getElementById('sendBtn');

  if (!form || !input || !msgs) return;

  scrollToBottom();
  renderHistoryMarkdown();

  // Auto-resize textarea
  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 160) + 'px';
    updateCharCount(input);
  });

  // Send on Enter (Shift+Enter = newline)
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      form.requestSubmit();
    }
  });

  // Detect if user scrolled away from bottom
  msgs.addEventListener('scroll', () => {
    const threshold = 80;
    isAtBottom = msgs.scrollHeight - msgs.scrollTop - msgs.clientHeight < threshold;
  });

  // Form submit
  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    if (_isRequesting) return;  // lock: ignore if a request is already in-flight
    const msg = input.value.trim();
    if (!msg) return;

    // Set in-flight lock and disable controls
    _isRequesting = true;
    sendBtn.disabled = true;
    input.disabled = true;
    sendBtn.style.opacity = '0.6';

    input.value = '';
    input.style.height = 'auto';
    updateCharCount(input);

    appendMessage('user', msg, new Date().toISOString());
    showTyping();
    if (isAtBottom) scrollToBottom();

    // Hide suggestions after first real send
    const sugg = document.getElementById('chatSuggestions');
    if (sugg) sugg.style.display = 'none';

    try {
      const res  = await fetch(chatEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify({ message: msg }),
      });
      const data = await res.json();
      hideTyping();

      if (res.ok && data.ai_response) {
        appendMessage('ai', data.ai_response, data.timestamp);
      } else {
        appendMessage('ai', data.error
          ? `## ⚠️ Error\n${data.error}`
          : '## ⚠️ Unexpected Error\nPlease try again.', new Date().toISOString());
      }
    } catch (err) {
      hideTyping();
      appendMessage('ai',
        '## ⚠️ Connection Error\nCould not reach the AI service. Please check your connection and try again.',
        new Date().toISOString()
      );
    } finally {
      // Always release lock and re-enable controls
      _isRequesting = false;
      sendBtn.disabled = false;
      input.disabled = false;
      sendBtn.style.opacity = '';
      input.focus();
    }

    if (isAtBottom) scrollToBottom();
  });
}


/* ── Append message bubble ───────────────────────────────────── */
function appendMessage(type, content, timestamp) {
  const msgs   = document.getElementById('chatMessages');
  const typing = document.getElementById('typingIndicator');

  const div = document.createElement('div');
  div.className = `chat-msg ${type}`;

  const timeStr = formatTime(timestamp);
  const rendered = type === 'ai' ? renderMarkdown(content) : escapeHtml(content);

  if (type === 'ai') {
    div.innerHTML = `
      <div class="chat-msg__avatar">
        <svg data-lucide="bot" style="width:18px;height:18px;color:white;"></svg>
      </div>
      <div class="chat-msg__content">
        <div class="chat-msg__bubble markdown-body">${rendered}</div>
        <div class="chat-msg__footer">
          <span class="chat-msg__time">${timeStr}</span>
          <button class="copy-btn" title="Copy response" onclick="copyMessage(this)">
            <svg data-lucide="copy" style="width:12px;height:12px;"></svg>
            Copy
          </button>
        </div>
      </div>
    `;
  } else {
    div.innerHTML = `
      <div class="chat-msg__content">
        <div class="chat-msg__bubble">${rendered}</div>
        <div class="chat-msg__footer">
          <span class="chat-msg__time">${timeStr}</span>
        </div>
      </div>
      <div class="chat-msg__avatar user-avatar">${userInitial}</div>
    `;
  }

  if (typing) msgs.insertBefore(div, typing);
  else msgs.appendChild(div);

  if (window.lucide) lucide.createIcons({ nodes: [div] });
  if (window.hljs) div.querySelectorAll('pre code').forEach(b => hljs.highlightElement(b));
}


/* ── Render Markdown on existing history messages ────────────── */
function renderHistoryMarkdown() {
  document.querySelectorAll('.chat-msg.ai .chat-msg__bubble.markdown-body').forEach(el => {
    const raw = el.getAttribute('data-raw');
    if (raw) {
      el.innerHTML = renderMarkdown(raw);
      if (window.hljs) el.querySelectorAll('pre code').forEach(b => hljs.highlightElement(b));
    }
  });
}


/* ── Markdown renderer ───────────────────────────────────────── */
function renderMarkdown(text) {
  if (!window.marked) return escapeHtml(text).replace(/\n/g, '<br>');
  marked.setOptions({
    breaks: true,
    gfm: true,
    headerIds: false,
    mangle: false,
  });
  return marked.parse(text);
}


/* ── Typing indicator ────────────────────────────────────────── */
function showTyping() {
  const t = document.getElementById('typingIndicator');
  if (t) { t.style.display = 'flex'; t.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }
}
function hideTyping() {
  const t = document.getElementById('typingIndicator');
  if (t) t.style.display = 'none';
}


/* ── Auto-scroll ─────────────────────────────────────────────── */
function scrollToBottom() {
  const msgs = document.getElementById('chatMessages');
  if (msgs) {
    msgs.scrollTo({ top: msgs.scrollHeight, behavior: 'smooth' });
    isAtBottom = true;
  }
}


/* ── Suggestion chips ────────────────────────────────────────── */
function sendSuggestion(btn) {
  if (_isRequesting) return;  // ignore while a request is in flight
  const input = document.getElementById('chatInput');
  if (input) {
    input.value = btn.textContent.trim();
    input.dispatchEvent(new Event('input'));
    document.getElementById('chatForm').requestSubmit();
  }
}
window.sendSuggestion = sendSuggestion;


/* ── Copy message content ────────────────────────────────────── */
function copyMessage(btn) {
  const bubble = btn.closest('.chat-msg__content').querySelector('.chat-msg__bubble');
  if (!bubble) return;
  const text = bubble.innerText || bubble.textContent;
  navigator.clipboard.writeText(text).then(() => {
    const orig = btn.innerHTML;
    btn.innerHTML = '<svg data-lucide="check" style="width:12px;height:12px;"></svg> Copied!';
    if (window.lucide) lucide.createIcons({ nodes: [btn] });
    setTimeout(() => {
      btn.innerHTML = orig;
      if (window.lucide) lucide.createIcons({ nodes: [btn] });
    }, 2000);
  }).catch(() => {
    showToast('Could not copy. Please select and copy manually.', 'warning');
  });
}
window.copyMessage = copyMessage;


/* ── Clear chat ──────────────────────────────────────────────── */
function clearChat() {
  if (!confirm('Clear all chat history? This cannot be undone.')) return;
  fetch(clearEndpoint, { method: 'POST' })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        // Remove all non-welcome, non-typing messages
        const msgs = document.getElementById('chatMessages');
        const toRemove = msgs.querySelectorAll('.chat-msg:not(#typingIndicator):not(.welcome-msg)');
        toRemove.forEach(el => {
          el.style.transition = 'opacity 0.2s';
          el.style.opacity = '0';
          setTimeout(() => el.remove(), 200);
        });
        // Restore suggestions
        const sugg = document.getElementById('chatSuggestions');
        if (sugg) { sugg.style.display = ''; sugg.style.opacity = '0'; setTimeout(() => { sugg.style.transition = 'opacity 0.3s'; sugg.style.opacity = '1'; }, 300); }
        showToast('Chat history cleared.', 'success');
      }
    })
    .catch(() => showToast('Could not clear chat. Please try again.', 'danger'));
}
window.clearChat = clearChat;


/* ── Character counter ───────────────────────────────────────── */
function updateCharCount(input) {
  const counter = document.getElementById('charCounter');
  if (!counter) return;
  const len = input.value.length;
  const max = 2000;
  counter.textContent = `${len}/${max}`;
  counter.style.color = len > 1800 ? 'var(--danger)' : len > 1500 ? 'var(--warning)' : 'var(--text-light)';
}


/* ── Toast notifications ─────────────────────────────────────── */
function showToast(msg, type = 'info') {
  let container = document.querySelector('.ai-toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'ai-toast-container';
    container.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:9999;display:flex;flex-direction:column;gap:8px;';
    document.body.appendChild(container);
  }
  const colors = { success: '#10B981', danger: '#EF4444', info: '#3B82F6', warning: '#F59E0B' };
  const toast = document.createElement('div');
  toast.style.cssText = `background:${colors[type]};color:white;padding:10px 18px;border-radius:10px;font-size:14px;font-weight:600;box-shadow:0 4px 16px rgba(0,0,0,.2);animation:slideInRight .3s ease;max-width:300px;`;
  toast.textContent = msg;
  container.appendChild(toast);
  setTimeout(() => { toast.style.opacity = '0'; toast.style.transition = 'opacity .3s'; setTimeout(() => toast.remove(), 300); }, 3000);
}


/* ── Helpers ─────────────────────────────────────────────────── */
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function formatTime(iso) {
  if (!iso) return 'now';
  try {
    return new Date(iso).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  } catch { return 'now'; }
}
