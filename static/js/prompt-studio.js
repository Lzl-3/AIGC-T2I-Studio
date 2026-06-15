/**
 * Qwen Prompt 工作室 - 前端交互模块
 * 折叠式面板，挂在主页面左侧顶部
 * 两段式：中文润色 -> ComfyUI 转换 -> 填入生成面板
 */

class QwenPromptManager {
  constructor(app) {
    this._app = app;
    this._polished = "";
    this._convertResult = null;
  }

  init() {
    this._bindEvents();
  }

  /** 绑定事件 */
  _bindEvents() {
    var self = this;

    // 字数统计 + 按钮启用
    var rawInput = document.getElementById("qwen-raw-input");
    if (rawInput) {
      rawInput.oninput = function () {
        var len = rawInput.value.length;
        var countEl = document.getElementById("qwen-char-count");
        if (countEl) {
          countEl.textContent = len;
          countEl.className = "qwen-char-count";
          if (len >= 500) countEl.className += " at-limit";
          else if (len >= 400) countEl.className += " near-limit";
        }
        var btn = document.getElementById("qwen-btn-polish");
        if (btn) btn.disabled = len === 0;
      };
    }

    // 快捷按钮（右侧生成区 -> 展开千问面板）
    var quickBtn = document.getElementById("qwen-quick-btn");
    if (quickBtn) {
      quickBtn.onclick = function () {
        self._openAndFocus();
      };
    }

    // 折叠/展开
    var header = document.getElementById("qwen-panel-header");
    if (header) {
      header.onclick = function () {
        self._toggle();
      };
    }

    // 润色按钮
    var btnPolish = document.getElementById("qwen-btn-polish");
    if (btnPolish) {
      btnPolish.onclick = function () {
        self._polish();
      };
    }

    // 转换按钮
    var btnConvert = document.getElementById("qwen-btn-convert");
    if (btnConvert) {
      btnConvert.onclick = function () {
        self._convert();
      };
    }

    // 填入生成面板
    var btnFill = document.getElementById("qwen-btn-fill");
    if (btnFill) {
      btnFill.onclick = function () {
        self._fillToMainForm();
      };
    }

    // 重新润色
    var btnRePolish = document.getElementById("qwen-btn-repolish");
    if (btnRePolish) {
      btnRePolish.onclick = function () {
        self._polish();
      };
    }
  }

  /** 展开千问面板并聚焦输入框 */
  _openAndFocus() {
    var body = document.querySelector(".qwen-panel-body");
    if (body && !body.classList.contains("expanded")) {
      body.classList.add("expanded");
      body.style.maxHeight = body.scrollHeight + "px";
      body.style.padding = "12px 14px";
      var arrow = document.querySelector(".qwen-panel-arrow");
      if (arrow) arrow.textContent = "▲";
    }
    // 滚动到千问面板
    var panel = document.getElementById("qwen-prompt-panel");
    if (panel) {
      panel.scrollIntoView({ behavior: "smooth", block: "start" });
      panel.style.transition = "box-shadow 0.3s";
      panel.style.boxShadow = "0 0 16px rgba(0,212,255,0.5)";
      setTimeout(function () {
        panel.style.boxShadow = "";
        setTimeout(function () { panel.style.transition = ""; }, 300);
      }, 2000);
    }
    // 聚焦输入框
    var input = document.getElementById("qwen-raw-input");
    if (input) {
      setTimeout(function () { input.focus(); }, 400);
    }
  }

  /** 折叠/展开切换（带动画） */
  _toggle() {
    var panel = document.getElementById("qwen-prompt-panel");
    if (!panel) return;
    var body = panel.querySelector(".qwen-panel-body");
    var arrow = panel.querySelector(".qwen-panel-arrow");
    if (!body) return;
    var isExpanded = body.classList.contains("expanded");
    if (isExpanded) {
      body.classList.remove("expanded");
      body.style.maxHeight = "0";
      body.style.padding = "0 14px";
      if (arrow) arrow.textContent = "▼";
    } else {
      body.classList.add("expanded");
      body.style.maxHeight = body.scrollHeight + "px";
      body.style.padding = "12px 14px";
      if (arrow) arrow.textContent = "▲";
    }
  }

