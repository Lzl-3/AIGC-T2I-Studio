// ============================================================
// 工作流卡片管理模块 (cards.js)
// 职责：卡片 CRUD / 锁定 / 编辑器 / 挂载到 App.cards
// 金字塔原则：顶层 API → 中层操作 → 底层渲染
// ============================================================

/**
 * 工作流卡片管理器
 * 挂载点：App.cards = new CardManager()
 * 使用方式：App.cards.loadList() / App.cards.openEditor() 等
 */
class CardManager {
  constructor(app) {
    this.app = app;  // 反向引用主 App 实例
  }

  // ========== 第一层：公开 API（外部调用入口） ==========

  /** 加载卡片列表到网格和下拉框 */
  async loadList() {
    try {
      const data = await API.get("/api/cards");
      const cards = data.cards || [];
      this._renderGrid(cards);
      this._updateSelect(cards);
    } catch (e) {
      console.error("加载卡片失败:", e);
    }
  }

  /** 选择一张卡片（用于生图） */
  select(cardId) {
    const sel = document.getElementById("active-card");
    if (sel) sel.value = cardId;
    this._showCardInfo(cardId);
  }

  /** 打开卡片编辑器（cardId 为空则新建） */
  openEditor(cardId) {
    const modal = document.getElementById("card-editor-modal");
    if (!modal) return;
    modal.classList.add("show");

    document.getElementById("card-editor-id").value = cardId || "";
    this._resetEditorFields();
    this._loadModelDropdowns();

    if (cardId) {
      this._loadCardIntoEditor(cardId);
    }
  }

  /** 关闭卡片编辑器 */
  closeEditor() {
    const modal = document.getElementById("card-editor-modal");
    if (modal) modal.classList.remove("show");
  }

  /** 保存卡片（新建或更新） */
  async save() {
    const cardId = document.getElementById("card-editor-id").value;
    const data = this._gatherEditorData();
    try {
      if (cardId) {
        await API.put("/api/cards/" + cardId, data);
      } else {
        await API.post("/api/cards", data);
      }
      this.closeEditor();
      this.loadList();
    } catch (e) {
      alert("保存失败: " + e.message);
    }
  }

  /** 从编辑器锁定卡片 */
  async lockFromEditor() {
    const cardId = document.getElementById("card-editor-id").value;
    if (!cardId) { alert("请先保存卡片"); return; }
    const notes = document.getElementById("card-notes")?.value || "";
    try {
      await API.post("/api/cards/" + cardId + "/lock", { notes });
      this.closeEditor();
      this.loadList();
    } catch (e) {
      alert("锁定失败: " + e.message);
    }
  }

  /** 从卡片列表直接锁定 */
  async lockDirect(cardId) {
    if (!confirm("锁定后卡片参数不可再修改，确认锁定？")) return;
    try {
      await API.post("/api/cards/" + cardId + "/lock", {});
      this.loadList();
    } catch (e) {
      alert("锁定失败: " + e.message);
    }
  }

  /** 删除卡片 */
  async deleteCard(cardId) {
    if (!confirm("确认删除此卡片？")) return;
    try {
      await API.del("/api/cards/" + cardId);
      this.loadList();
    } catch (e) {
      alert("删除失败: " + e.message);
    }
  }

  // ========== 第二层：内部操作 ==========

  /** 选中卡片时显示信息 + 自动切换到对应标签 */
  _showCardInfo(cardId) {
    const info = document.getElementById("active-card-info");
    if (!cardId) {
      if (info) info.style.display = "none";
      return;
    }
    API.get("/api/cards/" + cardId).then((card) => {
      const lines = [];
      if (card.checkpoint) lines.push("基模: " + card.checkpoint);
      if (card.vae) lines.push("VAE: " + card.vae);
      lines.push("参数: " + card.width + "x" + card.height + " / " + card.steps + "步 / CFG " + card.cfg);
      if (card.positive_prefix) lines.push("正向前缀: " + card.positive_prefix.substring(0, 80));
      if (info) {
        info.textContent = lines.join(" | ");
        info.style.display = "block";
      }
      // 自动切换到卡片对应的标签页
      if (card.category && this.app) {
        this.app.switchTab(card.category);
      }
    }).catch(() => {
      if (info) info.style.display = "none";
    });
  }

