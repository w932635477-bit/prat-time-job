// starting-point/static/js/chat.js
// Chat logic: send messages, render bubbles, handle API responses

var Chat = (function () {
  'use strict';

  var sending = false;

  // ---- DOM helpers ----

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function scrollToBottom() {
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
  }

  function getMessagesContainer() {
    return document.getElementById('chat-messages');
  }

  // ---- Render functions ----

  function renderBubbleAi(text) {
    var row = document.createElement('div');
    row.className = 'chat-row chat-row--ai fade-in';
    var bubble = document.createElement('div');
    bubble.className = 'bubble-ai';
    bubble.textContent = text;
    bubble.setAttribute('role', 'status');
    bubble.setAttribute('aria-live', 'polite');
    row.appendChild(bubble);
    return row;
  }

  function renderBubbleUser(text) {
    var row = document.createElement('div');
    row.className = 'chat-row chat-row--user fade-in';
    var bubble = document.createElement('div');
    bubble.className = 'bubble-user-text';
    bubble.textContent = text;
    row.appendChild(bubble);
    return row;
  }

  function renderLoading() {
    var row = document.createElement('div');
    row.className = 'chat-row chat-row--loading';
    row.id = 'loading-indicator';
    row.innerHTML =
      '<div class="bubble-ai loading-dots"><span></span><span></span><span></span></div>';
    return row;
  }

  function removeLoading() {
    var el = document.getElementById('loading-indicator');
    if (el) el.remove();
  }

  // ---- Stage 0 result: knowledge points ----

  function renderKnowledgePoints(knowledgePoints) {
    var container = document.createElement('div');
    container.className = 'fade-in';

    var transition = document.createElement('div');
    transition.className = 'stage-transition';
    transition.innerHTML =
      '<div class="stage-transition__label">评估完成</div>' +
      '<div class="stage-transition__title">你的经验比你想的值钱</div>';
    container.appendChild(transition);

    knowledgePoints.forEach(function (kp) {
      var card = document.createElement('div');
      card.className = 'kp-card fade-in';

      var typeLabels = {
        price_transparency: '价格透明',
        pitfall_guide: '避坑指南',
        channel_info: '渠道信息',
        industry_insider: '业内人视角',
      };

      card.innerHTML =
        '<div class="kp-card__type">' +
          escapeHtml(typeLabels[kp.knowledge_type] || kp.knowledge_type) +
        '</div>' +
        '<div class="kp-card__desc">' + escapeHtml(kp.description) + '</div>' +
        '<div class="kp-card__meta">' +
          '<strong>谁会买:</strong> ' + escapeHtml(kp.target_buyer) +
        '</div>' +
        '<div class="kp-card__meta">' +
          '<strong>估算价值:</strong> ' + escapeHtml(kp.estimated_value) +
        '</div>';

      container.appendChild(card);
    });

    return container;
  }

  // ---- Stage 1 result: product package ----

  function renderLoginCard() {
    var container = document.createElement('div');
    container.className = 'login-card fade-in';

    var isWechat = /MicroMessenger/i.test(navigator.userAgent);
    var pageUrl = window.location.href.split('?')[0];

    if (isWechat) {
      container.innerHTML =
        '<div class="login-card__icon">' +
          '<svg viewBox="0 0 32 32" width="40" height="40" fill="none" stroke="currentColor" stroke-width="1.5">' +
            '<path d="M16 8a4 4 0 100 8 4 4 0 000-8z"/>' +
            '<path d="M4 28c0-6.627 5.373-12 12-12s12 5.373 12 12"/>' +
          '</svg>' +
        '</div>' +
        '<div class="login-card__title">登录以生成启动套件</div>' +
        '<div class="login-card__desc">你的产品方案已就绪，微信登录后即可生成完整的启动套件。</div>' +
        '<a href="/api/auth/wechat/login" class="login-card__btn">微信登录</a>';
    } else {
      container.innerHTML =
        '<div class="login-card__title">登录以生成启动套件</div>' +
        '<div class="login-card__desc">你的产品方案已就绪。请用微信扫描下方二维码打开此页面，完成登录。</div>' +
        '<div class="login-card__qr">' +
          '<img src="https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=' + encodeURIComponent(pageUrl) + '" alt="扫码打开" width="180" height="180" />' +
        '</div>' +
        '<div class="login-card__hint">长按或扫描二维码，在微信中打开</div>';
    }

    if (typeof Chat !== 'undefined' && Chat.disableInput) {
      Chat.disableInput(true);
    }

    return container;
  }

  function renderNextStepCard(nextStep) {
    var container = document.createElement('div');
    container.className = 'next-step-card fade-in';

    container.innerHTML =
      '<div class="next-step-card__title">' + escapeHtml(nextStep.title) + '</div>' +
      '<div class="next-step-card__desc">' + escapeHtml(nextStep.description) + '</div>' +
      '<button class="next-step-card__btn">开始这一步</button>';

    var btn = container.querySelector('.next-step-card__btn');
    btn.addEventListener('click', function () {
      btn.disabled = true;
      btn.textContent = '正在开始...';
      var userId = (typeof App !== 'undefined' && App.getUserId) ? App.getUserId() : '';
      if (userId && nextStep.auto_prompt) {
        sendMessage(userId, nextStep.auto_prompt);
      }
    });

    return container;
  }

  function renderProductPackage(pkg) {
    var container = document.createElement('div');
    container.className = 'fade-in';

    var card = document.createElement('div');
    card.className = 'output-card';

    var serviceLabels = {
      consultation: '咨询服务',
      content: '内容产品',
      service: '服务交付',
    };

    card.innerHTML =
      '<div class="output-card__title">' + escapeHtml(pkg.product_name || '你的产品') + '</div>' +
      '<div class="output-card__subtitle">' + escapeHtml(pkg.one_liner || '') + '</div>' +
      '<div class="output-card__field">' +
        '<div class="output-card__label">目标客户</div>' +
        '<div class="output-card__value">' + escapeHtml(pkg.target_buyer || '') + '</div>' +
      '</div>' +
      '<div class="output-card__field">' +
        '<div class="output-card__label">服务形式</div>' +
        '<div class="output-card__value">' +
          escapeHtml(serviceLabels[pkg.service_type] || pkg.service_type || '') +
        '</div>' +
      '</div>' +
      '<div class="output-card__field">' +
        '<div class="output-card__label">建议定价</div>' +
        '<div class="output-card__value">' +
          (pkg.price_range
            ? pkg.price_range.min + ' - ' + pkg.price_range.max + ' 元'
            : '待定') +
        '</div>' +
      '</div>' +
      '<div class="output-card__field">' +
        '<div class="output-card__label">交付方式</div>' +
        '<div class="output-card__value">' + escapeHtml(pkg.delivery_method || '') + '</div>' +
      '</div>';

    container.appendChild(card);
    return container;
  }

  // ---- API call ----

  function callChatApi(userId, message) {
    return fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, message: message }),
    }).then(function (resp) {
      if (!resp.ok) {
        throw new Error('API error: ' + resp.status);
      }
      return resp.json();
    });
  }

  // ---- Send message ----

  function sendMessage(userId, text) {
    if (sending || !text.trim()) return;
    sending = true;
    disableInput(true);

    var messages = getMessagesContainer();
    messages.appendChild(renderBubbleUser(text.trim()));
    scrollToBottom();

    var loadingEl = renderLoading();
    messages.appendChild(loadingEl);
    scrollToBottom();

    callChatApi(userId, text.trim())
      .then(function (data) {
        removeLoading();
        handleResponse(data);
      })
      .catch(function (err) {
        removeLoading();
        messages.appendChild(renderBubbleAi('网络出了点问题，请重试。'));
        console.error('Chat API error:', err);
      })
      .finally(function () {
        sending = false;
        disableInput(false);
      });
  }

  // ---- Handle response ----

  function handleResponse(data) {
    var messages = getMessagesContainer();

    // Update step bar and stage label
    if (typeof App !== 'undefined' && App.updateProgress) {
      var stage = (typeof data.stage === 'number') ? data.stage : 0;
      var progress = (typeof data.progress === 'number') ? data.progress : 0;
      App.updateProgress(stage, progress);
    }

    // Render the AI message text
    if (data.message) {
      messages.appendChild(renderBubbleAi(data.message));
    }

    // Stage 0 complete: show knowledge points + next step card
    if (data.is_complete && data.stage === 1 && data.stage_data) {
      var kps = data.stage_data.knowledge_points || [];
      if (kps.length > 0) {
        messages.appendChild(renderKnowledgePoints(kps));
      }

      if (data.next_step) {
        messages.appendChild(renderNextStepCard(data.next_step));
      }

      scrollToBottom();
      return;
    }

    // Stage 1 complete: product packaged + login card or paywall
    if (data.is_complete && data.stage >= 2) {
      var pkg =
        (data.stage_data && data.stage_data.product_package) || null;
      if (pkg) {
        messages.appendChild(renderProductPackage(pkg));
      }

      if (data.is_anonymous) {
        messages.appendChild(renderLoginCard());
      } else {
        // Logged in user: show paywall or complete
        if (typeof Paywall !== 'undefined' && Paywall.checkAndShow) {
          Paywall.checkAndShow(App.getUserId(), data);
        } else if (typeof App !== 'undefined' && App.onStageOneComplete) {
          App.onStageOneComplete(data);
        }
      }
      scrollToBottom();
      return;
    }

    scrollToBottom();
  }

  // ---- Input control ----

  function disableInput(disabled) {
    var input = document.getElementById('chatInput');
    var sendBtn = document.getElementById('sendBtn');
    if (input) input.disabled = disabled;
    if (sendBtn) sendBtn.disabled = disabled;
    if (!disabled && input) input.focus();
  }

  // ---- Load chat history for session resume ----

  function loadHistory(userId) {
    fetch('/api/messages/' + encodeURIComponent(userId))
      .then(function (resp) {
        if (!resp.ok) return null;
        return resp.json();
      })
      .then(function (data) {
        if (!data || !data.messages) return;
        var container = getMessagesContainer();
        if (!container) return;

        data.messages.forEach(function (msg) {
          if (msg.role === 'user') {
            container.appendChild(renderBubbleUser(msg.content));
          } else if (msg.role === 'assistant') {
            container.appendChild(renderBubbleAi(msg.content));
          }
        });
        scrollToBottom();
      })
      .catch(function () {});
  }

  // ---- Session resume helpers ----

  function renderResumeCards(knowledgePoints, productPackage) {
    var messages = getMessagesContainer();
    if (!messages) return;

    // Stage transition header
    var transition = document.createElement('div');
    transition.className = 'stage-transition';
    transition.innerHTML =
      '<div class="stage-transition__label">评估完成</div>' +
      '<div class="stage-transition__title">你的经验比你想的值钱</div>';
    messages.appendChild(transition);

    if (knowledgePoints && knowledgePoints.length > 0) {
      knowledgePoints.forEach(function (kp) {
        var card = document.createElement('div');
        card.className = 'kp-card';
        var typeLabels = {
          price_transparency: '价格透明',
          pitfall_guide: '避坑指南',
          channel_info: '渠道信息',
          industry_insider: '业内人视角',
        };
        card.innerHTML =
          '<div class="kp-card__type">' +
            escapeHtml(typeLabels[kp.knowledge_type] || kp.knowledge_type) +
          '</div>' +
          '<div class="kp-card__desc">' + escapeHtml(kp.description) + '</div>' +
          '<div class="kp-card__meta"><strong>谁会买:</strong> ' + escapeHtml(kp.target_buyer) + '</div>' +
          '<div class="kp-card__meta"><strong>估算价值:</strong> ' + escapeHtml(kp.estimated_value) + '</div>';
        messages.appendChild(card);
      });
    }

    if (productPackage) {
      messages.appendChild(renderProductPackage(productPackage));
    }
  }

  function showLoginCard() {
    var messages = getMessagesContainer();
    if (!messages) return;
    messages.appendChild(renderLoginCard());
    disableInput(true);
    scrollToBottom();
  }

  function showPaywallIfNeeded(userId) {
    var tier = 'free';
    try {
      var userInfo = localStorage.getItem('sp_user_info');
      if (userInfo) {
        var parsed = JSON.parse(userInfo);
        tier = parsed.tier || 'free';
      }
    } catch (e) { /* ignore */ }

    if (tier === 'free') {
      if (typeof Paywall !== 'undefined' && Paywall.checkAndShow) {
        Paywall.checkAndShow(userId, {});
      }
    }
  }

  // ---- Public API ----

  return {
    sendMessage: sendMessage,
    handleResponse: handleResponse,
    renderBubbleAi: renderBubbleAi,
    disableInput: disableInput,
    loadHistory: loadHistory,
    showLoginCard: showLoginCard,
    showPaywallIfNeeded: showPaywallIfNeeded,
    renderResumeCards: renderResumeCards,
  };
})();
