// ============================================================
// Prompt ?????? (history.js)
// ?????/??/?? Prompt ?????? App.history
// ???localStorage (key: aigc_t2i_prompt_history)
// ============================================================

/**
 * Prompt ?????
 * ????App.history = new PromptHistoryManager()
 */
class PromptHistoryManager {
  constructor() {
    this.STORAGE_KEY = "aigc_t2i_prompt_history";
    this.MAX_ITEMS = 100;
  }

  // ========== ?? API ==========

  /** ???????? */
  save(positive, negative, params) {
    var items = this._load();
    items.unshift({
      id: Date.now().toString(36) + Math.random().toString(36).substr(2, 5),
      positive: positive,
      negative: negative || "",
      params: params || {},
      time: new Date().toLocaleString("zh-CN"),
    });
    if (items.length > this.MAX_ITEMS) {
      items = items.slice(0, this.MAX_ITEMS);
    }
    this._save(items);
  }

  /** ???????? */
  getAll() {
    return this._load();
  }

  /** ?????? */
  remove(id) {
    var items = this._load().filter(function(item) { return item.id !== id; });
    this._save(items);
  }

  /** ?????? */
  clearAll() {
    localStorage.removeItem(this.STORAGE_KEY);
  }

  /** ??????????? */
  render(containerId) {
    var container = document.getElementById(containerId);
    if (!container) return;
    var items = this._load();
    if (items.length === 0) {
      container.innerHTML = '<div class="empty-state">?? Prompt ????</div>';
      return;
    }
    var html = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">' +
               '<span style="font-size:12px;color:var(--text-muted);">? ' + items.length + ' ???</span>' +
               '<button class="btn btn-sm btn-danger" onclick="App.history.clearAll();App.history.render(\'history-list\')">????</button>' +
               '</div>';
    var self = this;
    items.forEach(function(item) {
      var preview = item.positive.substring(0, 60) + (item.positive.length > 60 ? "..." : "");
      html += '<div class="history-item" style="padding:8px;margin-bottom:4px;background:var(--bg-card);border-radius:var(--radius-sm);cursor:pointer;border:1px solid var(--border);position:relative;" onclick="App.history._loadToForm(\'' + item.id + '\')">' +
              '<div style="font-size:12px;color:var(--text-primary);margin-bottom:2px;">' + self._escapeHtml(preview) + '</div>' +
              '<div style="font-size:10px;color:var(--text-muted);">' + item.time + '</div>' +
              '<button style="position:absolute;top:4px;right:4px;background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:16px;" onclick="event.stopPropagation();App.history.remove(\'' + item.id + '\');App.history.render(\'history-list\');" title="??">x</button>' +
              '</div>';
    });
    container.innerHTML = html;
  }

  // ========== ???? ==========

  /** ??????? */
  _loadToForm(id) {
    var items = this._load();
    var found = items.find(function(item) { return item.id === id; });
    if (!found) return;
    // ???????
    var posEl = document.getElementById("free-positive");
    if (posEl) posEl.value = found.positive;
    // ???????
    var negEl = document.getElementById("free-negative");
    if (negEl) negEl.value = found.negative;
    // ???????
    if (typeof App !== "undefined" && App.switchTab) {
      App.switchTab("free");
    }
    // ????
    var p = found.params;
    if (p.width) { var w = document.getElementById("img-width"); if (w) w.value = p.width; }
    if (p.height) { var h = document.getElementById("img-height"); if (h) h.value = p.height; }
    if (p.steps) { var s = document.getElementById("img-steps"); if (s) s.value = p.steps; }
    if (p.cfg) { var c = document.getElementById("img-cfg"); if (c) c.value = p.cfg; }
    if (p.model) { var m = document.getElementById("model-name"); if (m) m.value = p.model; }
    // ?????
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  /** HTML ?? */
  _escapeHtml(text) {
    var div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  /** ? localStorage ?? */
  _load() {
    try {
      var raw = localStorage.getItem(this.STORAGE_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch (e) {
      return [];
    }
  }

  /** ??? localStorage */
  _save(items) {
    try {
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(items));
    } catch (e) {
      console.error("?? Prompt ????:", e);
    }
  }
}