  /** 重置编辑器所有字段为默认值 */
  _resetEditorFields() {
    const defaults = {
      "card-name": "",
      "card-desc": "",
      "card-notes": "",
      "card-positive-prefix": "",
      "card-negative-prefix": "",
      "card-width": "1024",
      "card-height": "1024",
      "card-steps": "28",
      "card-cfg": "7.0",
      "card-lora-strength": "1.0",
    };
    for (const [id, val] of Object.entries(defaults)) {
      const el = document.getElementById(id);
      if (el) el.value = val;
    }
    const statusSel = document.getElementById("card-status");
    if (statusSel) statusSel.value = "draft";
    const lockBtn = document.getElementById("btn-lock-card");
    if (lockBtn) lockBtn.style.display = "inline-block";
  }

  /** 加载 ComfyUI 模型列表到编辑器下拉框 */
  async _loadModelDropdowns() {
    try {
      const data = await API.get("/api/models");
      const models = data.models || [];
      const sel = document.getElementById("card-checkpoint");
      if (!sel) return;
      const currentVal = sel.value;
      sel.innerHTML = '<option value="">不指定</option>';
      models.forEach((m) => {
        sel.innerHTML += '<option value="' + m.name + '">' + m.name + '</option>';
      });
      if (currentVal) sel.value = currentVal;
    } catch (e) {
      console.error("加载模型列表失败:", e);
    }
  }

  /** 加载已有卡片数据到编辑器 */
  async _loadCardIntoEditor(cardId) {
    try {
      const card = await API.get("/api/cards/" + cardId);
      const fields = {
        "card-name": card.name || "",
        "card-desc": card.description || "",
        "card-category": card.category || "character",
        "card-status": card.status || "draft",
        "card-checkpoint": card.checkpoint || "",
        "card-vae": card.vae || "",
        "card-clip": card.clip_model || "",
        "card-lora": card.lora || "",
        "card-lora-strength": card.lora_strength || 1.0,
        "card-width": card.width || 1024,
        "card-height": card.height || 1024,
        "card-steps": card.steps || 28,
        "card-cfg": card.cfg || 7.0,
        "card-sampler": card.sampler_name || "",
        "card-scheduler": card.scheduler || "",
        "card-positive-prefix": card.positive_prefix || "",
        "card-negative-prefix": card.negative_prefix || "",
        "card-notes": card.notes || "",
      };
      for (const [id, val] of Object.entries(fields)) {
        const el = document.getElementById(id);
        if (el) el.value = val;
      }
      // 锁定状态下隐藏锁定按钮
      const lockBtn = document.getElementById("btn-lock-card");
      if (lockBtn) lockBtn.style.display = card.status === "locked" ? "none" : "inline-block";
    } catch (e) {
      console.error("加载卡片数据失败:", e);
    }
  }

  /** 从编辑器收集表单数据 */
  _gatherEditorData() {
    return {
      name: document.getElementById("card-name")?.value || "未命名卡片",
      description: document.getElementById("card-desc")?.value || "",
      category: document.getElementById("card-category")?.value || "character",
      status: document.getElementById("card-status")?.value || "draft",
      checkpoint: document.getElementById("card-checkpoint")?.value || "",
      vae: document.getElementById("card-vae")?.value || "",
      clip_model: document.getElementById("card-clip")?.value || "",
      width: parseInt(document.getElementById("card-width")?.value) || 1024,
      height: parseInt(document.getElementById("card-height")?.value) || 1024,
      steps: parseInt(document.getElementById("card-steps")?.value) || 28,
      cfg: parseFloat(document.getElementById("card-cfg")?.value) || 7.0,
      sampler_name: document.getElementById("card-sampler")?.value || "",
      scheduler: document.getElementById("card-scheduler")?.value || "",
      positive_prefix: document.getElementById("card-positive-prefix")?.value || "",
      negative_prefix: document.getElementById("card-negative-prefix")?.value || "",
      notes: document.getElementById("card-notes")?.value || "",
    };
  }

  // ========== 第三层：DOM 渲染 ==========

