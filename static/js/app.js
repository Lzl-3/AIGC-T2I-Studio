// AIGC T2I Studio - 主应用逻辑

const App = {
  currentTab: "character",
  sseConn: null,
  activeTasks: {},
  uploadedImage: null,
  selectedStyleTags: [],
  cards: null,  // CardManager 实例，由 cards.js 提供

  init() {
    this.bindEvents();
    this.initRadioButtons();
    this.checkHealth();
    // 读取千问工作室带回的数据
    this._loadQwenFillData();

    this.loadCharacterPresets();
    this.connectSSE();
    this.switchTab("character");
    this.refreshTasks();
    // 图库管理器（必须在 load 前初始化）
    this.gallery = new GalleryManager(this);
    this.gallery.load();
    this.initImg2Img();
    this.initKeyboardShortcuts();
    this.initAngleExpressionGroups();  // 填充角度/表情多选按钮
    // 初始化卡片管理器（cards.js 中的 CardManager）
    this.cards = new CardManager(this);
    this.cards.loadList();
    // Prompt 工作室 + 训练素材 管理器
    this.history = new PromptHistoryManager();
    this.stylePalette = new StylePaletteManager(this);
    this.stylePalette.init();
    this.stylePalette.onChange = (tags) => { this.selectedStyleTags = tags; };
            this.materialStudio = new MaterialStudioManager(this);
    this.materialStudio.init();
    this.fudaohuaStudio = new FudaohuaStudio(this);
    this.tagger = new WD14TaggerManager(this);
    this.tagger.init();
    this.sceneMaterialStudio = new SceneMaterialStudioManager(this);
    this.sceneMaterialStudio.init();

            setInterval(() => this.refreshTasks(), 5000);
    setInterval(() => this.gallery.load(), 30000);
  },

  bindEvents() {
    document.getElementById("tab-character").onclick = () => this.switchTab("character");
    document.getElementById("tab-scene").onclick = () => this.switchTab("scene");
    document.getElementById("tab-costume").onclick = () => this.switchTab("costume");
    document.getElementById("tab-img2img").onclick = () => this.switchTab("img2img");
    document.getElementById("tab-cards").onclick = () => this.switchTab("cards");
    var elHistory = document.getElementById("tab-history");
    if (elHistory) elHistory.onclick = () => this.switchTab("history");
    var elMS = document.getElementById("tab-material-studio");
    if (elMS) elMS.onclick = () => this.switchTab("material-studio");
    var elCS = document.getElementById("tab-costume-studio");
    if (elCS) elCS.onclick = () => this.switchTab("costume-studio");
    var elTagger = document.getElementById("tab-tagger");
    if (elTagger) elTagger.onclick = () => this.switchTab("tagger");
    var elSM = document.getElementById("tab-scene-material");
    if (elSM) elSM.onclick = () => this.switchTab("scene-material");

            document.getElementById("tab-free").onclick = () => this.switchTab("free");
    document.getElementById("btn-generate").onclick = () => this.submitTask();
    document.getElementById("btn-cancel").onclick = () => this.cancelTask();
    document.getElementById("modal-close").onclick = () => this.closeModal();
    document.getElementById("image-modal").onclick = (e) => {
      if (e.target === document.getElementById("image-modal")) this.closeModal();
    };
    // Gallery filter events
    document.getElementById("gallery-filter-genre").onchange = () => this.gallery.load();
    document.getElementById("gallery-filter-category").onchange = () => this.gallery.load();
    document.getElementById("gallery-group-by").onchange = () => this.gallery.load();
    document.getElementById("gallery-filter-search").oninput = () => this.debounceLoadGallery();
    document.getElementById("btn-refresh-gallery").onclick = () => this.gallery.load();
    document.getElementById("btn-clear-gallery-selection").onclick = () => this.batchDeleteSelected();
    // Card events (delegated to CardManager)
    document.getElementById("btn-new-card").onclick = () => this.cards.openEditor();
    document.getElementById("card-editor-close").onclick = () => this.cards.closeEditor();
    document.getElementById("btn-save-card").onclick = () => this.cards.save();
    document.getElementById("btn-lock-card").onclick = () => this.cards.lockFromEditor();
    document.getElementById("active-card").onchange = () => {
      var val = document.getElementById("active-card").value;
      if (this.cards) this.cards._showCardInfo(val);
    };
    document.getElementById("card-editor-modal").onclick = (e) => {
      if (e.target === document.getElementById("card-editor-modal")) this.cards.closeEditor();
    };
    // ?????????
    var batchToggle = document.getElementById("batch-mode-toggle");
    if (batchToggle) batchToggle.onchange = () => this.toggleBatchMode();
    // Denoising slider
    var ds = document.getElementById("denoising-strength");
    if (ds) ds.oninput = function() { document.getElementById("denoising-value").textContent = parseFloat(this.value).toFixed(2); };
    window._currentTaskId = null;
    window._galleryDebounce = null;
  },

  initRadioButtons() {
    document.querySelectorAll(".radio-item").forEach((el) => {
      el.onclick = function() {
        const group = this.parentElement;
        group.querySelectorAll(".radio-item").forEach((c) => c.classList.remove("selected"));
        this.classList.add("selected");
      };
    });
  },

  initKeyboardShortcuts() {
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") this.closeModal();
      if (e.ctrlKey && e.key === "Enter") { e.preventDefault(); this.submitTask(); }
      var tabs = ["character", "scene", "costume", "img2img", "cards", "free", "history"];
      for (var i = 0; i < tabs.length; i++) {
        if (e.ctrlKey && e.key === String(i + 1)) { e.preventDefault(); this.switchTab(tabs[i]); }
      }
    });
  },

  initImg2Img() {
    const dropzone = document.getElementById("img2img-dropzone");
    const fileInput = document.getElementById("img2img-file-input");
    if (!dropzone) return;
    dropzone.onclick = () => fileInput.click();
    dropzone.ondragover = (e) => { e.preventDefault(); dropzone.classList.add("dragover"); };
    dropzone.ondragleave = () => dropzone.classList.remove("dragover");
    dropzone.ondrop = (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
      const file = e.dataTransfer.files[0];
      if (file) this.handleImageFile(file);
    };
    fileInput.onchange = () => {
      const file = fileInput.files[0];
      if (file) this.handleImageFile(file);
    };
  },

  async handleImageFile(file) {
    try {
      document.getElementById("img2img-placeholder").textContent = "上传中...";
      const result = await API.uploadImage(file);
      this.uploadedImage = result;
      var preview = document.getElementById("img2img-preview");
      var placeholder = document.getElementById("img2img-placeholder");
      preview.style.display = "block";
      placeholder.style.display = "none";
      preview.innerHTML = '<img src="' + result.url + '" style="max-width:100%;max-height:200px;border-radius:4px;"><br><small>' + result.filename + '</small>';
    } catch (e) {
      alert("上传失败: " + e.message);
      document.getElementById("img2img-placeholder").textContent = "拖拽图片到此处 或 点击上传";
    }
  },

  switchTab(tab) {
    this.currentTab = tab;
    document.querySelectorAll(".sidebar-btn").forEach((b) => b.classList.remove("active"));
    var tabBtn = document.getElementById("tab-" + tab);
    if (tabBtn) tabBtn.classList.add("active");
    var panels = {
      character: "params-character", scene: "params-scene", costume: "params-costume",
      img2img: "params-img2img", cards: "params-cards", history: "params-history", free: "params-free",
      tagger: "tagger-panel",
      "material-studio": "params-material-studio",
      "costume-studio": "params-fudaohua-studio",
      "scene-material": "params-scene-material",
    };
    for (var key in panels) {
      var el = document.getElementById(panels[key]);
      if (el) el.style.display = (key === tab) ? "block" : "none";
    }
    // 角色参数面板在 character/free/cards 时显示
    var charPanel = document.getElementById("params-character");
    if (charPanel) charPanel.style.display = (tab === "character") ? "block" : "none";
    // 角度/表情在自由模式隐藏
    var angleGroup = document.getElementById("angle-group");
    var exprGroup = document.getElementById("expression-group");
    if (angleGroup) angleGroup.style.display = tab === "free" ? "none" : "";
    if (exprGroup) exprGroup.style.display = tab === "free" ? "none" : "";
    // 调优/模板模式：隐藏通用表单控件，只显示模块面板
    var specialTabs = ["material-studio", "costume-studio", "tagger", "scene-material"];
    var showControls = specialTabs.indexOf(tab) === -1;
    var commonArea = document.getElementById("common-form-area");
    var generateArea = document.getElementById("generate-area");
    if (commonArea) commonArea.style.display = showControls ? "" : "none";
    if (generateArea) generateArea.style.display = showControls ? "" : "none";
    // ??? Prompt ?????????
    // ??????? Tab ????

    if (tab === "tagger") {
      if (this.tagger) this.tagger.show();
    } else if (this.tagger) {
      this.tagger.hide();
    }
    if (tab === "costume-studio" && this.fudaohuaStudio) {
      this.fudaohuaStudio.loadPresets();
    }
    if (tab === "scene-material" && this.sceneMaterialStudio) {
      this.sceneMaterialStudio.onTabShown();
    }
    if (tab === "history" && this.history) {
      this.history.render("history-list");
    }
  },

  async checkHealth() {
    try {
      const data = await API.get("/api/health");
      const el = document.getElementById("comfyui-status");
      var banner = document.getElementById("comfyui-offline-banner");
      if (data.comfyui_connected) {
        el.textContent = "ComfyUI 已连接 (" + data.comfyui_url + ")";
        el.className = "comfyui-status online";
        if (banner) banner.style.display = "none";
      } else {
        el.textContent = "ComfyUI 未连接";
        el.className = "comfyui-status offline";
        if (banner) banner.style.display = "block";
      }
      this.loadModels();  // 不 await，避免 ComfyUI 离线时阻塞健康检查
    } catch (e) {
      console.error("健康检查失败:", e);
      const el = document.getElementById("comfyui-status");
      if (el) { el.textContent = "ComfyUI 未连接（网络错误）"; el.className = "comfyui-status offline"; }
      var banner = document.getElementById("comfyui-offline-banner");
      if (banner) banner.style.display = "block";
    }
  },

  // 关闭图片预览弹窗（ESC / 关闭按钮 / 点击背景）
  closeModal() {
    var modal = document.getElementById("image-modal");
    if (modal) modal.style.display = "none";
  },

  // 查看大图（由 gallery item onclick 委托到 GalleryManager）
  viewImage(path) {
    if (this.gallery) this.gallery.viewImage(path);
  },

  // 切换图库图片选中状态（由 gallery item checkbox onclick 委托）
  toggleGallerySelect(el, event) {
    if (event) event.stopPropagation();
    var path = el.parentElement?.getAttribute("data-path");
    if (path && this.gallery) this.gallery.toggleSelect(path);
  },

  async loadModels() {
    try {
      const data = await API.get("/api/models");
      var models = data.models || [];
      var sel = document.getElementById("model-name");
      sel.innerHTML = '<option value="">自动选择...</option>';
      models.forEach(function(m) { sel.innerHTML += '<option value="' + m.name + '">' + m.name + '</option>'; });
      if (models.length > 0 && !sel.value) sel.value = models[0].name;
    } catch (e) {
      console.error("加载模型列表失败:", e);
    }
  },


  // ?????????????
  initAngleExpressionGroups() {
    var angleGroup = document.getElementById("angle-group");
    if (angleGroup) {
      angleGroup.innerHTML = "";
      UI.angles.forEach(function(item) {
        var el = document.createElement("div");
        el.className = "checkbox-item" + (item.value === "front_view" ? " checked" : "");
        el.textContent = item.label;
        el.dataset.value = item.value;
        el.onclick = function() { el.classList.toggle("checked"); };
        angleGroup.appendChild(el);
      });
    }
    var expGroup = document.getElementById("expression-group");
    if (expGroup) {
      expGroup.innerHTML = "";
      UI.expressions.forEach(function(item) {
        var el = document.createElement("div");
        el.className = "checkbox-item" + (item.value === "neutral" ? " checked" : "");
        el.textContent = item.label;
        el.dataset.value = item.value;
        el.onclick = function() { el.classList.toggle("checked"); };
        expGroup.appendChild(el);
      });
    }
  },
  getSelectedValues(groupId) {
    var selected = [];
    document.querySelectorAll("#" + groupId + " .checkbox-item.checked").forEach(function(el) {
      selected.push(el.dataset.value);
    });
    return selected;
  },

  async submitTask() {
    // ?????????
    var batchToggle = document.getElementById("batch-mode-toggle");
    if (batchToggle && batchToggle.checked && this.currentTab === "free") {
      return this.submitBatchTask();
    }
    try {
      var tab = this.currentTab;
      var category = tab === "free" ? "character" : tab;
      var isFree = tab === "free";

      var modelName = document.getElementById("model-name").value;
      var width = parseInt(document.getElementById("img-width").value) || 1024;
      var height = parseInt(document.getElementById("img-height").value) || 1024;
      var steps = parseInt(document.getElementById("img-steps").value) || 40;
      var cfg = parseFloat(document.getElementById("img-cfg").value) || 7.0;
      var sampler = document.getElementById("img-sampler")?.value || "";
      var scheduler = document.getElementById("img-scheduler")?.value || "";

      var roleSelect = document.getElementById("role-name");
      var roleName = (roleSelect.value === "__custom__")
        ? (document.getElementById("role-name-custom").value || "custom")
        : (roleSelect.value || "");

      var payload = {
        category: category,
        genre: document.getElementById("genre").value,
        project_name: document.getElementById("project-name").value || "untitled",
        role_name: roleName,
        character_gender: document.getElementById('character-gender')?.value || 'female',
        lighting: document.getElementById("lighting").value,
        seed_mode: document.querySelector(".radio-item.selected")?.dataset?.value || "random",
        seed: parseInt(document.getElementById("seed-value").value) || 0,
        model_name: modelName,
        width: width, height: height, steps: steps, cfg: cfg,
        sampler_name: sampler, scheduler: scheduler,
        batch_count: 1,
        angles: this.getSelectedValues("angle-group"),
        expressions: this.getSelectedValues("expression-group"),
        composition: document.getElementById("composition")?.value || "full_body",
        character_sheet_mode: document.getElementById("sheet-mode-toggle")?.classList.contains("checked") || false,
        style_tags: (this.selectedStyleTags || []).join(", "),
      };

      if (isFree) {
        payload.free_positive = document.getElementById("free-positive")?.value || "";
        payload.free_negative = document.getElementById("free-negative")?.value || "";
      }
      if (tab === "scene") {
        payload.scene_type = document.getElementById("scene-type")?.value || "";
        payload.time_of_day = document.getElementById("scene-time")?.value || "";
        payload.atmosphere = document.getElementById("scene-atmosphere")?.value || "";
      }
      if (tab === "costume") {
        payload.item_type = document.getElementById("item-type")?.value || "";
        payload.material = document.getElementById("item-material")?.value || "";
        payload.item_style = document.getElementById("item-style")?.value || "";
      }
      if (tab === "img2img") {
        if (!this.uploadedImage) { alert("请先上传一张参考图"); return; }
        payload.image_filename = this.uploadedImage.filename;
        payload.img2img_prompt = document.getElementById("img2img-prompt")?.value?.trim() || "";
        payload.denoising_strength = parseFloat(document.getElementById("denoising-strength")?.value) || 0.4;
      }

      var el = document.getElementById("btn-generate");
      el.disabled = true;
      el.textContent = "提交中...";

      var cardId = document.getElementById("active-card")?.value || "";
      var url = cardId ? "/api/generate?card_id=" + encodeURIComponent(cardId) : "/api/generate";
      const result = await API.post(url, payload);
      window._currentTaskId = result.task_id;
      el.textContent = "已提交 #" + result.task_id;
      setTimeout(function() { el.disabled = false; el.textContent = "开始生成"; }, 2000);
    } catch (e) {
      alert("生成失败: " + e.message);
      var btn = document.getElementById("btn-generate");
      btn.disabled = false;
      btn.textContent = "开始生成";
    }
  },

  async cancelTask() {
    if (!window._currentTaskId) { alert("没有正在进行的任务"); return; }
    try {
      await API.del("/api/tasks/" + window._currentTaskId);
      window._currentTaskId = null;
    } catch (e) { alert("取消失败: " + e.message); }
  },

  connectSSE() {
    this.sseConn = API.connectSSE((type, data) => {
      if (type === "task_progress") this.handleTaskProgress(data);
      else if (type === "task_created") this.handleTaskCreated(data);
      else if (type === "subtask_completed") this.handleSubtaskCompleted(data);
      else if (type === "subtask_failed") this.handleSubtaskFailed(data);
      else if (type === "subtask_started") this.handleSubtaskStarted(data);
    });
  },

  handleTaskProgress(data) {
    var el = document.querySelector('.task-item[data-task-id="' + data.task_id + '"]');
    if (!el) return this.refreshTasks();
    var pct = data.total > 0 ? Math.round((data.completed / data.total) * 100) : 0;
    var barEl = el.querySelector(".task-progress-bar");
    if (barEl) barEl.style.width = pct + "%";
    var statusEl = el.querySelector(".task-status");
    if (statusEl) { statusEl.textContent = data.status; statusEl.className = "task-status " + data.status; }
    var infoEl = el.querySelector(".task-info-text");
    if (infoEl) infoEl.textContent = data.completed + "/" + data.total + " 已完成";
  },

  handleTaskCreated(data) { this.refreshTasks(); },
  handleSubtaskStarted(data) { this.refreshTasks(); },
  handleSubtaskCompleted(data) { this.gallery.load(); this.refreshTasks(); },
  handleSubtaskFailed(data) { this.refreshTasks(); },
  handleSubtaskProgress(data) {
    // 更新任务列表中对应项的进度信息
    var items = document.querySelectorAll('.task-item');
    items.forEach(function(item) {
      var subEl = item.querySelector('[data-subtask-id="' + data.subtask_id + '"]');
      if (subEl) {
        var elapsed = Math.round(data.elapsed || 0);
        var timeout = data.timeout || 600;
        subEl.style.color = 'var(--text-muted)';
        subEl.textContent = '进度: 已等待 ' + elapsed + 's / ' + timeout + 's';
      }
    });
  },

  async refreshTasks() {
    try {
      const data = await API.get("/api/tasks");
      const container = document.getElementById("task-list");
      var tasks = data.tasks || [];
      if (tasks.length === 0) { container.innerHTML = '<div class="empty-state">暂无任务</div>'; return; }
      container.innerHTML = tasks.slice(0, 20).map((t) => {
        var pct = t.total_subtasks > 0 ? Math.round((t.completed_subtasks / t.total_subtasks) * 100) : 0;
        var statusLabel = { pending: "等待中", running: "运行中", completed: "已完成", failed: "失败", cancelled: "已取消" }[t.status] || t.status;
        return (
          '<div class="task-item" data-task-id="' + t.task_id + '">' +
          '<div class="task-header">' +
          '<span class="task-name">' + t.project_name + ' <span class="task-id">#' + t.task_id + '</span></span>' +
          '<span class="task-status ' + t.status + '">' + statusLabel + '</span>' +
          (t.status === "pending" || t.status === "running" ? '<button class="btn btn-sm btn-danger task-stop-btn" onclick="App.cancelTaskById(\x27' + t.task_id + '\x27)" title="停止生成">停止</button>' : '') +
          '</div>' +
          '<div class="task-info-text" style="font-size:12px;color:var(--text-muted)">' + t.category + ' / ' + t.genre + ' · ' + t.completed_subtasks + '/' + t.total_subtasks + '</div>' +
          '<div class="task-progress"><div class="task-progress-bar" style="width:' + pct + '%"></div></div>' +
          '</div>'
        );
      }).join("");
    } catch (e) { console.error("刷新任务列表失败:", e); }
  },

  // ===== 图库桥接（实际逻辑在 gallery.js） =====
  loadGallery() { return this.gallery.load(); },
  debounceLoadGallery() { return this.gallery.debounceLoad(); },
  updateGallerySelectUI() { return this.gallery._updateSelectUI(); },
  async deleteImage(path, event) { return this.gallery.deleteImage(path, event); },
  async batchDeleteSelected() { return this.gallery.batchDeleteSelected(); },
  async viewImage(path) { return this.gallery.viewImage(path); },

  async cancelTaskById(taskId) {
    try {
      await API.del("/api/tasks/" + taskId);
      this.refreshTasks();
    } catch (e) { alert("取消失败: " + e.message); }
  },

  async loadCharacterPresets() {
    try {
      const data = await API.get("/api/character-presets");
      const select = document.getElementById("role-name");
      const presets = data.presets || [];
      let options = '<option value="">-- 自由角色 --</option>';
      presets.forEach(function(p) { options += '<option value="' + p.name + '">' + p.name + '</option>'; });
      options += '<option value="__custom__">输入自定义角色...</option>';
      select.innerHTML = options;
      select.onchange = () => this.onPresetChange(presets);
    } catch (e) {
      console.error("加载角色预设失败:", e);
      document.getElementById("role-name").innerHTML = '<option value="">-- 加载失败 --</option>';
    }
  },

  onPresetChange(presets) {
    const select = document.getElementById("role-name");
    const customInput = document.getElementById("role-name-custom");
    const infoDiv = document.getElementById("preset-info");
    const infoContent = document.getElementById("preset-info-content");
    if (select.value === "__custom__") { customInput.style.display = "block"; infoDiv.style.display = "none"; }
    else {
      customInput.style.display = "none";
      const preset = presets.find(function(p) { return p.name === select.value; });
      if (preset) {
        infoDiv.style.display = "block";
        // ????????????
        if (preset.gender) {
          var genderSelect = document.getElementById("character-gender");
          if (genderSelect) genderSelect.value = preset.gender;
        }
        infoContent.innerHTML =
          "<b>触发词:</b> " + preset.trigger_word + "<br>" +
          "<b>脸部:</b> " + preset.face + "<br>" +
          "<b>发型:</b> " + preset.hair + "<br>" +
          "<b>服装:</b> " + preset.clothing + "<br>" +
          "<b>武器:</b> " + preset.weapon + "<br>" +
          "<b>风格:</b> " + preset.style;
      } else if (select.value === "") { infoDiv.style.display = "none"; customInput.style.display = "none"; }
    }
  },
  /** 读取千问工作室带回的数据并填入表单 */
  _loadQwenFillData() {
    try {
      var raw = localStorage.getItem("qwen_fill_data");
      if (!raw) return;
      localStorage.removeItem("qwen_fill_data");
      var data = JSON.parse(raw);
      if (data.positive) {
        var el = document.getElementById("free-positive");
        if (el) el.value = data.positive;
      }
      if (data.negative) {
        var el = document.getElementById("free-negative");
        if (el) el.value = data.negative;
      }
      if (data.width) {
        var el = document.getElementById("img-width");
        if (el) el.value = data.width;
      }
      if (data.height) {
        var el = document.getElementById("img-height");
        if (el) el.value = data.height;
      }
    } catch(e) {}
  },

};

