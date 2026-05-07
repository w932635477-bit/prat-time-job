// starting-point/static/js/app.js
// Main controller: view switching, user ID, event binding, stage transitions

var App = (function () {
  'use strict';

  var USER_ID_KEY = 'sp_user_id';
  var currentView = 'landing';
  var sessionReady = false;

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
        // Session creation failed — allow limited access
        sessionReady = true;
        if (callback) callback();
      });
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

    var messages = document.getElementById('chat-messages');
    if (!messages) return;

    // Send initial greeting to kick off Stage 0
    Chat.sendMessage(getUserId(), '你好，我想看看我的经验能值多少钱');
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
    // Delay slightly so user sees the "generating kit" message
    setTimeout(function () {
      showView('kit');
      Kit.loadKit(getUserId());
    }, 1500);
  }

  // ---- Init on DOM ready ----

  function init() {
    initLanding();

    // Create server session first, then check for existing conversation
    ensureSession(function () {
      checkExistingSession(getUserId());
    });
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
          // User has a kit, go directly to kit view
          showView('kit');
          Kit.renderKit = Kit.renderKit; // ensure loaded
          fetch('/api/kit/' + encodeURIComponent(userId))
            .then(function (r) { return r.json(); })
            .then(function (kit) {
              Kit.renderKit(kit);
            });
          return;
        }

        if (data.status === 'pending' || data.status === 'not_found') {
          // Check conversation state — user may be mid-conversation
          fetch('/api/state/' + encodeURIComponent(userId))
            .then(function (r) {
              if (!r.ok) return null;
              return r.json();
            })
            .then(function (state) {
              if (state && state.current_stage != null) {
                showView('chat');
                Chat.loadHistory(userId);
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
  };
})();

document.addEventListener('DOMContentLoaded', App.init);