  /** 渲染卡片网格 */
  _renderGrid(cards) {
    const container = document.getElementById("card-grid");
    if (!container) return;
    if (!cards || cards.length === 0) {
      container.innerHTML = '<div class="empty-state">暂无卡片，点击"+ 新建卡片"创建</div>';
      return;
    }
    container.innerHTML = cards.map((c) => this._renderCardItem(c)).join("");
  }

  /** 渲染单个卡片 */
  _renderCardItem(card) {
    const statusLabel = { draft: "草稿", testing: "测试中", locked: "已锁定" }[card.status] || card.status;
    const modelInfo = card.checkpoint
      ? card.checkpoint.split(".")[0].substring(0, 30)
      : "未指定基模";
    const params = card.width + "x" + card.height + " / " + card.steps + "步 / CFG " + card.cfg;
    const isLocked = card.status === "locked";

    let html = "";
    html += '<div class="card-item ' + card.status + '" onclick="App.cards.select(\'' + card.card_id + '\')">';
    html += '<div class="card-header">';
    html += '<span class="card-name">' + card.name + '</span>';
    html += '<span class="card-badge ' + card.status + '">' + statusLabel + '</span>';
    html += '</div>';
    html += '<div class="card-meta">';
    html += '<span>' + params + '</span>';
    html += '<span class="card-model">' + modelInfo + '</span>';
    html += '</div>';
    if (!isLocked) {
      html += '<div class="card-actions">';
      html += '<button class="btn-xs" onclick="event.stopPropagation();App.cards.openEditor(\'' + card.card_id + '\')">编辑</button>';
      html += '<button class="btn-xs success" onclick="event.stopPropagation();App.cards.lockDirect(\'' + card.card_id + '\')">锁定</button>';
      html += '<button class="btn-xs danger" onclick="event.stopPropagation();App.cards.deleteCard(\'' + card.card_id + '\')">删除</button>';
      html += '</div>';
    }
    html += '</div>';
    return html;
  }

  /** 更新卡片下拉选择器 */
  _updateSelect(cards) {
    const sel = document.getElementById("active-card");
    if (!sel) return;
    const currentVal = sel.value;
    sel.innerHTML = '<option value="">-- 手动调参（不使用卡片） --</option>';
    cards.forEach((c) => {
      const label = c.name + (c.status === "locked" ? " [已锁定]" : c.status === "testing" ? " [测试]" : "");
      sel.innerHTML += '<option value="' + c.card_id + '">' + label + '</option>';
    });
    if (currentVal) sel.value = currentVal;
  }
}


// ============================================================
// CostumeManager - 角色装扮管理（追加模块）
// 用法: App.costumeManager = new CostumeManager(app)
// ============================================================

function CostumeManager(app) {
  this.app = app;
  this._currentCardId = null;
  this._costumeData = null;
  this._modalEl = null;
  this._initModal();
}

