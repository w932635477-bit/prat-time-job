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
      var materialHeading = document.createElement('div');
      materialHeading.className = 'output-card__title fade-in';
      materialHeading.textContent = '启动素材';
      materialHeading.style.marginTop = 'var(--sp-6)';
      materialHeading.style.marginBottom = 'var(--sp-4)';
      container.appendChild(materialHeading);

      Object.keys(kitData.startup_materials).forEach(function (platform) {
        var materials = kitData.startup_materials[platform];
        if (materials && typeof materials === 'object') {
          container.appendChild(renderPlatformMaterials(platform, materials));
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
        '</div>';

      container.appendChild(pkgCard);
    }
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
