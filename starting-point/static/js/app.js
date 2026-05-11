// starting-point/static/js/app.js
// Main controller: view switching, user ID, event binding, stage transitions

var App = (function () {
  'use strict';

  var USER_ID_KEY = 'sp_user_id';
  var currentView = 'landing';
  var sessionReady = false;

  var STAGE_NAMES = ['经验评估', '产品包装', '启动套件'];
  var STAGE_DESCS = [
    '找到你经验里最值钱的部分',
    '把经验变成可以卖的产品',
    '拿到可以直接用的素材'
  ];
  var STAGE_TOTAL = STAGE_NAMES.length;

  // ---- Device detection ----

  function isWechatBrowser() {
    return /MicroMessenger/i.test(navigator.userAgent);
  }

  function isMobile() {
    return /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent);
  }

  // ---- WeChat JS SDK init ----

  function initWxConfig() {
    if (!isWechatBrowser() || typeof wx === 'undefined') return;
    fetch('/api/auth/wechat/jsapi-config?url=' + encodeURIComponent(location.href.split('#')[0]))
      .then(function (r) { return r.json(); })
      .then(function (config) {
        wx.config({
          debug: false,
          appId: config.appId,
          timestamp: config.timestamp,
          nonceStr: config.nonceStr,
          signature: config.signature,
          jsApiList: ['chooseWXPay']
        });
      })
      .catch(function () {});
  }

  // ---- User ID management ----

  function getUserId() {
    var id = localStorage.getItem(USER_ID_KEY);
    if (!id) {
      id = 'u_' + crypto.randomUUID();
      localStorage.setItem(USER_ID_KEY, id);
    }
    return id;
  }

  // ---- Session management ----

  function ensureSession(callback) {
    // If just returned from OAuth or QR login, the session cookie was set by the server.
    // Sync user_id from the server session rather than trusting localStorage.
    if (localStorage.getItem('sp_auth') === 'wechat') {
      localStorage.removeItem('sp_auth');
      fetch('/api/session', { method: 'GET' })
        .then(function (resp) { return resp.json(); })
        .then(function (data) {
          if (data.authenticated && data.user_id) {
            localStorage.setItem(USER_ID_KEY, data.user_id);
            sessionReady = true;
            if (callback) callback();
          } else {
            // No valid session cookie yet, create one for the logged-in user
            createSessionForUser(getUserId(), callback);
          }
        })
        .catch(function () {
          createSessionForUser(getUserId(), callback);
        });
      return;
    }

    // Check if existing session is valid
    fetch('/api/session', { method: 'GET' })
      .then(function (resp) { return resp.json(); })
      .then(function (data) {
        if (data.authenticated && data.user_id) {
          localStorage.setItem(USER_ID_KEY, data.user_id);
          sessionReady = true;
          if (callback) callback();
          return;
        }
        createAnonymousSession(callback);
      })
      .catch(function () {
        createAnonymousSession(callback);
      });
  }

  function createSessionForUser(userId, callback) {
    fetch('/api/session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId }),
    })
      .then(function (resp) { return resp.json(); })
      .then(function () {
        sessionReady = true;
        if (callback) callback();
      })
      .catch(function () {
        sessionReady = true;
        if (callback) callback();
      });
  }

  function createAnonymousSession(callback) {
    fetch('/api/session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: getUserId() }),
    })
      .then(function (resp) { return resp.json(); })
      .then(function () {
        sessionReady = true;
        if (callback) callback();
      })
      .catch(function () {
        sessionReady = true;
        if (callback) callback();
      });
  }

  // ---- View switching ----

  function showView(viewName) {
    var views = document.querySelectorAll('.view');
    views.forEach(function (v) {
      v.classList.remove('view--active');
    });

    var target = document.getElementById(viewName);
    if (target) {
      target.classList.add('view--active');
    }

    currentView = viewName;
  }

  // ---- Progress / Stage UI ----

  function updateProgress(stage, progress) {
    var fill = document.getElementById('stepBarFill');
    var desc = document.getElementById('stepDesc');
    var label = document.getElementById('stageLabel');
    if (!fill) return;

    var pct = Math.min(100, Math.max(0, (stage + (progress || 0)) / STAGE_TOTAL * 100));
    fill.style.width = pct + '%';
    if (label) label.textContent = STAGE_NAMES[stage] || '';
    if (desc) desc.textContent = STAGE_DESCS[stage] || '';

    for (var i = 0; i < STAGE_TOTAL; i++) {
      var stepEl = document.getElementById('step' + i);
      if (!stepEl) continue;
      stepEl.className = 'step-bar__step';
      if (i < stage) {
        stepEl.classList.add('step-bar__step--completed');
      } else if (i === stage) {
        stepEl.classList.add('step-bar__step--active');
      } else {
        stepEl.classList.add('step-bar__step--future');
      }
    }
  }

  function hideRoadmap() {
    var stepBar = document.getElementById('stepBar');
    if (stepBar) stepBar.style.display = 'none';
  }

  // ---- Init landing ----

  function initLanding() {
    var startBtn = document.getElementById('startBtn');
    if (startBtn) {
      startBtn.addEventListener('click', function () {
        startChat();
      });
    }
  }

  // ---- Start chat ----

  function startChat() {
    showView('chat');
    initChatInput();
    updateProgress(0, 0);

    var messages = document.getElementById('chat-messages');
    if (!messages) return;

    Chat.sendMessage(getUserId(), '你好，我想看看我的经验能值多少钱');
  }

  // ---- Resume chat ----

  function resumeChat(stage) {
    showView('chat');
    initChatInput();
    updateProgress(stage, 0);
  }

  // ---- Init chat input ----

  function initChatInput() {
    var input = document.getElementById('chatInput');
    var sendBtn = document.getElementById('sendBtn');

    if (!input || !sendBtn) return;

    input.addEventListener('input', function () {
      sendBtn.classList.toggle(
        'input-bar__send--active',
        input.value.trim().length > 0
      );
    });

    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && input.value.trim()) {
        var text = input.value.trim();
        input.value = '';
        sendBtn.classList.remove('input-bar__send--active');
        Chat.sendMessage(getUserId(), text);
      }
    });

    sendBtn.addEventListener('click', function () {
      if (input.value.trim()) {
        var text = input.value.trim();
        input.value = '';
        sendBtn.classList.remove('input-bar__send--active');
        Chat.sendMessage(getUserId(), text);
      }
    });
  }

  // ---- Stage 1 complete -> switch to kit view ----

  function onStageOneComplete(data) {
    setTimeout(function () {
      showView('kit');
      Kit.loadKit(getUserId());
    }, 1500);
  }

  // ---- Init on DOM ready ----

  function init() {
    initLanding();

    ensureSession(function () {
      checkExistingSession(getUserId());
    });

    initWxConfig();
  }

  function checkExistingSession(userId) {
    fetch('/api/kit-status/' + encodeURIComponent(userId))
      .then(function (resp) {
        if (!resp.ok) return null;
        return resp.json();
      })
      .then(function (data) {
        if (!data) return;

        if (data.status === 'completed') {
          showView('kit');
          updateProgress(2, 1);
          Kit.renderKit = Kit.renderKit;
          fetch('/api/kit/' + encodeURIComponent(userId))
            .then(function (r) { return r.json(); })
            .then(function (kit) {
              Kit.renderKit(kit);
            });
          return;
        }

        if (data.status === 'pending' || data.status === 'not_found') {
          fetch('/api/state/' + encodeURIComponent(userId))
            .then(function (r) {
              if (!r.ok) return null;
              return r.json();
            })
            .then(function (state) {
              if (state && state.current_stage != null) {
                var stage = state.current_stage || 0;
                resumeChat(stage);
                Chat.loadHistory(userId);

                if (stage >= 2 && state.is_anonymous) {
                  var sd = state.stage_data || {};
                  var kps = sd.knowledge_points || [];
                  var pkg = sd.product_package || null;
                  Chat.renderResumeCards(kps, pkg);
                  Chat.showLoginCard();
                } else if (stage >= 2 && !state.is_anonymous) {
                  var sd2 = state.stage_data || {};
                  var pkg2 = sd2.product_package || null;
                  if (pkg2) Chat.renderResumeCards([], pkg2);
                  Chat.showPaywallIfNeeded(userId);
                }
              }
            })
            .catch(function () {});
        }
      })
      .catch(function () {
        // Ignore errors, stay on landing
      });
  }

  // ---- Public API ----

  return {
    init: init,
    onStageOneComplete: onStageOneComplete,
    getUserId: getUserId,
    updateProgress: updateProgress,
    hideRoadmap: hideRoadmap,
    isWechatBrowser: isWechatBrowser,
    isMobile: isMobile,
  };
})();

document.addEventListener('DOMContentLoaded', App.init);