CostumeManager.prototype._initModal = function () {
  // 创建装扮编辑弹窗（追加到 body）
  if (document.getElementById("costume-modal")) return;

  var modal = document.createElement("div");
  modal.id = "costume-modal";
  modal.className = "costume-modal-overlay";
  modal.style.display = "none";
  modal.innerHTML =
    '<div class="costume-modal">' +
    '<div class="costume-modal-header">' +
    '<h3>装扮管理</h3>' +
    '<button class="costume-modal-close" onclick="App.costumeManager.close()">&times;</button>' +
    "</div>" +
    '<div class="costume-modal-body">' +
    // 身份区（只读）
    '<div class="costume-identity-section">' +
    '<div class="costume-section-title">身份信息（锁定）</div>' +
    '<div id="costume-identity-display" class="costume-identity-display"></div>' +
    "</div>" +
    // 装扮切换
    '<div class="costume-switch-section">' +
    '<label>当前装扮：</label>' +
    '<select id="costume-switch-select" class="costume-switch-select"></select>' +
    '<button id="costume-btn-activate" class="costume-btn-sm" onclick="App.costumeManager._activateCurrent()">激活</button>' +
    '<button id="costume-btn-delete" class="costume-btn-sm costume-btn-danger" onclick="App.costumeManager._deleteCurrent()">删除</button>' +
    "</div>" +
    // 装扮编辑区
    '<div class="costume-edit-section">' +
    '<div class="costume-section-title">编辑装扮</div>' +
    '<div class="costume-field">' +
    '<label>装扮名称</label>' +
    '<input id="costume-edit-name" type="text" class="costume-input" placeholder="如：默认道袍">' +
    "</div>" +
    '<div class="costume-field">' +
    '<label>服装</label>' +
    '<textarea id="costume-edit-outfit" class="costume-textarea" rows="2" placeholder="服装描述，英文标签最佳"></textarea>' +
    "</div>" +
    '<div class="costume-field">' +
    '<label>发型</label>' +
    '<input id="costume-edit-hairstyle" type="text" class="costume-input" placeholder="发型描述">' +
    "</div>" +
    '<div class="costume-field">' +
    '<label>配饰</label>' +
    '<input id="costume-edit-accessories" type="text" class="costume-input" placeholder="配饰描述">' +
    "</div>" +
    '<div class="costume-field">' +
    '<label>妆容</label>' +
    '<input id="costume-edit-makeup" type="text" class="costume-input" placeholder="妆容描述">' +
    "</div>" +
    '<div class="costume-field">' +
    '<label>道具</label>' +
    '<input id="costume-edit-props" type="text" class="costume-input" placeholder="道具描述">' +
    "</div>" +
    '<div class="costume-field">' +
    '<label>场景暗示</label>' +
    '<input id="costume-edit-scene" type="text" class="costume-input" placeholder="场景/环境描述">' +
    "</div>" +
    '<div class="costume-edit-actions">' +
    '<button id="costume-btn-save-new" class="costume-btn-primary" onclick="App.costumeManager._saveAsNew()">保存为新装扮</button>' +
    '<button id="costume-btn-overwrite" class="costume-btn-ghost" onclick="App.costumeManager._overwriteCurrent()">覆盖当前装扮</button>' +
    "</div>" +
    "</div>" +
    "</div>" +
    "</div>";

  document.body.appendChild(modal);
  this._modalEl = modal;

  // 切换装扮时自动加载
  document.getElementById("costume-switch-select").addEventListener("change", function () {
    App.costumeManager._onSwitchChange();
  });
};

// ---------- 公开方法 ----------

CostumeManager.prototype.open = function (cardId) {
  this._currentCardId = cardId;
  this._loadCostumes();
};

CostumeManager.prototype.close = function () {
  if (this._modalEl) this._modalEl.style.display = "none";
};

// ---------- 内部方法 ----------

CostumeManager.prototype._loadCostumes = function () {
  var self = this;
  if (!this._currentCardId) return;

  fetch("/api/cards/" + this._currentCardId + "/costumes")
    .then(function (r) { return r.json(); })
    .then(function (data) {
      self._costumeData = data;
      self._renderIdentity(data.identity);
      self._renderSwitch(data.costumes, data.active_index);
      if (self._modalEl) self._modalEl.style.display = "flex";
    })
    .catch(function (err) {
      alert("加载装扮失败: " + err.message);
    });
};

CostumeManager.prototype._renderIdentity = function (identity) {
  var el = document.getElementById("costume-identity-display");
  if (!el) return;
  var items = [];
  if (identity.name) items.push('<span class="costume-id-item"><b>角色:</b> ' + this._esc(identity.name) + "</span>");
  if (identity.gender) items.push('<span class="costume-id-item"><b>性别:</b> ' + this._esc(identity.gender) + "</span>");
  if (identity.age_range) items.push('<span class="costume-id-item"><b>年龄:</b> ' + this._esc(identity.age_range) + "</span>");
  if (identity.face_desc) items.push('<span class="costume-id-item"><b>面部:</b> ' + this._esc(identity.face_desc.substring(0, 60)) + "..." + "</span>");
  if (identity.body_type) items.push('<span class="costume-id-item"><b>体型:</b> ' + this._esc(identity.body_type) + "</span>");
  if (identity.temperament) items.push('<span class="costume-id-item"><b>气质:</b> ' + this._esc(identity.temperament) + "</span>");
  el.innerHTML = items.join("") || '<span class="costume-id-empty">未设置身份信息</span>';
};

