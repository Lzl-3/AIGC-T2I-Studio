/**
 * 场景 LoRA 训练素材生产室 - 前端交互逻辑
 *
 * 职责:模板管理 -> 预览生成(单张) -> 批量生成(后台) -> 训练集标记
 * 通过 App.sceneMaterialStudio = new SceneMaterialStudioManager(app) 挂载
 */
var SceneMaterialStudioManager = (function () {
  "use strict";

  function SceneMaterialStudioManager(app) {
    this.app = app;
    this.state = {
      templates: [],
      currentTemplateId: "",
      previewUrl: "",
      previewParams: null,
      currentBatchId: "",
      batchImages: [],
      pollingTimer: null,
      generatingPreview: false,
      generatingBatch: false,
    };
    this.API_BASE = "/api/scene-material";
  }

  var P = SceneMaterialStudioManager.prototype;

  // ========== 初始化 ==========
  P.init = function () {
    this._bindEvents();
    this._loadTemplates();
  };

  P.onTabShown = function () {
    this._loadTemplates();
    this._loadBatches();
    this._loadModels();
  };

  P._loadModels = function () {
    var self = this;
    API.get("/api/models")
      .then(function (data) {
        var models = data.models || [];
        var sel = document.getElementById("sm-model");
        if (!sel) return;
        var current = sel.value;
        var opts = '<option value="">-- 选择底模 --</option>';
        models.forEach(function (m) {
          opts += '<option value="' + m.name + '">' + m.name + '</option>';
        });
        sel.innerHTML = opts;
        // restore previous selection or default to flux-2-klein
        if (current) sel.value = current;
        if (!sel.value) {
          for (var i = 0; i < sel.options.length; i++) {
            if (sel.options[i].value.indexOf("flux-2-klein") !== -1) {
              sel.selectedIndex = i;
              break;
            }
          }
        }
      })
      .catch(function () {});
  };

  // ========== 事件绑定 ==========
  P._bindEvents = function () {
    var self = this;

    // 模板操作
    var btnSave = document.getElementById("sm-btn-save-template");
    if (btnSave) btnSave.onclick = function () { self._saveTemplate(); };

    var btnDelete = document.getElementById("sm-btn-delete-template");
    if (btnDelete) btnDelete.onclick = function () { self._deleteTemplate(); };

    var selTemplate = document.getElementById("sm-template-select");
    if (selTemplate) selTemplate.onchange = function () { self._onTemplateSelect(); };

    // 预设尺寸
    var selSize = document.getElementById("sm-size-preset");
    if (selSize) selSize.onchange = function () { self._onSizePresetChange(); };

    // 预览
    var btnPreview = document.getElementById("sm-btn-preview");
    if (btnPreview) btnPreview.onclick = function () { self._generatePreview(); };

    var btnRepreview = document.getElementById("sm-btn-repreview");
    if (btnRepreview) btnRepreview.onclick = function () { self._generatePreview(); };

    // 批量
    var btnBatch = document.getElementById("sm-btn-batch");
    if (btnBatch) btnBatch.onclick = function () { self._submitBatch(); };

    // 批量列表刷新
    var btnRefreshBatches = document.getElementById("sm-btn-refresh-batches");
    if (btnRefreshBatches) btnRefreshBatches.onclick = function () { self._loadBatches(); };

    // 导出 approved
    var btnExport = document.getElementById("sm-btn-export");
    if (btnExport) btnExport.onclick = function () { self._exportApproved(); };

    // 批量详情关闭
    var btnCloseDetail = document.getElementById("sm-btn-close-detail");
    if (btnCloseDetail) btnCloseDetail.onclick = function () { self._closeBatchDetail(); };
  };

  // ========== 尺寸预设 ==========
  P._onSizePresetChange = function () {
    var sel = document.getElementById("sm-size-preset");
    if (!sel || !sel.value) return;
    var parts = sel.value.split("x");
    if (parts.length === 2) {
      var w = parseInt(parts[0]); var h = parseInt(parts[1]);
      if (w && h) {
        document.getElementById("sm-width").value = w;
        document.getElementById("sm-height").value = h;
      }
    }
  };

  // ========== 模板管理 ==========
  P._loadTemplates = function () {
    var self = this;
    API.get(this.API_BASE + "/templates")
      .then(function (data) {
        self.state.templates = data.templates || [];
        self._renderTemplateList();
      })
      .catch(function (e) { console.error("加载模板失败:", e); });
  };

  P._renderTemplateList = function () {
    var sel = document.getElementById("sm-template-select");
    if (!sel) return;
    var opts = '<option value="">-- 选择模板 --</option>';
    this.state.templates.forEach(function (t) {
      opts += '<option value="' + t.id + '">' + (t.title || t.id) + '</option>';
    });
    sel.innerHTML = opts;
  };

  P._onTemplateSelect = function () {
    var sel = document.getElementById("sm-template-select");
    if (!sel || !sel.value) return;
    var tid = sel.value;
    var self = this;

    API.get(this.API_BASE + "/template/" + tid)
      .then(function (data) {
        self._fillForm(data);
        self.state.currentTemplateId = tid;
        // 加载预览信息
        self._loadPreviewInfo(tid);
      })
      .catch(function (e) { alert("加载模板失败: " + e.message); });
  };

  P._fillForm = function (data) {
    var el = document.getElementById("sm-title");
    if (el) el.value = data.title || "";
    el = document.getElementById("sm-model");
    if (el) el.value = data.model || "";
    el = document.getElementById("sm-width");
    if (el) el.value = data.width || 1344;
    el = document.getElementById("sm-height");
    if (el) el.value = data.height || 768;
    el = document.getElementById("sm-positive");
    if (el) el.value = data.positive_prompt || "";
    el = document.getElementById("sm-negative");
    if (el) el.value = data.negative_prompt || "";
    el = document.getElementById("sm-category");
    if (el) el.value = data.scene_category || "";
    el = document.getElementById("sm-batch-count");
    if (el) el.value = data.batch_count || 10;
    // Seed 策略
    var seedMode = data.seed_mode || "random";
    var radRandom = document.getElementById("sm-seed-random");
    var radFixed = document.getElementById("sm-seed-fixed");
    var seedInput = document.getElementById("sm-seed");
    if (radRandom && radFixed) {
      radRandom.classList.toggle("selected", seedMode === "random");
      radFixed.classList.toggle("selected", seedMode === "fixed");
    }
    if (seedInput) seedInput.value = data.seed || 0;
    // 更新批量按钮文本
    this._updateBatchBtnText();
  };

  P._collectForm = function () {
    return {
      title: (document.getElementById("sm-title") || {}).value || "",
      model: (document.getElementById("sm-model") || {}).value || "",
      width: parseInt((document.getElementById("sm-width") || {}).value) || 1344,
      height: parseInt((document.getElementById("sm-height") || {}).value) || 768,
      positive_prompt: (document.getElementById("sm-positive") || {}).value || "",
      negative_prompt: (document.getElementById("sm-negative") || {}).value || "",
      scene_category: (document.getElementById("sm-category") || {}).value || "",
      seed_mode: document.getElementById("sm-seed-random") && document.getElementById("sm-seed-random").classList.contains("selected") ? "random" : "fixed",
      seed: parseInt((document.getElementById("sm-seed") || {}).value) || 0,
      steps: parseInt((document.getElementById("sm-steps") || {}).value) || 25,
      cfg: parseFloat((document.getElementById("sm-cfg") || {}).value) || 3.5,
      batch_count: parseInt((document.getElementById("sm-batch-count") || {}).value) || 10,
    };
  };

  P._saveTemplate = function () {
    var data = this._collectForm();
    if (!data.title) { alert("请输入模板标题"); return; }
    if (!data.positive_prompt) { alert("请输入正向提示词"); return; }
    data.id = this.state.currentTemplateId || "";
    var self = this;
    API.post(this.API_BASE + "/template/save", data)
      .then(function (r) {
        self.state.currentTemplateId = r.id;
        alert("模板已保存: " + r.title);
        self._loadTemplates();
      })
      .catch(function (e) { alert("保存失败: " + e.message); });
  };

  P._deleteTemplate = function () {
    var tid = this.state.currentTemplateId;
    if (!tid) { alert("请先选择一个模板"); return; }
    if (!confirm("确定删除此模板？(不会删除已生成的预览和批量数据)")) return;
    var self = this;
    API.del(this.API_BASE + "/template/" + tid)
      .then(function () {
        self.state.currentTemplateId = "";
        self._loadTemplates();
        var sel = document.getElementById("sm-template-select");
        if (sel) sel.value = "";
      })
      .catch(function (e) { alert("删除失败: " + e.message); });
  };

  // ========== 预览生成 ==========
  P._generatePreview = function () {
    if (this.state.generatingPreview) return;
    var data = this._collectForm();
    if (!data.positive_prompt) { alert("请输入正向提示词"); return; }

    var self = this;
    this.state.generatingPreview = true;
    this._setPreviewBtnState(true);
    this._showPreviewStatus("生成预览中...");

    API.post(this.API_BASE + "/preview", data)
      .then(function (r) {
        self.state.previewUrl = r.image_url;
        self.state.previewParams = data;
        self.state.generatingPreview = false;
        self._setPreviewBtnState(false);
        self._renderPreview(r);
        self._showPreviewStatus("预览完成 (seed: " + r.seed + ")");
        self._updateBatchBtnText();
      })
      .catch(function (e) {
        self.state.generatingPreview = false;
        self._setPreviewBtnState(false);
        self._showPreviewStatus("预览失败: " + e.message);
      });
  };

  P._renderPreview = function (data) {
    var container = document.getElementById("sm-preview-container");
    if (!container) return;
    var url = data.image_url;
    var meta = data.metadata || {};
    var html = '<div style="text-align:center;">';
    html += '<img src="' + url + '?t=' + Date.now() + '" style="max-width:100%;max-height:400px;border-radius:6px;border:1px solid var(--border);" alt="预览图">';
    html += '<div style="margin-top:6px;font-size:11px;color:var(--text-muted);">';
    html += 'Seed: ' + meta.seed + ' | ' + meta.width + 'x' + meta.height + ' | Steps: ' + meta.steps + ' | CFG: ' + meta.cfg;
    html += '</div></div>';
    container.innerHTML = html;
    container.style.display = "block";
  };

  P._loadPreviewInfo = function (tid) {
    var self = this;
    API.get(this.API_BASE + "/preview/" + tid)
      .then(function (data) {
        if (data && data.has_preview) {
          self.state.previewUrl = data.image_url;
          self._renderPreview({ image_url: data.image_url, metadata: data.metadata || {} });
          self._updateBatchBtnText();
        }
      })
      .catch(function () {});
  };

  P._setPreviewBtnState = function (loading) {
    var btn = document.getElementById("sm-btn-preview");
    if (btn) { btn.disabled = loading; btn.textContent = loading ? "生成中..." : "生成预览"; }
    var btn2 = document.getElementById("sm-btn-repreview");
    if (btn2) { btn2.disabled = loading; btn2.textContent = loading ? "生成中..." : "重新生成预览"; }
  };

  P._showPreviewStatus = function (msg) {
    var el = document.getElementById("sm-preview-status");
    if (el) el.textContent = msg;
  };

  // ========== 批量生成 ==========
  P._submitBatch = function () {
    if (this.state.generatingBatch) return;
    var data = this._collectForm();
    if (!data.positive_prompt) { alert("请输入正向提示词"); return; }

    var batchCount = parseInt((document.getElementById("sm-batch-count") || {}).value) || 10;
    var payload = {
      title: data.title,
      model: data.model,
      width: data.width,
      height: data.height,
      positive_prompt: data.positive_prompt,
      negative_prompt: data.negative_prompt,
      scene_category: data.scene_category,
      seed_mode: data.seed_mode,
      seed: data.seed,
      steps: data.steps,
      cfg: data.cfg,
      total: batchCount,
      template_id: this.state.currentTemplateId || "direct",
    };

    var self = this;
    this.state.generatingBatch = true;
    this._setBatchBtnState(true);

    API.post(this.API_BASE + "/batch", payload)
      .then(function (r) {
        self.state.currentBatchId = r.batch_id;
        self._showBatchStatus("批量任务已提交: " + r.batch_id + " (共 " + r.total + " 张)");
        self._startPolling(r.batch_id);
        self._loadBatches();
      })
      .catch(function (e) {
        self.state.generatingBatch = false;
        self._setBatchBtnState(false);
        alert("提交批量任务失败: " + e.message);
      });
  };

  P._startPolling = function (batchId) {
    var self = this;
    if (this.state.pollingTimer) clearInterval(this.state.pollingTimer);
    this.state.pollingTimer = setInterval(function () {
      API.get(self.API_BASE + "/batch/" + batchId + "/status")
        .then(function (s) {
          if (!s) return;
          var pct = s.total > 0 ? Math.round(s.completed / s.total * 100) : 0;
          self._showBatchStatus(
            "批量生成中: " + s.completed + "/" + s.total + " (" + pct + "%)" +
            (s.failed ? " 失败: " + s.failed : "")
          );
          if (s.status === "completed" || s.status === "failed") {
            clearInterval(self.state.pollingTimer);
            self.state.pollingTimer = null;
            self.state.generatingBatch = false;
            self._setBatchBtnState(false);
            self._showBatchStatus(
              s.status === "completed"
                ? "批量生成完成! " + s.completed + "/" + s.total
                : "批量生成失败: " + (s.error || "未知错误")
            );
            self._loadBatches();
            // 自动打开详情
            self._openBatchDetail(batchId);
          }
        })
        .catch(function () {});
    }, 3000);
  };

  P._setBatchBtnState = function (loading) {
    var btn = document.getElementById("sm-btn-batch");
    if (btn) { btn.disabled = loading; btn.textContent = loading ? "提交中..." : "使用当前参数批量生成"; }
  };

  P._showBatchStatus = function (msg) {
    var el = document.getElementById("sm-batch-status");
    if (el) el.textContent = msg;
  };

  P._updateBatchBtnText = function () {
    var btn = document.getElementById("sm-btn-batch");
    if (!btn) return;
    var cnt = (document.getElementById("sm-batch-count") || {}).value || "10";
    btn.textContent = "使用当前参数批量生成 (" + cnt + " 张)";
  };

  // ========== 批量列表 ==========
  P._loadBatches = function () {
    var self = this;
    API.get(this.API_BASE + "/batches")
      .then(function (data) {
        var list = data.batches || [];
        self._renderBatchList(list);
      })
      .catch(function (e) { console.error("加载批量列表失败:", e); });
  };

  P._renderBatchList = function (batches) {
    var container = document.getElementById("sm-batch-list");
    if (!container) return;
    if (!batches.length) {
      container.innerHTML = '<div style="color:var(--text-muted);font-size:12px;padding:8px;">暂无批量任务</div>';
      return;
    }
    var html = "";
    batches.forEach(function (b) {
      var pct = b.total > 0 ? Math.round(b.completed / b.total * 100) : 0;
      var statusColor = b.status === "completed" ? "var(--accent-color)" : (b.status === "running" || b.status === "pending" ? "#ffc832" : "#ff6b6b");
      var statusText = b.status === "completed" ? "完成" : (b.status === "running" ? "生成中" : (b.status === "pending" ? "等待中" : "失败"));
      html += '<div class="sm-batch-item" data-batch-id="' + b.batch_id + '" style="display:flex;align-items:center;justify-content:space-between;padding:8px 10px;margin:4px 0;background:var(--bg-card);border:1px solid var(--border);border-radius:6px;cursor:pointer;">';
      html += '<div style="flex:1;min-width:0;">';
      html += '<div style="font-size:13px;font-weight:600;">' + b.batch_id + '</div>';
      html += '<div style="font-size:11px;color:var(--text-muted);">' + (b.created_at || "") + '</div>';
      html += '</div>';
      html += '<div style="text-align:right;margin-left:8px;">';
      html += '<div style="font-size:13px;color:' + statusColor + ';">' + statusText + ' ' + b.completed + '/' + b.total + '</div>';
      html += '<div style="font-size:10px;color:var(--text-muted);">生成:' + (b.generated_count || 0) + ' 失败:' + (b.failed_count || 0) + '</div>';
      html += '</div></div>';
    });
    container.innerHTML = html;
    // 绑定点击事件
    var self = this;
    container.querySelectorAll(".sm-batch-item").forEach(function (el) {
      el.onclick = function () { self._openBatchDetail(this.dataset.batchId); };
    });
  };

  // ========== 批量详情 ==========
  P._openBatchDetail = function (batchId) {
    var self = this;
    this.state.currentBatchId = batchId;
    var panel = document.getElementById("sm-batch-detail");
    if (panel) panel.style.display = "block";
    var list = document.getElementById("sm-batch-list");
    if (list) list.style.display = "none";

    API.get(this.API_BASE + "/batch/" + batchId)
      .then(function (data) {
        self.state.batchImages = data.images || [];
        self._renderBatchDetail(data);
      })
      .catch(function (e) { alert("加载批量详情失败: " + e.message); });
  };

  P._closeBatchDetail = function () {
    var panel = document.getElementById("sm-batch-detail");
    if (panel) panel.style.display = "none";
    var list = document.getElementById("sm-batch-list");
    if (list) list.style.display = "block";
    this.state.currentBatchId = "";
  };

  P._renderBatchDetail = function (data) {
    var container = document.getElementById("sm-batch-detail-content");
    if (!container) return;

    var approved = 0, rejected = 0;
    (data.images || []).forEach(function (img) {
      if (img.approved) approved++;
      if (img.rejected) rejected++;
    });

    var html = '<div style="margin-bottom:10px;display:flex;justify-content:space-between;align-items:center;">';
    html += '<div>';
    html += '<strong>' + data.batch_id + '</strong>';
    html += ' <span style="font-size:12px;color:var(--text-muted);">(' + (data.generated_count || 0) + '/' + (data.total || 0) + ' 张)</span>';
    html += ' <span style="font-size:11px;color:#4ecdc4;">Approved: ' + approved + '</span>';
    html += ' <span style="font-size:11px;color:#ff6b6b;">Rejected: ' + rejected + '</span>';
    html += '</div>';
    html += '<button id="sm-btn-export-detail" style="padding:4px 10px;background:var(--accent-color);border:none;border-radius:4px;color:#000;cursor:pointer;font-size:11px;">导出 Approved</button>';
    html += '</div>';

    html += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:6px;max-height:500px;overflow-y:auto;">';
    (data.images || []).forEach(function (img) {
      var borderColor = img.approved ? "#4ecdc4" : (img.rejected ? "#ff6b6b" : "var(--border)");
      var bgOverlay = img.approved ? "rgba(78,205,196,0.12)" : (img.rejected ? "rgba(255,107,107,0.12)" : "transparent");
      html += '<div class="sm-img-card" data-stem="' + img.stem + '" style="border:2px solid ' + borderColor + ';border-radius:6px;overflow:hidden;background:' + bgOverlay + ';cursor:pointer;position:relative;">';
      html += '<img src="' + img.url + '" style="width:100%;aspect-ratio:1;object-fit:cover;" loading="lazy">';
      html += '<div style="padding:4px 6px;font-size:10px;color:var(--text-muted);display:flex;justify-content:space-between;">';
      html += '<span>' + img.filename + '</span>';
      var statusBadge = img.approved ? '[已确认]' : (img.rejected ? '[已拒绝]' : '');
      if (statusBadge) html += '<span style="color:' + (img.approved ? '#4ecdc4' : '#ff6b6b') + ';">' + statusBadge + '</span>';
      html += '</div>';
      html += '</div>';
    });
    html += '</div>';

    container.innerHTML = html;

    // 绑定导出按钮
    var self = this;
    var btnExport = document.getElementById("sm-btn-export-detail");
    if (btnExport) btnExport.onclick = function () { self._exportApproved(); };

    // 绑定图片卡片点击（切换 approved/rejected）
    container.querySelectorAll(".sm-img-card").forEach(function (card) {
      card.onclick = function (e) {
        var stem = this.dataset.stem;
        self._toggleImageStatus(stem, e.shiftKey);
      };
    });
  };

  P._toggleImageStatus = function (stem, shiftKey) {
    var bid = this.state.currentBatchId;
    if (!bid) return;
    var self = this;
    // shift+click = rejected, normal click = approved
    var status = shiftKey ? "rejected" : "approved";
    API.post(this.API_BASE + "/batch/" + bid + "/status", { stem: stem, status: status, value: true })
      .then(function () {
        self._openBatchDetail(bid);
      })
      .catch(function (e) { console.error("更新状态失败:", e); });
  };

  P._exportApproved = function () {
    var bid = this.state.currentBatchId;
    if (!bid) { alert("请先打开一个批次"); return; }
    var self = this;
    API.post(this.API_BASE + "/batch/" + bid + "/export", {})
      .then(function (r) {
        alert("已导出 " + r.count + " 张 approved 图片到:\n" + r.export_dir);
      })
      .catch(function (e) { alert("导出失败: " + e.message); });
  };

  return SceneMaterialStudioManager;
})();