// ==== Character Manager ====

App.loadFreeCharacters = async function() {
  try {
    var data = await API.get("/api/characters/list");
    var chars = data.characters || [];
    var sel = document.getElementById("free-char-select");
    if (sel) {
      var opts = '<option value="">-- 不使用角色配置 --</option>';
      chars.forEach(function(ch) { opts += "<option value='" + ch.name + "'>" + ch.name + "</option>"; });
      sel.innerHTML = opts;
    }
    var list = document.getElementById("free-char-list");
    if (list) {
      if (chars.length === 0) {
        list.innerHTML = '<span style="color:var(--text-muted);">无已保存角色</span>';
      } else {
        var h = "";
        chars.forEach(function(ch) {
          h += '<div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid var(--border);">';
          h += "<span>" + ch.name + "</span>";
          h += "<div>";
          h += "<button onclick='App.selectFreeChar(" + JSON.stringify(ch.name) + ")' style='padding:2px 8px;background:var(--bg-input);border:1px solid var(--border);border-radius:3px;color:var(--accent);cursor:pointer;font-size:11px;margin-right:4px;'>选择</button>";
          h += "<button onclick='App.deleteFreeChar(" + JSON.stringify(ch.name) + ")' style='padding:2px 8px;background:var(--bg-input);border:1px solid var(--border);border-radius:3px;color:var(--danger);cursor:pointer;font-size:11px;'>删除</button>";
          h += "</div></div>";
        });
        list.innerHTML = h;
      }
    }
    await App.loadCharacterPresets();
  } catch(e) { console.error(e); }
};