CostumeManager.prototype._renderSwitch = function (costumes, activeIndex) {
  var sel = document.getElementById("costume-switch-select");
  if (!sel) return;
  sel.innerHTML = "";
  for (var i = 0; i < costumes.length; i++) {
    var opt = document.createElement("option");
    opt.value = i;
    opt.textContent = costumes[i].name || ("装扮 " + (i + 1));
    if (i === activeIndex) opt.selected = true;
    sel.appendChild(opt);
  }
  // 加载当前选中的装扮到编辑区
  this._loadCostumeToEditor(costumes[activeIndex], activeIndex);
};

CostumeManager.prototype._loadCostumeToEditor = function (costume, index) {
  document.getElementById("costume-edit-name").value = costume.name || "";
  document.getElementById("costume-edit-outfit").value = costume.outfit || "";
  document.getElementById("costume-edit-hairstyle").value = costume.hairstyle || "";
  document.getElementById("costume-edit-accessories").value = costume.accessories || "";
  document.getElementById("costume-edit-makeup").value = costume.makeup || "";
  document.getElementById("costume-edit-props").value = costume.props || "";
  document.getElementById("costume-edit-scene").value = costume.scene_hint || "";
  // 禁用删除按钮当只有一个装扮时
  var delBtn = document.getElementById("costume-btn-delete");
  if (delBtn && this._costumeData) {
    delBtn.disabled = this._costumeData.costumes.length <= 1;
  }
};

CostumeManager.prototype._onSwitchChange = function () {
  var sel = document.getElementById("costume-switch-select");
  if (!sel || !this._costumeData) return;
  var idx = parseInt(sel.value);
  this._loadCostumeToEditor(this._costumeData.costumes[idx], idx);
};

CostumeManager.prototype._readEditor = function () {
  return {
    name: document.getElementById("costume-edit-name").value.trim() || "新装扮",
    outfit: document.getElementById("costume-edit-outfit").value.trim(),
    hairstyle: document.getElementById("costume-edit-hairstyle").value.trim(),
    accessories: document.getElementById("costume-edit-accessories").value.trim(),
    makeup: document.getElementById("costume-edit-makeup").value.trim(),
    props: document.getElementById("costume-edit-props").value.trim(),
    scene_hint: document.getElementById("costume-edit-scene").value.trim(),
  };
};

CostumeManager.prototype._activateCurrent = function () {
  var self = this;
  var sel = document.getElementById("costume-switch-select");
  if (!sel) return;
  var idx = parseInt(sel.value);

  fetch("/api/cards/" + this._currentCardId + "/costumes/" + idx + "/activate", { method: "POST" })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      self._costumeData.active_index = data.active_index;
      alert("已激活装扮");
    })
    .catch(function (err) { alert("激活失败: " + err.message); });
};

CostumeManager.prototype._deleteCurrent = function () {
  var self = this;
  var sel = document.getElementById("costume-switch-select");
  if (!sel) return;
  var idx = parseInt(sel.value);

  if (!confirm('确定删除装扮 "' + (this._costumeData.costumes[idx].name || '') + '" ？')) return;

  fetch("/api/cards/" + this._currentCardId + "/costumes/" + idx, { method: "DELETE" })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      self._costumeData = data;
      self._renderSwitch(data.costumes, data.active_index);
    })
    .catch(function (err) { alert("删除失败: " + err.message); });
};

CostumeManager.prototype._saveAsNew = function () {
  var self = this;
  var costume = this._readEditor();

  fetch("/api/cards/" + this._currentCardId + "/costumes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(costume),
  })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      self._costumeData = data;
      self._renderSwitch(data.costumes, data.added_index);
      alert("已保存为新装扮");
    })
    .catch(function (err) { alert("保存失败: " + err.message); });
};

CostumeManager.prototype._overwriteCurrent = function () {
  var self = this;
  var sel = document.getElementById("costume-switch-select");
  if (!sel) return;
  var idx = parseInt(sel.value);

  if (!confirm("确定覆盖当前装扮？")) return;

  fetch("/api/cards/" + this._currentCardId + "/costumes/" + idx, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(this._readEditor()),
  })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      self._costumeData = data;
      self._renderSwitch(data.costumes, data.active_index);
      alert("已覆盖装扮");
    })
    .catch(function (err) { alert("覆盖失败: " + err.message); });
};

CostumeManager.prototype._esc = function (str) {
  var div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
};
