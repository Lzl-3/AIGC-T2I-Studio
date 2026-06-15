/**
 * 风格标签选择器 —— 从100+标签库中多选组合
 *
 * 职责：加载风格标签 → 渲染分类面板 → 多选标签 → 输出选中列表
 * 挂载: App.stylePalette = new StylePaletteManager(app)
 */

var StylePaletteManager = (function () {
  "use strict";

  function StylePaletteManager(app) {
    this.app = app;
    this.categories = {};
    this.presets = {};
    this.selected = [];
    this.customTags = [];
    this.onChange = null;  // 回调: function(selectedTags)
  }

  var P = StylePaletteManager.prototype;

  P.init = function () {
    this._load();
  };

  P._load = function () {
    var self = this;
    fetch("/api/style-tags")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        self.categories = data.categories || {};
        self.presets = data.presets || {};
        self._render();
      })
      .catch(function (e) { console.error("加载风格标签失败:", e); });
  };

  P._render = function () {
    var self = this;
    var container = document.getElementById("style-palette");
    if (!container) return;

    var catKeys = Object.keys(this.categories);
    var html = '<div class="sp-tabs">';
    catKeys.forEach(function (key, i) {
      var cat = self.categories[key];
      html += '<button class="sp-tab' + (i === 0 ? ' active' : '') + '" data-cat="' + key + '">' + (cat.icon || '') + ' ' + cat.label + '</button>';
    });
    html += '</div><div class="sp-tags-container" id="sp-tags-container"></div>';
    html += '<div id="sp-custom-tags" class="sp-custom-tags"></div>';
    html += '<div class="sp-footer"><span id="sp-selected-count">??: 0</span>';
    html += '<button class="sp-btn-clear" id="sp-clear-all">??</button></div>';
    html += '<div class="sp-custom"><input type="text" id="sp-custom-input" class="sp-custom-input" placeholder="输入自定义风格..."><button class="sp-custom-btn" id="sp-custom-btn">+ 添加</button></div>';

    container.innerHTML = html;
    this._renderCustomTags();
    this._showCategory(catKeys[0]);
    this._bindEvents();
  };

  P._showCategory = function (catKey) {
    var container = document.getElementById("sp-tags-container");
    if (!container) return;
    var cat = this.categories[catKey];
    if (!cat) return;

    var self = this;
    var html = "";
    (cat.tags || []).forEach(function (tag) {
      var active = self.selected.indexOf(tag) >= 0 ? " active" : "";
      html += '<span class="sp-tag' + active + '" data-tag="' + self._escAttr(tag) + '">' + self._escHtml(tag) + '</span>';
    });
    container.innerHTML = html;

    // Bind tag clicks
    container.querySelectorAll(".sp-tag").forEach(function (el) {
      el.onclick = function () {
        var tag = this.getAttribute("data-tag");
        self._toggleTag(tag);
      };
    });
  };

  P._bindEvents = function () {
    var self = this;
    var tabs = document.querySelectorAll("#style-palette .sp-tab");
    tabs.forEach(function (tab) {
      tab.onclick = function () {
        tabs.forEach(function (t) { t.classList.remove("active"); });
        this.classList.add("active");
        self._showCategory(this.getAttribute("data-cat"));
      };
    });

    var clearBtn = document.getElementById("sp-clear-all");
    if (clearBtn) clearBtn.onclick = function () { self._clearAll(); };

    var customInput = document.getElementById("sp-custom-input");
    var customBtn = document.getElementById("sp-custom-btn");
    if (customInput) customInput.onkeydown = function (e) { if (e.key === "Enter") { e.preventDefault(); self._addCustomTag(); } };
    if (customBtn) customBtn.onclick = function () { self._addCustomTag(); };
  };

  P._toggleTag = function (tag) {
    var idx = this.selected.indexOf(tag);
    if (idx >= 0) {
      this.selected.splice(idx, 1);
    } else {
      this.selected.push(tag);
    }
    this._updateUI();
    if (this.onChange) this.onChange(this.selected);
  };

  P._clearAll = function () {
    this.selected = [];
    this.customTags = [];
    this._renderCustomTags();
    this._updateUI();
    if (this.onChange) this.onChange([]);
  };

  P._updateUI = function () {
    var self = this;
    var count = document.getElementById("sp-selected-count");
    if (count) count.textContent = "已选: " + this.selected.length;

    // Update tag active states
    var container = document.getElementById("sp-tags-container");
    if (container) {
      container.querySelectorAll(".sp-tag").forEach(function (el) {
        var tag = el.getAttribute("data-tag");
        if (self.selected.indexOf(tag) >= 0) {
          el.classList.add("active");
        } else {
          el.classList.remove("active");
        }
      });
    }
  };

  P._addCustomTag = function () {
    var input = document.getElementById("sp-custom-input");
    if (!input) return;
    var tag = input.value.trim();
    if (!tag) return;
    if (this.customTags.indexOf(tag) >= 0) { input.value = ""; return; }
    this.customTags.push(tag);
    input.value = "";
    this._renderCustomTags();
    this._notify();
  };

  P._removeCustomTag = function (tag) {
    var idx = this.customTags.indexOf(tag);
    if (idx >= 0) { this.customTags.splice(idx, 1); }
    this._renderCustomTags();
    this._notify();
  };

  P._renderCustomTags = function () {
    var container = document.getElementById("sp-custom-tags");
    if (!container) return;
    var self = this;
    var html = "";
    this.customTags.forEach(function (tag) {
      html += '<span class="sp-tag sp-tag-custom" onclick="App.stylePalette._removeCustomTag(&quot;' + self._escAttr(tag) + '&quot;)" title="点击移除">' + self._escHtml(tag) + ' <span style="opacity:0.5">x</span></span>';
    });
    container.innerHTML = html;
  };

  P._notify = function () {
    var count = document.getElementById("sp-selected-count");
    if (count) count.textContent = "已选: " + (this.selected.length + this.customTags.length);
    if (this.onChange) this.onChange(this.getSelected());
  };

  P.getSelected = function () {
    return this.selected.concat(this.customTags);
  };

  P._escHtml = function (str) {
    var div = document.createElement("div");
    div.textContent = str || "";
    return div.innerHTML;
  };

  P._escAttr = function (str) {
    return (str || "").replace(/&/g, "&amp;").replace(/"/g, "&quot;");
  };

  return StylePaletteManager;
})();