App.createFreeChar = async function() {
  var inp = document.getElementById("free-char-name");
  var name = inp ? inp.value.trim() : "";
  if (!name) { alert("请输入角色名称"); return; }
  var pos = document.getElementById("free-positive")?.value || "";
  var neg = document.getElementById("free-negative")?.value || "";
  var gender = document.getElementById("free-char-gender")?.value || "";
  var age = document.getElementById("free-char-age")?.value || "";
  var height = document.getElementById("free-char-height")?.value.trim() || "";
  var metadata = {};
  if (gender) metadata.gender = gender;
  if (age) metadata.age = age;
  if (height) metadata.height = height;
  try {
    await API.post("/api/characters/create", {name:name, positive:pos, negative:neg, metadata:metadata});
    inp.value = "";
    await App.loadFreeCharacters();
  } catch(e) { alert("创建失败: " + (e.message||e)); }
};

App.deleteFreeChar = async function(name) {
  if (!confirm("确定删除 " + name + " ?\n可在 characters/.trash 恢复")) return;
  try {
    await API.del("/api/characters/" + encodeURIComponent(name));
    await App.loadFreeCharacters();
    var sel = document.getElementById("free-char-select");
    if (sel && sel.value === name) sel.value = "";
  } catch(e) { alert("删除失败: " + (e.message||e)); }
};

