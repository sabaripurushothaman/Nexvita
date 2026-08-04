/* ============================================================
   NexVita – ai.js
   AI Chatbot: real-time chat, typing indicator, suggestions
   ============================================================ */

'use strict';

let chatEndpoint = '';
let userInitial  = 'U';

function initChatbot(endpoint, initial) {
  chatEndpoint = endpoint;
  userInitial  = initial;

  const form  = document.getElementById('chatForm');
  const input = document.getElementById('chatInput');
  const msgs  = document.getElementById('chatMessages');

  if (!form || !input || !msgs) return;

  // Scroll to bottom on load
  scrollToBottom();

  form.addEventListener('submit', async function(e) {
    e.preventDefault();
    const msg = input.value.trim();
    if (!msg) return;

    // Clear input immediately
    input.value = '';

    // Append user bubble
    appendMessage('user', msg, 'now');

    // Show typing indicator
    showTyping();
    scrollToBottom();

    try {
      const res = await fetch(chatEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({ message: msg }),
      });

      const data = await res.json();
      hideTyping();

      if (data.ai_response) {
        appendMessage('ai', data.ai_response, formatTime(data.timestamp));
      } else if (data.error) {
        appendMessage('ai', '⚠️ ' + data.error, 'now');
      }
    } catch (err) {
      hideTyping();
      appendMessage('ai', '⚠️ Sorry, I could not connect. Please try again.', 'now');
    }

    scrollToBottom();

    // Hide suggestions after first message
    const sugg = document.getElementById('chatSuggestions');
    if (sugg) sugg.style.display = 'none';
  });
}

function appendMessage(type, content, time) {
  const msgs = document.getElementById('chatMessages');
  const typing = document.getElementById('typingIndicator');

  const div = document.createElement('div');
  div.className = `chat-msg ${type}`;

  if (type === 'ai') {
    div.innerHTML = `
      <div class="chat-msg__avatar">
        <svg data-lucide="bot" style="width:18px;height:18px;color:white;"></svg>
      </div>
      <div class="chat-msg__bubble">${escapeHtml(content)}</div>
      <div class="chat-msg__time">${time}</div>
    `;
  } else {
    div.innerHTML = `
      <div class="chat-msg__bubble">${escapeHtml(content)}</div>
      <div class="chat-msg__time">${time}</div>
      <div class="chat-msg__avatar user-avatar">${userInitial}</div>
    `;
  }

  // Insert before typing indicator
  if (typing) msgs.insertBefore(div, typing);
  else msgs.appendChild(div);

  if (window.lucide) lucide.createIcons({ nodes: [div] });
}

function showTyping() {
  const t = document.getElementById('typingIndicator');
  if (t) t.style.display = 'flex';
}

function hideTyping() {
  const t = document.getElementById('typingIndicator');
  if (t) t.style.display = 'none';
}

function scrollToBottom() {
  const msgs = document.getElementById('chatMessages');
  if (msgs) msgs.scrollTop = msgs.scrollHeight;
}

function sendSuggestion(btn) {
  const input = document.getElementById('chatInput');
  if (input) {
    input.value = btn.textContent;
    document.getElementById('chatForm').requestSubmit();
  }
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/\n/g, '<br>');
}

function formatTime(iso) {
  if (!iso) return 'now';
  try {
    return new Date(iso).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  } catch { return 'now'; }
}
