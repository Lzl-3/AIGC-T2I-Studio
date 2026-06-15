/**
 * 训练素材工作室 —— 前端交互逻辑
 *
 * 职责：身份选择 → 策略比例展示 → Prompt 预览 → 分批生成
 * 通过 App.materialStudio = new MaterialStudioManager(app) 挂载
 */

var MaterialStudioManager = (function () {
  "use strict";

  function MaterialStudioManager(app) {
    this.app = app;
    this.state = {
      identityKey: "",
      total: 150,
      batchSize: 10,
      modelType: "sdxl",
      previewPrompts: [],
      generating: false,
      taskIds: [],
    };
  }

  var P = MaterialStudioManager.prototype;

  /** 初始化：加载身份列表和策略数据 */
  P.init = function () {
    this._loadIdentities();
    this._loadLibrary();
    this._bindEvents();
  };

  /** 当切换到训练素材 Tab 时调用 */
  P.onTabShown = function () {
    if (!this._identitiesLoaded) {
      this._loadIdentities();
      this._loadLibrary();
    }
  };

  // ==============================
  // 数据加载
  // ==============================

  P._loadIdentities = function () {
    var self = this;
    fetch("/api/training/identity-presets")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var select = document.getElementById("tm-identity-select");
        if (!select) return;
        var options = '<option value="">-- 选择角色身份 --</option>';
        (data.identities || []).forEach(function (id) {
          options +=
            '<option value="' +
            id.key +
            '">' +
            id.name +
            " (" +
            id.gender +
            ", " +
            id.age_range +
            ")</option>";
        });
        select.innerHTML = options;
        self._identitiesLoaded = true;
      })
      .catch(function (e) {
        console.error("加载身份列表失败:", e);
      });
  };

  P._loadLibrary = function () {
    var self = this;
    fetch("/api/training/library")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        self._renderStrategyPanel(data);
      })
      .catch(function (e) {
        console.error("加载变体库失败:", e);
      });
  };

  // ==============================
  // 事件绑定
  // ==============================

  P._bindEvents = function () {
    var self = this;

    var sel = document.getElementById("tm-identity-select");
    if (sel) sel.onchange = function () { self._onIdentityChange(); };

    var total = document.getElementById("tm-total-slider");
    if (total) total.oninput = function () { self._onTotalChange(); };

    var batch = document.getElementById("tm-batch-size");
    if (batch) batch.onchange = function () { self.state.batchSize = parseInt(batch.value) || 10; };

    var modelSel = document.getElementById("tm-model-type");
    if (modelSel) modelSel.onchange = function () { self.state.modelType = modelSel.value || "sdxl"; };

    var btnPreview = document.getElementById("btn-tm-preview");
    if (btnPreview) btnPreview.onclick = function () { self._previewPrompts(); };

    var btnGenerate = document.getElementById("btn-tm-generate");
    if (btnGenerate) btnGenerate.onclick = function () { self._startGenerate(); };

    var btnStop = document.getElementById("btn-tm-stop");
    if (btnStop) btnStop.onclick = function () { self._stopGenerate(); };
  };

  // ==============================
  // 策略面板渲染
  // ==============================

  P._renderStrategyPanel = function (dimensions) {
    var container = document.getElementById("tm-strategy-panel");
    if (!container) return;

    var dimNames = ["costume", "background", "composition", "angle", "expression", "action", "weapon"];
    var html = "";

    dimNames.forEach(function (key) {
      var dim = dimensions[key];
      if (!dim) return;
      html += '<div class="tm-dim-group">';
      html += '<div class="tm-dim-label">' + dim.label + "</div>";
      html += '<div class="tm-dim-bars">';
      (dim.variants || []).forEach(function (v) {
        var pct = Math.round((v.ratio || v.count / 150 || 0) * 100);
        html +=
          '<span class="tm-dim-bar" style="flex:' +
          pct +
          ';" title="' +
          v.label +
          ": " +
          pct +
          '%">' +
          v.label +
          " " +
          pct +
          "%</span>";
      });
      html += "</div></div>";
    });

    container.innerHTML = html;
  };

  // ==============================
  // 身份切换
  // ==============================

  P._onIdentityChange = function () {
    var sel = document.getElementById("tm-identity-select");
    this.state.identityKey = sel ? sel.value : "";

    var infoEl = document.getElementById("tm-identity-info");
    var previewEl = document.getElementById("tm-preview-section");
    var generateBtn = document.getElementById("btn-tm-generate");

    if (this.state.identityKey) {
      if (infoEl) infoEl.style.display = "block";
      if (generateBtn) generateBtn.disabled = false;
    } else {
      if (infoEl) infoEl.style.display = "none";
      if (previewEl) previewEl.style.display = "none";
      if (generateBtn) generateBtn.disabled = true;
    }

    // 加载身份详情
    if (this.state.identityKey && infoEl) {
      this._loadIdentityDetail(this.state.identityKey);
    }
  };

  P._loadIdentityDetail = function (key) {
    var self = this;
    fetch("/api/training/identity-presets")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var identities = data.identities || [];
        var found = null;
        for (var i = 0; i < identities.length; i++) {
          if (identities[i].key === key) { found = identities[i]; break; }
        }
        var el = document.getElementById("tm-identity-info");
        if (found && el) {
          el.innerHTML =
            '<span class="tm-info-tag">触发词: ' +
            found.trigger_word +
            "</span>" +
            '<span class="tm-info-tag">性别: ' +
            found.gender +
            "</span>" +
            '<span class="tm-info-tag">年龄段: ' +
            found.age_range +
            "</span>" +
            '<span class="tm-info-tag">气质: ' +
            found.temperament +
            "</span>";
        }
      });
  };

  // ==============================
  // 总量变更
  // ==============================

  P._onTotalChange = function () {
    var slider = document.getElementById("tm-total-slider");
    var display = document.getElementById("tm-total-display");
    if (slider) {
      this.state.total = parseInt(slider.value) || 150;
      if (display) display.textContent = this.state.total;
    }
  };

  // ==============================
  // Prompt 预览
  // ==============================

  P._previewPrompts = function () {
    var self = this;
    if (!this.state.identityKey) {
      alert("请先选择角色身份");
      return;
    }

    var previewSection = document.getElementById("tm-preview-section");
    var previewList = document.getElementById("tm-preview-list");
    var previewCount = document.getElementById("tm-preview-count");
    var statusEl = document.getElementById("tm-status");

    if (statusEl) {
      statusEl.textContent = "正在生成 Prompt 预览...";
      statusEl.className = "ps-status ps-status-loading";
    }

    fetch("/api/training/material/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identity_key: this.state.identityKey, total: this.state.total, model_type: this.state.modelType }),
    })
      .then(function (r) {
        if (!r.ok) return r.json().then(function (e) { throw new Error(e.detail || "预览失败"); });
        return r.json();
      })
      .then(function (data) {
        self.state.previewPrompts = data.prompts || [];
        if (previewSection) previewSection.style.display = "block";
        if (previewCount) previewCount.textContent = self.state.previewPrompts.length;

        // 渲染预览列表（只显示前 30 条，避免 DOM 过重）
        var showCount = Math.min(self.state.previewPrompts.length, 30);
        var html = "";
        for (var i = 0; i < showCount; i++) {
          var p = self.state.previewPrompts[i];
          var meta = p.meta || {};
          html +=
            '<div class="tm-preview-item">' +
            '<span class="tm-preview-idx">#' +
            (i + 1) +
            "</span>" +
            '<span class="tm-preview-meta">' +
            meta.costume +
            " | " +
            meta.background +
            " | " +
            meta.angle +
            " | " +
            meta.expression +
            "</span>" +
            '<span class="tm-preview-prompt" title="' +
            self._escAttr(p.positive) +
            '">' +
            self._escHtml(p.positive.substring(0, 80)) +
            (p.positive.length > 80 ? "..." : "") +
            "</span>" +
            "</div>";
        }
        if (self.state.previewPrompts.length > 30) {
          html +=
            '<div class="tm-preview-more">... 还有 ' +
            (self.state.previewPrompts.length - 30) +
            " 条未显示</div>";
        }
        if (previewList) previewList.innerHTML = html;
        if (statusEl) {
          statusEl.textContent = "预览完成：" + self.state.previewPrompts.length + " 条 Prompt 已就绪";
          statusEl.className = "ps-status";
        }
      })
      .catch(function (err) {
        if (statusEl) {
          statusEl.textContent = "预览失败: " + err.message;
          statusEl.className = "ps-status ps-status-error";
        }
      });
  };

  // ==============================
  // 开始生成
  // ==============================

  P._startGenerate = function () {
    var self = this;
    if (!this.state.identityKey) {
      alert("请先选择角色身份");
      return;
    }
    if (this.state.generating) return;

    this.state.generating = true;
    var statusEl = document.getElementById("tm-status");
    var progressBar = document.getElementById("tm-progress-bar");
    var progressText = document.getElementById("tm-progress-text");
    var btnGen = document.getElementById("btn-tm-generate");
    var btnStop = document.getElementById("btn-tm-stop");

    if (btnGen) btnGen.disabled = true;
    if (btnStop) btnStop.style.display = "inline-block";
    if (statusEl) { statusEl.textContent = "正在提交生成任务..."; statusEl.className = "ps-status ps-status-loading"; }

    fetch("/api/training/material/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        identity_key: this.state.identityKey,
        total: this.state.total,
        model_type: this.state.modelType,
        batch_size: this.state.batchSize,
      }),
    })
      .then(function (r) {
        if (!r.ok) return r.json().then(function (e) { throw new Error(e.detail || "生成失败"); });
        return r.json();
      })
      .then(function (data) {
        self.state.taskIds = data.task_ids || [];
        if (statusEl) {
          statusEl.innerHTML =
            '已提交 ' +
            data.total_images +
            " 张素材（" +
            data.batches +
            ' 批），<a href="#" onclick="App.materialStudio._viewTasks()">查看任务队列</a>';
          statusEl.className = "ps-status";
        }
        self.state.generating = false;
        if (btnGen) btnGen.disabled = false;
        if (btnStop) btnStop.style.display = "none";
      })
      .catch(function (err) {
        if (statusEl) {
          statusEl.textContent = "提交失败: " + err.message;
          statusEl.className = "ps-status ps-status-error";
        }
        self.state.generating = false;
        if (btnGen) btnGen.disabled = false;
        if (btnStop) btnStop.style.display = "none";
      });
  };

  P._stopGenerate = function () {
    this.state.generating = false;
    var btnStop = document.getElementById("btn-tm-stop");
    if (btnStop) btnStop.style.display = "none";
    var btnGen = document.getElementById("btn-tm-generate");
    if (btnGen) btnGen.disabled = false;
  };

  P._viewTasks = function () {
    // 切换到任务 Tab 查看进度
    if (this.app && this.app.switchTab) {
      // 主页没有独立任务 tab，刷新图库即可
      if (this.app.gallery) this.app.gallery.load();
    }
  };

  // ==============================
  // 工具函数
  // ==============================

  P._escHtml = function (str) {
    var div = document.createElement("div");
    div.textContent = str || "";
    return div.innerHTML;
  };

  P._escAttr = function (str) {
    return (str || "").replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  };

  return MaterialStudioManager;
})();