// starting-point/static/js/paywall.js
// Paywall gate: shows pricing cards after Stage 1, triggers WeChat payment

var Paywall = (function () {
  'use strict';

  var PAYWALL_SHOWN_KEY = 'sp_paywall_dismissed';

  // ---- Check if user needs to pay ----

  function checkAndShow(userId, stageData) {
    // If user already dismissed this session, skip
    if (sessionStorage.getItem(PAYWALL_SHOWN_KEY)) {
      if (typeof App !== 'undefined' && App.onStageOneComplete) {
        App.onStageOneComplete(stageData);
      }
      return;
    }

    // Fetch user info to check tier
    fetch('/api/state/' + encodeURIComponent(userId))
      .then(function (r) { return r.json(); })
      .then(function () {
        // Check tier from localStorage (set by auth flow) or assume free
        var tier = getUserTier();
        if (tier === 'standard' || tier === 'human') {
          // Paid user, proceed to kit
          if (typeof App !== 'undefined' && App.onStageOneComplete) {
            App.onStageOneComplete(stageData);
          }
        } else {
          // Free user, show paywall
          showPaywall(userId);
        }
      })
      .catch(function () {
        showPaywall(userId);
      });
  }

  function getUserTier() {
    try {
      var userInfo = localStorage.getItem('sp_user_info');
      if (userInfo) {
        var parsed = JSON.parse(userInfo);
        return parsed.tier || 'free';
      }
    } catch (e) { /* ignore */ }
    return 'free';
  }

  // ---- Render paywall ----

  function showPaywall(userId) {
    var messages = document.getElementById('chat-messages');
    if (!messages) return;

    // Disable input while paywall is visible
    if (typeof Chat !== 'undefined' && Chat.disableInput) {
      Chat.disableInput(true);
    }

    var paywall = document.createElement('div');
    paywall.className = 'paywall fade-in';
    paywall.id = 'paywall-container';

    paywall.innerHTML =
      '<div class="paywall__title">解锁你的完整方案</div>' +
      '<div class="paywall__subtitle">免费体验已结束，选择方案继续</div>' +
      '<div class="pricing-grid">' +
        '<div class="pricing-card pricing-card--popular" id="pay-standard" data-tier="standard">' +
          '<div class="pricing-card__name">完整方案包</div>' +
          '<div class="pricing-card__price">¥29 <span>/ 60天</span></div>' +
          '<div class="pricing-card__desc">全部 6 阶段对话 + AI 生成的启动套件</div>' +
        '</div>' +
        '<div class="pricing-card" id="pay-human" data-tier="human">' +
          '<div class="pricing-card__name">真人教练加持</div>' +
          '<div class="pricing-card__price">¥199 <span>/ 60天</span></div>' +
          '<div class="pricing-card__desc">完整方案包 + 创始人 1 对 1 微信辅导</div>' +
        '</div>' +
      '</div>' +
      '<div id="paywall-status" style="text-align:center;margin-top:16px;color:var(--text-secondary);font-size:0.85rem;display:none;"></div>' +
      '<div id="paywall-qr" style="text-align:center;margin-top:16px;display:none;"></div>';

    messages.appendChild(paywall);
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });

    // Bind click handlers
    document.getElementById('pay-standard').addEventListener('click', function () {
      initiatePayment(userId, 'standard');
    });
    document.getElementById('pay-human').addEventListener('click', function () {
      initiatePayment(userId, 'human');
    });
  }

  // ---- Payment flow ----

  function initiatePayment(userId, tier) {
    var statusEl = document.getElementById('paywall-status');
    if (statusEl) {
      statusEl.style.display = 'block';
      statusEl.textContent = '正在创建订单...';
    }

    // Disable cards
    var cards = document.querySelectorAll('.pricing-card');
    cards.forEach(function (c) { c.style.pointerEvents = 'none'; c.style.opacity = '0.6'; });

    fetch('/api/payments/create?tier=' + encodeURIComponent(tier), {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
    })
      .then(function (resp) {
        if (!resp.ok) throw new Error('Order creation failed: ' + resp.status);
        return resp.json();
      })
      .then(function (data) {
        var prepay = data.prepay;
        if (!prepay || !prepay.success) {
          throw new Error(prepay ? prepay.error : 'Prepay failed');
        }

        if (prepay.trade_type === 'JSAPI' && typeof wx !== 'undefined' && wx.chooseWXPay) {
          // WeChat browser: JSAPI payment
          if (statusEl) statusEl.textContent = '正在调起微信支付...';
          callWechatPay(prepay, data.order_id, userId);
        } else if (prepay.trade_type === 'MWEB') {
          // Mobile non-WeChat browser: H5 payment
          if (statusEl) statusEl.textContent = '正在跳转微信支付...';
          var redirectUrl = encodeURIComponent(location.href);
          window.location.href = prepay.mweb_url + '&redirect_url=' + redirectUrl;
        } else if (prepay.trade_type === 'NATIVE') {
          // Desktop: show payment QR code
          if (statusEl) statusEl.textContent = '请用微信扫码支付';
          showPaymentQrCode(prepay.code_url, data.order_id, userId);
        } else {
          if (statusEl) statusEl.textContent = '请在微信中打开此页面完成支付';
          cards.forEach(function (c) { c.style.pointerEvents = ''; c.style.opacity = ''; });
        }
      })
      .catch(function (err) {
        console.error('Payment error:', err);
        if (statusEl) statusEl.textContent = '支付出错: ' + err.message;
        cards.forEach(function (c) { c.style.pointerEvents = ''; c.style.opacity = ''; });
      });
  }

  function callWechatPay(prepay, orderId, userId) {
    wx.chooseWXPay({
      timestamp: String(prepay.timeStamp || prepay.timestamp),
      nonceStr: prepay.nonceStr,
      package: prepay.package,
      signType: prepay.signType || 'MD5',
      paySign: prepay.paySign,
      success: function () {
        pollPaymentStatus(orderId, userId);
      },
      cancel: function () {
        var statusEl = document.getElementById('paywall-status');
        if (statusEl) statusEl.textContent = '支付已取消';
        var cards = document.querySelectorAll('.pricing-card');
        cards.forEach(function (c) { c.style.pointerEvents = ''; c.style.opacity = ''; });
      },
      fail: function (res) {
        var statusEl = document.getElementById('paywall-status');
        if (statusEl) statusEl.textContent = '支付失败，请重试';
        console.error('WeChat pay error:', res);
        var cards = document.querySelectorAll('.pricing-card');
        cards.forEach(function (c) { c.style.pointerEvents = ''; c.style.opacity = ''; });
      },
    });
  }

  function showPaymentQrCode(codeUrl, orderId, userId) {
    var qrEl = document.getElementById('paywall-qr');
    if (!qrEl) return;
    qrEl.style.display = 'block';
    qrEl.innerHTML = '<img src="https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=' +
      encodeURIComponent(codeUrl) + '" alt="支付二维码" style="border-radius:8px;">' +
      '<p style="margin-top:8px;font-size:0.8rem;color:var(--text-secondary);">打开微信扫一扫完成支付</p>';
    pollPaymentStatus(orderId, userId);
  }

  function pollPaymentStatus(orderId, userId) {
    var statusEl = document.getElementById('paywall-status');
    if (statusEl) statusEl.textContent = '确认支付中...';

    var attempts = 0;
    var maxAttempts = 30;

    function poll() {
      if (attempts >= maxAttempts) {
        if (statusEl) statusEl.textContent = '支付确认超时，请刷新页面';
        return;
      }
      attempts++;

      fetch('/api/payments/status/' + encodeURIComponent(orderId), {
        credentials: 'same-origin',
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.status === 'paid') {
            updateLocalTier(data.tier);
            if (statusEl) statusEl.textContent = '支付成功！正在继续...';
            setTimeout(function () {
              window.location.reload();
            }, 1000);
          } else {
            setTimeout(poll, 3000);
          }
        })
        .catch(function () {
          setTimeout(poll, 3000);
        });
    }

    setTimeout(poll, 1500);
  }

  function updateLocalTier(tier) {
    try {
      var userInfo = localStorage.getItem('sp_user_info');
      if (userInfo) {
        var parsed = JSON.parse(userInfo);
        parsed.tier = tier;
        localStorage.setItem('sp_user_info', JSON.stringify(parsed));
      }
    } catch (e) { /* ignore */ }
  }

  return {
    checkAndShow: checkAndShow,
  };
})();
