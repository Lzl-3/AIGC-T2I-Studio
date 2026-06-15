// -*- coding: utf-8 -*-
// WD14 Tagger - 前端标签提取模块
// 用户选图 -> 后端推理 -> 展示标签列表

class WD14TaggerManager {
  constructor(app) {
    this.app = app;
    this._threshold = 0.35;
    this._tags = {};
    this._ratings = {};
  }


  init() {
    // 绑定侧边栏按钮
    var btn = document.getElementById("tab-tagger");
    if (btn) btn.onclick = () => this.app.switchTab("tagger");

    // 确保 UI 容器存在
    this._ensureUI();
  }


  // ── UI 渲染 ──

  _ensureUI() {
    if (document.getElementById("tagger-panel")) return;

    var panel = document.createElement("div");
    panel.id = "tagger-panel";
    panel.style.display = "none";
    panel.innerHTML =
      "<div style='padding:12px 0;'>" +
      "<div style='display:flex;align-items:center;gap:12px;margin-bottom:12px;'>" +
      "<label id='tagger-upload-label' style='display:inline-flex;align-items:center;gap:6px;padding:8px 16px;background:var(--accent);color:#000;border-radius:6px;cursor:pointer;font-size:14px;font-weight:600;'>" +
      "选择图片" +
      "<input type='file' id='tagger-file-input' accept='image/*' style='display:none;'>" +
      "</label>" +
      "<span id='tagger-file-name' style='color:var(--text-muted);font-size:13px;'></span>" +
      "</div>" +
      "<div style='display:flex;align-items:center;gap:10px;margin-bottom:12px;'>" +
      "<label style='font-size:13px;color:var(--text-secondary);white-space:nowrap;'>最低置信度</label>" +
      "<input type='range' id='tagger-threshold' min='0' max='1' step='0.05' value='0.35' style='flex:1;max-width:200px;'>" +
      "<span id='tagger-threshold-val' style='font-size:13px;color:var(--accent);min-width:36px;'>0.35</span>" +
      "</div>" +
      "<div style='margin-bottom:10px;'>" +
      "<span id='tagger-status' style='font-size:12px;color:var(--text-muted);'></span>" +
      "</div>" +
      "<div id='tagger-ratings' style='display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px;'></div>" +
      "<div id='tagger-tags' style='display:flex;flex-wrap:wrap;gap:4px;max-height:320px;overflow-y:auto;'></div>" +
      "</div>";

    // 插入到 panel-left 区域（公共表单区下方）
    var target = document.getElementById("common-form-area");
    if (target) {
      target.parentNode.insertBefore(panel, target.nextSibling);
    } else {
      var left = document.querySelector(".panel-left");
      if (left) left.appendChild(panel);
    }

    this._bindEvents();
  }


  _bindEvents() {
    var self = this;
    var fileInput = document.getElementById("tagger-file-input");
    var threshold = document.getElementById("tagger-threshold");

    fileInput.onchange = function () { self._handleFile(this.files); };
    threshold.oninput = function () {
      self._threshold = parseFloat(this.value);
      document.getElementById("tagger-threshold-val").textContent = this.value;
      // 实时重新过滤（不改 threshold 不重新请求）
      self._renderTags();
    };
  }


  // ── 显示/隐藏 ──

  show() {
    var panel = document.getElementById("tagger-panel");
    if (panel) panel.style.display = "block";
  }

  hide() {
    var panel = document.getElementById("tagger-panel");
    if (panel) panel.style.display = "none";
  }


  // ── 文件处理 ──

  _handleFile(files) {
    if (!files || !files.length) return;
    var file = files[0];
    document.getElementById("tagger-file-name").textContent = file.name;
    document.getElementById("tagger-status").textContent = "正在分析...";

    // 重置显示
    document.getElementById("tagger-ratings").innerHTML = "";
    document.getElementById("tagger-tags").innerHTML = "";

    this._uploadAndTag(file);
  }


  async _uploadAndTag(file) {
    var self = this;
    try {
      var base64 = await this._readAsDataURL(file);
      var resp = await fetch("/api/tagger/interrogate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image: base64, threshold: 0.0 }),
      });
      if (!resp.ok) {
        var err = await resp.json().catch(function() { return { detail: resp.statusText }; });
        throw new Error(err.detail || "请求失败");
      }
      var data = await resp.json();
      self._ratings = data.ratings || {};
      self._tags = data.tags || {};
      document.getElementById("tagger-status").textContent =
        "共提取 " + Object.keys(self._tags).length + " 个标签";
      self._renderAll();
    } catch (e) {
      document.getElementById("tagger-status").textContent =
        "错误: " + e.message;
      document.getElementById("tagger-status").style.color = "#ff6b6b";
    }
  }


  _readAsDataURL(file) {
    return new Promise(function(resolve, reject) {
      var reader = new FileReader();
      reader.onload = function() { resolve(reader.result); };
      reader.onerror = function() { reject(new Error("读取图片失败")); };
      reader.readAsDataURL(file);
    });
  }


  // ── 渲染 ──

  _renderAll() {
    this._renderRatings();
    this._renderTags();
  }


  _renderRatings() {
    var container = document.getElementById("tagger-ratings");
    if (!container) return;
    var html = "";
    var labels = {
      "general": "全年龄",
      "sensitive": "敏感",
      "questionable": "可疑",
      "explicit": "明确",
    };
    for (var key in this._ratings) {
      var val = this._ratings[key];
      var label = labels[key] || key;
      var color = val > 0.5 ? "var(--accent)" : "var(--text-muted)";
      html +=
        "<span style='font-size:11px;padding:2px 8px;border:1px solid " + color +
        ";color:" + color + ";border-radius:10px;'>" +
        label + " " + (val * 100).toFixed(0) + "%</span>";
    }
    container.innerHTML = html;
  }


  _renderTags() {
    var container = document.getElementById("tagger-tags");
    if (!container) return;
    var threshold = this._threshold;
    var entries = [];
    for (var tag in this._tags) {
      if (this._tags[tag] >= threshold) {
        entries.push({ name: tag, conf: this._tags[tag] });
      }
    }
    // 按置信度降序
    entries.sort(function(a, b) { return b.conf - a.conf; });

    var html = "";
    for (var i = 0; i < entries.length; i++) {
      var e = entries[i];
      var alpha = Math.min(1, 0.4 + e.conf);
      html +=
        "<span class='tagger-tag-chip' data-tag='" + this._escAttr(e.name) +
        "' style='font-size:12px;padding:3px 8px;background:rgba(0,212,255," +
        alpha.toFixed(2) + ");color:#fff;border-radius:4px;cursor:pointer;' " +
        "title='" + this._escAttr(e.name) + ": " + (e.conf * 100).toFixed(1) +
        "%'>" + this._escHtml(e.name) + "</span>";
    }
    container.innerHTML = html;

    // 点击标签复制到剪贴板
    var chips = container.querySelectorAll(".tagger-tag-chip");
    for (var j = 0; j < chips.length; j++) {
      chips[j].onclick = function() {
        var tag = this.getAttribute("data-tag");
        this._copyTag(tag);
      }.bind(this);
    }
  }


  _copyTag(tag) {
    navigator.clipboard.writeText(tag).then(function() {
      // 短暂反馈
    }).catch(function() {
      // 静默失败
    });
  }


  _escHtml(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  _escAttr(s) {
    return s.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
}