  /** 阶段1：中文润色 */
  _polish() {
    var input = document.getElementById("qwen-raw-input");
    var idea = (input && input.value || "").trim();
    if (!idea) return;

    this._showLoading("qwen-polish-loading");
    this._hide("qwen-polish-result");
    this._hide("qwen-convert-result");

    var self = this;
    fetch("/api/prompt/polish", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ idea: idea }),
    })
      .then(function (r) {
        if (!r.ok) return r.json().then(function (e) { throw new Error(e.detail || "润色失败"); });
        return r.json();
      })
      .then(function (data) {
        self._polished = data.polished;
        var out = document.getElementById("qwen-polished-text");
        if (out) out.value = data.polished;
        self._show("qwen-polish-result");
        // 确保面板足够高以显示结果
        self._ensurePanelExpanded();
      })
      .catch(function (err) {
        alert("润色失败: " + err.message);
      })
      .finally(function () {
        self._hide("qwen-polish-loading");
      });
  }

  /** 阶段2：中文 -> ComfyUI 英文标签 */
  _convert() {
    var out = document.getElementById("qwen-polished-text");
    var chinese = (out && out.value || "").trim();
    if (!chinese) return;

    this._showLoading("qwen-convert-loading");
    this._hide("qwen-convert-result");

    var self = this;
    fetch("/api/prompt/convert", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chinese_prompt: chinese }),
    })
      .then(function (r) {
        if (!r.ok) return r.json().then(function (e) { throw new Error(e.detail || "转换失败"); });
        return r.json();
      })
      .then(function (data) {
        self._convertResult = data;
        var pos = document.getElementById("qwen-positive-text");
        var neg = document.getElementById("qwen-negative-text");
        var w = document.getElementById("qwen-param-width");
        var h = document.getElementById("qwen-param-height");
        var st = document.getElementById("qwen-param-steps");
        var cf = document.getElementById("qwen-param-cfg");
        if (pos) pos.value = data.positive;
        if (neg) neg.value = data.negative;
        if (w) w.value = (data.params && data.params.width) || 512;
        if (h) h.value = (data.params && data.params.height) || 768;
        if (st) st.value = (data.params && data.params.steps) || 20;
        if (cf) cf.value = (data.params && data.params.cfg) || 7.0;
        var tagCount = data.positive.split(",").length;
        var countEl = document.getElementById("qwen-tag-count");
        if (countEl) countEl.textContent = tagCount + " tags";
        self._show("qwen-convert-result");
        self._ensurePanelExpanded();
        // 滚动到转换结果
        var result = document.getElementById("qwen-convert-result");
        if (result) result.scrollIntoView({ behavior: "smooth", block: "nearest" });
      })
      .catch(function (err) {
        alert("转换失败: " + err.message);
      })
      .finally(function () {
        self._hide("qwen-convert-loading");
      });
  }

  /** 填入主生成面板 */
  _fillToMainForm() {
    var pos = document.getElementById("qwen-positive-text");
    var neg = document.getElementById("qwen-negative-text");
    var w = document.getElementById("qwen-param-width");
    var h = document.getElementById("qwen-param-height");

    // Standalone page: save to localStorage and navigate back
    if (!this._app) {
      var data = {};
      if (pos && pos.value) data.positive = pos.value;
      if (neg && neg.value) data.negative = neg.value;
      if (w) data.width = w.value;
      if (h) data.height = h.value;
      try {
        localStorage.setItem("qwen_fill_data", JSON.stringify(data));
      } catch(e) {}
      window.location.href = "/";
      return;
    }

    // Embedded mode: fill directly
    if (pos && pos.value) {
      var freePositive = document.getElementById("free-positive");
      if (freePositive) freePositive.value = pos.value;
    }
    if (neg && neg.value) {
      var freeNegative = document.getElementById("free-negative");
      if (freeNegative) freeNegative.value = neg.value;
    }
    if (w && h) {
      var iw = document.getElementById("img-width");
      var ih = document.getElementById("img-height");
      if (iw) iw.value = w.value;
      if (ih) ih.value = h.value;
    }

    if (this._app && this._app.switchTab) {
      this._app.switchTab("free");
    }

    var panel = document.getElementById("qwen-prompt-panel");
    if (panel) {
      panel.style.boxShadow = "0 0 12px rgba(0,212,255,0.5)";
      setTimeout(function () { panel.style.boxShadow = ""; }, 1500);
    }
  }

  /** 工具方法：显示元素 */
  _show(id) {
    var el = document.getElementById(id);
    if (el) el.style.display = "block";
  }

  /** 工具方法：隐藏元素 */
  _hide(id) {
    var el = document.getElementById(id);
    if (el) el.style.display = "none";
  }

  /** 确保面板高度足够显示内容 */
  _ensurePanelExpanded() {
    var body = document.querySelector(".qwen-panel-body");
    if (body && body.classList.contains("expanded")) {
      body.style.maxHeight = body.scrollHeight + "px";
    }
  }

  /** 工具方法：显示加载 */
  _showLoading(id) {
    var el = document.getElementById(id);
    if (el) el.style.display = "flex";
  }
}