App.selectFreeChar = function(name) {
  var sel = document.getElementById("free-char-select");
  if (!sel) return;
  for (var i=0; i<sel.options.length; i++) {
    if (sel.options[i].value === name) { sel.selectedIndex = i; break; }
  }
};

App._onFreeCharSelectChange = function() {
  var name = document.getElementById("free-char-select")?.value;
  if (!name) return;
  API.get("/api/characters/list").then(function(data) {
    var chars = data.characters || [];
    var found = chars.find(function(c) { return c.name === name; });
    if (found) {
      var pos = document.getElementById("free-positive");
      var neg = document.getElementById("free-negative");
      if (pos) pos.value = found.positive || "";
      if (neg) neg.value = found.negative || "";
      var meta = found.metadata || {};
      var genderEl = document.getElementById("free-char-gender");
      var ageEl = document.getElementById("free-char-age");
      var heightEl = document.getElementById("free-char-height");
      if (genderEl) genderEl.value = meta.gender || "";
      if (ageEl) ageEl.value = meta.age || "";
      if (heightEl) heightEl.value = meta.height || "";
    }
  });
};

App._initCharManager = function() {
  var btn = document.getElementById("btn-create-char");
  if (btn) btn.onclick = function() { App.createFreeChar(); };
  var sel = document.getElementById("free-char-select");
  if (sel) sel.onchange = App._onFreeCharSelectChange;
  App.loadFreeCharacters();
};

var _origInit = App.init;
App.init = function() {
  _origInit.call(this);
  setTimeout(function() { App._initCharManager(); }, 300);
};


document.addEventListener("DOMContentLoaded", () => App.init());
