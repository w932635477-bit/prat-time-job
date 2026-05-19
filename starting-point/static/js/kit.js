// starting-point/static/js/kit.js
// Kit display: load kit data, render platform cards and materials, copy to clipboard

var Kit = (function () {
  'use strict';

  var POLL_INTERVAL = 2000;
  var POLL_MAX_ATTEMPTS = 60;
  var pollAttempts = 0;

  // ---- DOM helpers ----

  function escapeHtml(str) {
    if (typeof str !== 'string') return '';
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function escapeHtmlObj(obj) {
    if (typeof obj === 'string') return escapeHtml(obj);
    if (typeof obj === 'number') return String(obj);
    if (Array.isArray(obj)) return obj.map(escapeHtmlObj).join(', ');
    if (obj && typeof obj === 'object') {
      return Object.entries(obj)
        .map(function (e) { return e[0] + ': ' + escapeHtmlObj(e[1]); })
        .join('\n');
    }
    return '';
  }

  // ---- Copy to clipboard ----

  function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text).then(function () {
        return true;
      }).catch(function () {
        return fallbackCopy(text);
      });
    }
    return fallbackCopy(text);
  }

  function fallbackCopy(text) {
    var textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    try {
      document.execCommand('copy');
      return Promise.resolve(true);
    } catch (e) {
      return Promise.resolve(false);
    } finally {
      document.body.removeChild(textarea);
    }
  }

  function createCopyButton(text) {
    var btn = document.createElement('button');
    btn.className = 'copy-btn';
    btn.textContent = '复制';
    btn.addEventListener('click', function () {
      copyToClipboard(text).then(function (success) {
        if (success) {
          btn.textContent = '已复制';
          btn.classList.add('copy-btn--copied');
          setTimeout(function () {
            btn.textContent = '复制';
            btn.classList.remove('copy-btn--copied');
          }, 2000);
        }
      });
    });
    return btn;
  }

  // ---- Render platform recommendations ----

  function renderPlatformRecommendations(recommendations) {
    if (!recommendations || recommendations.length === 0) return null;

    var section = document.createElement('div');
    section.className = 'fade-in';

    recommendations
      .sort(function (a, b) { return (a.priority || 99) - (b.priority || 99); })
      .forEach(function (rec) {
        var card = document.createElement('div');
        card.className = 'platform-card';

        card.innerHTML =
          '<div class="platform-card__header">' +
            '<span class="platform-card__name">' + escapeHtml(rec.platform) + '</span>' +
            '<span class="platform-card__priority">推荐 #' + (rec.priority || '-') + '</span>' +
          '</div>' +
          '<div class="platform-card__reason">' + escapeHtml(rec.reason) + '</div>' +
          '<div class="platform-card__format">内容形式: ' + escapeHtml(rec.content_format) + '</div>';

        section.appendChild(card);
      });

    return section;
  }

  // ---- Render action guide ----

  function renderActionGuide(guide, kitId) {
    var card = document.createElement('div');
    card.className = 'action-guide fade-in';

    var html = '<div class="action-guide__title">你的第一步</div>';

    if (guide.day1_what) {
      html += '<div class="action-guide__what">' + escapeHtml(guide.day1_what) + '</div>';
    }
    if (guide.day1_how) {
      html += '<div class="action-guide__how">' + escapeHtml(guide.day1_how) + '</div>';
    }
    if (guide.week_goal) {
      html += '<div class="action-guide__goal">7天目标: ' + escapeHtml(guide.week_goal) + '</div>';
    }
    if (guide.mindset_tip) {
      html += '<div class="action-guide__tip">' + escapeHtml(guide.mindset_tip) + '</div>';
    }

    card.innerHTML = html;
    return card;
  }

  // ---- Check-in (localStorage) ----

  function getCheckinKey(kitId, platform, day) {
    return 'sp_checkin_' + kitId + '_' + platform + '_' + day;
  }

  function isCheckedIn(kitId, platform, day) {
    return !!localStorage.getItem(getCheckinKey(kitId, platform, day));
  }

  function doCheckIn(kitId, platform, day, btn) {
    localStorage.setItem(getCheckinKey(kitId, platform, day), String(Date.now()));
    btn.textContent = '已完成';
    btn.classList.add('calendar-day__checkin-btn--done');
    btn.disabled = true;

    var dayCard = btn.closest('.calendar-day');
    if (dayCard) dayCard.classList.add('calendar-day--done');

    fetch('/api/checkin', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ kit_id: kitId, platform: platform, day: day }),
    }).catch(function () { /* offline fallback: localStorage already saved */ });
  }

  // ---- Render content calendar ----

  function renderContentCalendar(platform, calendar, kitId, createdAt) {
    if (!calendar || calendar.length === 0) return null;

    var section = document.createElement('div');
    section.className = 'calendar-section fade-in';

    var title = document.createElement('div');
    title.className = 'calendar-section__title';
    title.textContent = platform + ' 7天内容日历';
    section.appendChild(title);

    // Calculate current day number based on kit creation time
    var currentDay = 1;
    if (createdAt) {
      var createdMs = new Date(createdAt.replace(' ', 'T')).getTime();
      if (!isNaN(createdMs)) {
        currentDay = Math.floor((Date.now() - createdMs) / 86400000) + 1;
        if (currentDay < 1) currentDay = 1;
        if (currentDay > 7) currentDay = 7;
      }
    }

    // Show progress indicator
    var progress = document.createElement('div');
    progress.className = 'calendar-progress';
    var doneCount = calendar.filter(function (d) { return d.day <= currentDay; }).length;
    progress.textContent = '进度: ' + doneCount + '/' + calendar.length + ' 天已解锁';
    section.appendChild(progress);

    calendar.forEach(function (day) {
      // Only show current day and earlier (unlock by day)
      if (day.day > currentDay) {
        var locked = document.createElement('div');
        locked.className = 'calendar-day calendar-day--locked';
        locked.innerHTML =
          '<div class="calendar-day__header">' +
            '<span class="calendar-day__badge">第' + day.day + '天</span>' +
            '<span class="calendar-day__theme">明天解锁</span>' +
          '</div>' +
          '<div class="calendar-day__locked-text">完成今天的任务后，明天会解锁新内容</div>';
        section.appendChild(locked);
        return;
      }
      var card = document.createElement('div');
      card.className = 'calendar-day';
      if (isCheckedIn(kitId, platform, day.day)) {
        card.classList.add('calendar-day--done');
      }

      var bodyText = day.body || '';
      card.innerHTML =
        '<div class="calendar-day__header">' +
          '<span class="calendar-day__badge">第' + day.day + '天</span>' +
          '<span class="calendar-day__theme">' + escapeHtml(day.theme || '') + '</span>' +
          (day.estimated_time ? '<span class="calendar-day__time">' + escapeHtml(day.estimated_time) + '</span>' : '') +
        '</div>' +
        '<div class="calendar-day__title">' + escapeHtml(day.title || '') + '</div>' +
        (bodyText ? '<div class="calendar-day__body">' + escapeHtml(bodyText) + '</div>' : '') +
        (day.why ? '<div class="calendar-day__why">' + escapeHtml(day.why) + '</div>' : '') +
        (day.success_signal ? '<div class="calendar-day__signal">成功信号: ' + escapeHtml(day.success_signal) + '</div>' : '');

      if (bodyText) {
        var labelRow = card.querySelector('.calendar-day__body');
        if (labelRow) {
          var copyBtn = createCopyButton(day.title ? day.title + '\n\n' + bodyText : bodyText);
          copyBtn.style.marginTop = '4px';
          labelRow.appendChild(copyBtn);
        }
      }

      var checkinBtn = document.createElement('button');
      checkinBtn.className = 'calendar-day__checkin-btn';
      if (isCheckedIn(kitId, platform, day.day)) {
        checkinBtn.textContent = '已完成';
        checkinBtn.classList.add('calendar-day__checkin-btn--done');
        checkinBtn.disabled = true;
      } else {
        checkinBtn.textContent = '打卡';
        checkinBtn.addEventListener('click', function () {
          doCheckIn(kitId, platform, day.day, checkinBtn);
        });
      }
      card.appendChild(checkinBtn);

      section.appendChild(card);
    });

    return section;
  }

  // ---- Render startup materials for one platform ----

  function renderPlatformMaterials(platformName, materials) {
    var section = document.createElement('div');
    section.className = 'material-section fade-in';

    var title = document.createElement('div');
    title.className = 'material-section__title';
    title.textContent = platformName + ' 启动素材';
    section.appendChild(title);

    // Account name suggestions
    if (materials.account_name_suggestions && materials.account_name_suggestions.length > 0) {
      var namesText = materials.account_name_suggestions.join(' / ');
      section.appendChild(createMaterialField('账号名建议', namesText));
    }

    // Short bio
    if (materials.bio_short) {
      section.appendChild(createMaterialField('一句话简介', materials.bio_short));
    }

    // Full bio
    if (materials.bio_full) {
      section.appendChild(createMaterialField('详细简介', materials.bio_full));
    }

    // First post
    if (materials.first_post) {
      var post = materials.first_post;
      var postText = '';
      if (post.title) postText += post.title + '\n\n';
      if (post.body) postText += post.body;
      if (post.price) postText += '\n\n定价: ' + post.price + ' 元';
      section.appendChild(createMaterialField('第一条内容', postText));
    }

    // Reply templates
    if (materials.reply_templates && materials.reply_templates.length > 0) {
      var templatesText = materials.reply_templates
        .map(function (t) {
          return '【' + t.trigger + '】\n' + t.reply;
        })
        .join('\n\n');
      section.appendChild(createMaterialField('回复模板', templatesText));
    }

    return section;
  }

  function createMaterialField(label, value) {
    var field = document.createElement('div');
    field.className = 'material-field';

    var labelEl = document.createElement('div');
    labelEl.className = 'material-field__label';
    labelEl.innerHTML = '<span>' + escapeHtml(label) + '</span>';
    labelEl.appendChild(createCopyButton(value));

    var valueEl = document.createElement('div');
    valueEl.className = 'material-field__value';
    valueEl.textContent = value;

    field.appendChild(labelEl);
    field.appendChild(valueEl);
    return field;
  }

  // ---- Render full kit ----

  function renderKit(kitData) {
    var container = document.getElementById('kit-content');
    if (!container) return;

    container.innerHTML = '';

    // Content direction banner
    if (kitData.content_direction) {
      var direction = document.createElement('div');
      direction.className = 'content-direction fade-in';
      direction.textContent = kitData.content_direction;
      container.appendChild(direction);
    }

    // Platform recommendations
    if (kitData.platform_recommendations && kitData.platform_recommendations.length > 0) {
      var heading = document.createElement('div');
      heading.className = 'output-card__title fade-in';
      heading.textContent = '推荐平台';
      heading.style.marginBottom = 'var(--sp-4)';
      container.appendChild(heading);

      var recsEl = renderPlatformRecommendations(kitData.platform_recommendations);
      if (recsEl) container.appendChild(recsEl);
    }

    // Startup materials per platform
    if (kitData.startup_materials && Object.keys(kitData.startup_materials).length > 0) {
      var kitId = kitData.id || 'unknown';
      var kitCreatedAt = kitData.created_at || null;

      // Action guide (shown first)
      var guide = kitData.startup_materials._action_guide;
      if (guide && typeof guide === 'object') {
        container.appendChild(renderActionGuide(guide, kitId));
      }

      var materialHeading = document.createElement('div');
      materialHeading.className = 'output-card__title fade-in';
      materialHeading.textContent = '启动素材';
      materialHeading.style.marginTop = 'var(--sp-6)';
      materialHeading.style.marginBottom = 'var(--sp-4)';
      container.appendChild(materialHeading);

      Object.keys(kitData.startup_materials).forEach(function (platform) {
        if (platform.startsWith('_')) return;
        var materials = kitData.startup_materials[platform];
        if (materials && typeof materials === 'object') {
          container.appendChild(renderPlatformMaterials(platform, materials));

          // Content calendar for this platform
          if (materials.content_calendar && materials.content_calendar.length > 0) {
            container.appendChild(renderContentCalendar(platform, materials.content_calendar, kitId, kitCreatedAt));
          }
        }
      });
    }

    // Product package summary
    if (kitData.product_package) {
      var pkg = kitData.product_package;
      var pkgCard = document.createElement('div');
      pkgCard.className = 'output-card fade-in';
      pkgCard.style.marginTop = 'var(--sp-6)';

      var serviceLabels = {
        consultation: '咨询服务',
        content: '内容产品',
        service: '服务交付',
      };

      pkgCard.innerHTML =
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
        (pkg.service_flow && pkg.service_flow.length > 0
          ? '<div class="output-card__field">' +
              '<div class="output-card__label">服务流程</div>' +
              '<div class="output-card__value"><ol style="margin:0;padding-left:1.2em;">' +
                pkg.service_flow.map(function (s) { return '<li>' + escapeHtml(s) + '</li>'; }).join('') +
              '</ol></div>' +
            '</div>'
          : '') +
        (pkg.deliverables
          ? '<div class="output-card__field">' +
              '<div class="output-card__label">客户获得</div>' +
              '<div class="output-card__value">' + escapeHtml(pkg.deliverables) + '</div>' +
            '</div>'
          : '') +
        (pkg.tools_recommended && pkg.tools_recommended.length > 0
          ? '<div class="output-card__field">' +
              '<div class="output-card__label">推荐工具</div>' +
              '<div class="output-card__value">' + escapeHtml(pkg.tools_recommended.join('、')) + '</div>' +
            '</div>'
          : '');

      container.appendChild(pkgCard);
    }

    // Export all button
    var exportBtn = document.createElement('button');
    exportBtn.className = 'export-btn fade-in';
    exportBtn.textContent = '复制全部内容';
    exportBtn.addEventListener('click', function () {
      var text = kitToPlainText(kitData, kitCreatedAt);
      copyToClipboard(text).then(function (success) {
        if (success) {
          exportBtn.textContent = '已复制';
          exportBtn.classList.add('copy-btn--copied');
          setTimeout(function () {
            exportBtn.textContent = '复制全部内容';
            exportBtn.classList.remove('copy-btn--copied');
          }, 2000);
        }
      });
    });
    container.appendChild(exportBtn);

    // WeChat follow guide
    container.appendChild(renderWeChatGuide());
  }

  // ---- WeChat follow guide ----

  function renderWeChatGuide() {
    if (localStorage.getItem('sp_wechat_guide_dismissed')) return document.createElement('span');

    var card = document.createElement('div');
    card.className = 'wechat-guide fade-in';

    var closeBtn = document.createElement('button');
    closeBtn.className = 'wechat-guide__close';
    closeBtn.textContent = '×';
    closeBtn.addEventListener('click', function () {
      localStorage.setItem('sp_wechat_guide_dismissed', '1');
      card.style.display = 'none';
    });

    card.innerHTML =
      '<div class="wechat-guide__title">每天收到行动提醒</div>' +
      '<div class="wechat-guide__desc">关注公众号，每天早上收到当天的内容任务和鼓励，不再断更</div>' +
      '<div class="wechat-guide__qr">' +
        '<div class="wechat-guide__qr-placeholder">公众号二维码</div>' +
      '</div>' +
      '<div class="wechat-guide__hint">长按识别二维码，关注即可</div>';
    card.appendChild(closeBtn);

    return card;
  }

  function kitToPlainText(kitData, createdAt) {
    var lines = [];

    // Calculate current day for calendar filtering
    var currentDay = 7;
    if (createdAt) {
      var createdMs = new Date(createdAt.replace(' ', 'T')).getTime();
      if (!isNaN(createdMs)) {
        currentDay = Math.floor((Date.now() - createdMs) / 86400000) + 1;
        if (currentDay < 1) currentDay = 1;
        if (currentDay > 7) currentDay = 7;
      }
    }
    if (kitData.content_direction) {
      lines.push('【内容方向】');
      lines.push(kitData.content_direction);
      lines.push('');
    }
    // Action guide
    if (kitData.startup_materials && kitData.startup_materials._action_guide) {
      var g = kitData.startup_materials._action_guide;
      lines.push('【行动指南】');
      if (g.day1_what) lines.push('今天做什么: ' + g.day1_what);
      if (g.day1_how) lines.push('操作步骤: ' + g.day1_how);
      if (g.week_goal) lines.push('7天目标: ' + g.week_goal);
      if (g.mindset_tip) lines.push('心态提醒: ' + g.mindset_tip);
      lines.push('');
    }
    if (kitData.platform_recommendations && kitData.platform_recommendations.length > 0) {
      lines.push('【推荐平台】');
      kitData.platform_recommendations
        .sort(function (a, b) { return (a.priority || 99) - (b.priority || 99); })
        .forEach(function (rec) {
          lines.push('#' + (rec.priority || '-') + ' ' + rec.platform + ' - ' + rec.reason);
          lines.push('  内容形式: ' + rec.content_format);
        });
      lines.push('');
    }
    if (kitData.startup_materials) {
      Object.keys(kitData.startup_materials).forEach(function (platform) {
        if (platform.startsWith('_')) return;
        var m = kitData.startup_materials[platform];
        if (!m || typeof m !== 'object') return;
        lines.push('【' + platform + ' 启动素材】');
        if (m.account_name_suggestions) lines.push('账号名: ' + m.account_name_suggestions.join(' / '));
        if (m.bio_short) lines.push('简介: ' + m.bio_short);
        if (m.bio_full) lines.push('详细简介: ' + m.bio_full);
        if (m.first_post) {
          if (m.first_post.title) lines.push('首条标题: ' + m.first_post.title);
          if (m.first_post.body) lines.push('首条内容: ' + m.first_post.body);
          if (m.first_post.price) lines.push('定价: ' + m.first_post.price + ' 元');
        }
        if (m.reply_templates) {
          m.reply_templates.forEach(function (t) {
            lines.push('回复模板[' + t.trigger + ']: ' + t.reply);
          });
        }
        if (m.content_calendar && m.content_calendar.length > 0) {
          lines.push('');
          var unlockedDays = m.content_calendar.filter(function (d) { return d.day <= currentDay; });
          lines.push('【' + platform + ' 内容日历（已解锁' + unlockedDays.length + '/' + m.content_calendar.length + '天）】');
          unlockedDays.forEach(function (d) {
            lines.push('第' + d.day + '天 [' + (d.theme || '') + '] ' + (d.title || ''));
            if (d.body) lines.push(d.body);
            if (d.why) lines.push('  原因: ' + d.why);
            lines.push('');
          });
        }
        lines.push('');
      });
    }
    if (kitData.product_package) {
      var pkg = kitData.product_package;
      lines.push('【产品方案】');
      lines.push('产品名: ' + (pkg.product_name || ''));
      lines.push(pkg.one_liner || '');
      if (pkg.target_buyer) lines.push('目标客户: ' + pkg.target_buyer);
      if (pkg.price_range) lines.push('定价: ' + pkg.price_range.min + '-' + pkg.price_range.max + ' 元');
      if (pkg.delivery_method) lines.push('交付方式: ' + pkg.delivery_method);
      if (pkg.service_flow) lines.push('服务流程: ' + pkg.service_flow.join(' → '));
      if (pkg.deliverables) lines.push('客户获得: ' + pkg.deliverables);
      if (pkg.tools_recommended) lines.push('推荐工具: ' + pkg.tools_recommended.join('、'));
    }
    return lines.join('\n');
  }

  // ---- Load kit ----

  function loadKit(userId) {
    var kitContent = document.getElementById('kit-content');
    if (!kitContent) return;

    kitContent.innerHTML =
      '<div class="kit-loading">' +
        '<div class="kit-loading__title">正在生成你的启动套件...</div>' +
        '<div class="kit-loading__desc">这可能需要1-2分钟，请稍候</div>' +
        '<div class="loading-dots"><span></span><span></span><span></span></div>' +
      '</div>';

    pollAttempts = 0;
    pollKitStatus(userId);
  }

  function pollKitStatus(userId) {
    pollAttempts++;

    if (pollAttempts > POLL_MAX_ATTEMPTS) {
      var kitContent = document.getElementById('kit-content');
      if (kitContent) {
        kitContent.innerHTML =
          '<div class="error-banner">启动套件生成超时，请刷新页面重试。</div>';
      }
      return;
    }

    fetch('/api/kit-status/' + encodeURIComponent(userId))
      .then(function (resp) {
        if (!resp.ok) throw new Error('Status check failed: ' + resp.status);
        return resp.json();
      })
      .then(function (data) {
        if (data.status === 'completed') {
          fetchKitData(userId);
        } else if (data.status === 'failed') {
          var kitContent = document.getElementById('kit-content');
          if (kitContent) {
            kitContent.innerHTML =
              '<div class="error-banner">启动套件生成失败，请重试。</div>';
          }
        } else {
          setTimeout(function () { pollKitStatus(userId); }, POLL_INTERVAL);
        }
      })
      .catch(function (err) {
        console.error('Kit status poll error:', err);
        setTimeout(function () { pollKitStatus(userId); }, POLL_INTERVAL);
      });
  }

  function fetchKitData(userId) {
    fetch('/api/kit/' + encodeURIComponent(userId))
      .then(function (resp) {
        if (!resp.ok) throw new Error('Load kit failed: ' + resp.status);
        return resp.json();
      })
      .then(function (kit) {
        renderKit(kit);
      })
      .catch(function (err) {
        console.error('Load kit error:', err);
        var kitContent = document.getElementById('kit-content');
        if (kitContent) {
          kitContent.innerHTML =
            '<div class="error-banner">加载启动套件失败，请刷新页面。</div>';
        }
      });
  }

  // ---- Public API ----

  return {
    loadKit: loadKit,
    renderKit: renderKit,
    copyToClipboard: copyToClipboard,
  };
})();
