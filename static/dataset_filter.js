/**
 * 数据集筛选器 — 前端交互模块
 * 零依赖，纯原生 JS。通过 FilterPage 类管理全部状态。
 */
var FilterPage = (function () {
  "use strict";

  const API = "http://localhost:8888";

  // ===== 工具函数 =====
  function $(id) { return document.getElementById(id); }
  function el(tag, attrs, children) {
    var e = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) { if (k === "cls") e.className = attrs[k]; else if (k === "text") e.textContent = attrs[k]; else e.setAttribute(k, attrs[k]); });
    if (children) children.forEach(function (c) { e.appendChild(typeof c === "string" ? document.createTextNode(c) : c); });
    return e;
  }

  // ===== 状态管理 =====
  var state = {
    taskId: null,
    pollTimer: null,
    resultData: null,
    tabFilter: "all",
  };

  // ===== localStorage 持久化 =====
  function loadPrefs() {
    try { return JSON.parse(localStorage.getItem("dsf_prefs") || "{}"); } catch (e) { return {}; }
  }
  function savePrefs(p) {
    try { localStorage.setItem("dsf_prefs", JSON.stringify(p)); } catch (e) {}
  }

  // ===== API 调用 =====
  async function api(path, opts) {
    var url = API + path;
    var fetchOpts = { headers: { "Content-Type": "application/json" } };
    if (opts) {
      fetchOpts.method = opts.method || "POST";
      if (opts.body) fetchOpts.body = JSON.stringify(opts.body);
    }
    var res = await fetch(url, fetchOpts);
    if (!res.ok) {
      var err = await res.json().catch(function () { return { detail: res.statusText }; });
      throw new Error(err.detail || res.statusText);
    }
    return res.json();
  }

  // ===== UI 绑定 =====
  function bindEvents() {
    // 滑块实时更新数值
    $("qualityThreshold").addEventListener("input", function () {
      $("qualityVal").textContent = parseFloat(this.value).toFixed(2);
    });
    $("hammingThreshold").addEventListener("input", function () {
      $("hammingVal").textContent = this.value;
    });

    // 均衡开关
    $("enableBalance").addEventListener("change", function () {
      $("compTargets").style.opacity = this.checked ? "1" : "0.4";
    });

    // 开始筛选
    $("btnStart").addEventListener("click", startFilter);

    // 取消
    $("btnCancel").addEventListener("click", cancelFilter);

    // 重置
    $("btnReset").addEventListener("click", resetDefaults);

    // 浏览输入目录
    $("btnBrowseInput").addEventListener("click", browseInput);

    // Tab 切换
    $("btnTabAll").addEventListener("click", function () { state.tabFilter = "all"; renderTable(); });
    $("btnTabSelected").addEventListener("click", function () { state.tabFilter = "selected"; renderTable(); });
    $("btnTabRejected").addEventListener("click", function () { state.tabFilter = "rejected"; renderTable(); });
    $("btnTabDup").addEventListener("click", function () { state.tabFilter = "duplicate"; renderTable(); });
    $("btnTabBal").addEventListener("click", function () { state.tabFilter = "cluster_removed"; renderTable(); });

    // 打开目录 / 下载报告
    $("btnOpenDir").addEventListener("click", openOutputDir);
    $("btnDownloadReport").addEventListener("click", downloadReport);

    // 输入目录回车触发浏览
    $("inputDir").addEventListener("keydown", function (e) { if (e.key === "Enter") browseInput(); });
  }

  // ===== 浏览输入目录 =====
  async function browseInput() {
    var dir = $("inputDir").value.trim();
    if (!dir) return;
    try {
      var data = await api("/api/filter/browse?dir_path=" + encodeURIComponent(dir));
      var images = data.items.filter(function (i) { return i.type === "image"; });
      alert("目录: " + data.path + "\n图片: " + images.length + " 张\n子目录: " + (data.count - images.length) + " 个");
    } catch (e) {
      alert("浏览失败: " + e.message);
    }
  }

  // ===== 开始筛选 =====
  async function startFilter() {
    var inputDir = $("inputDir").value.trim();
    if (!inputDir) { alert("请输入素材目录"); return; }

    var outputDir = $("outputDir").value.trim();
    var qualityThreshold = parseFloat($("qualityThreshold").value);
    var hammingThreshold = parseInt($("hammingThreshold").value);
    var enableBalance = $("enableBalance").checked;

    // 收集构图比例
    var targets = null;
    if (enableBalance) {
      targets = {};
      var total = 0;
      var keys = ["全身","半身","胸像","特写","环境人像"];
      var ids = ["comp_full","comp_half","comp_bust","comp_closeup","comp_env"];
      ids.forEach(function (id, i) {
        targets[keys[i]] = parseInt($(id).value) / 100;
        total += parseInt($(id).value);
      });
      if (total !== 100) {
        alert("构图比例之和必须为 100%，当前: " + total + "%");
        return;
      }
    }

    // 保存偏好
    savePrefs({ inputDir: inputDir, outputDir: outputDir, qualityThreshold: qualityThreshold, hammingThreshold: hammingThreshold, enableBalance: enableBalance, targets: targets });

    // 锁定 UI
    setUIState("running");

    try {
      var body = { input_dir: inputDir, output_dir: outputDir, quality_threshold: qualityThreshold, hamming_threshold: hammingThreshold };
      if (targets) body.composition_targets = targets;
      else body.composition_targets = null; // 跳过均衡

      var res = await api("/api/filter/start", { method: "POST", body: body });
      state.taskId = res.task_id;
      startPolling();
    } catch (e) {
      showError("启动失败: " + e.message);
      setUIState("idle");
    }
  }

  // ===== 轮询进度 =====
  function startPolling() {
    if (state.pollTimer) clearInterval(state.pollTimer);
    state.pollTimer = setInterval(pollStatus, 800);
  }

  async function pollStatus() {
    if (!state.taskId) return;
    try {
      var s = await api("/api/filter/status/" + state.taskId);
      updateProgress(s);
      if (s.status === "done" || s.status === "cancelled" || s.status === "error") {
        clearInterval(state.pollTimer);
        state.pollTimer = null;
        if (s.status === "done") {
          await loadResult();
          setUIState("done");
        } else if (s.status === "error") {
          showError(s.error || "未知错误");
          setUIState("idle");
        } else {
          setUIState("idle");
        }
      }
    } catch (e) {
      clearInterval(state.pollTimer);
      state.pollTimer = null;
      showError("轮询失败: " + e.message);
      setUIState("idle");
    }
  }

  function updateProgress(s) {
    $("progressPanel").style.display = "block";
    var pct = s.total > 0 ? Math.round((s.current / s.total) * 100) : 0;
    $("progressFill").style.width = pct + "%";
    $("progressText").textContent = "阶段: " + stageLabel(s.stage) + " | " + s.current + "/" + s.total + " | " + s.elapsed_seconds + "s";

    // 阶段标记
    var stages = [
      { key: "scanning", label: "扫描" },
      { key: "quality", label: "质量" },
      { key: "dedup", label: "去重" },
      { key: "balance", label: "均衡" },
      { key: "copying", label: "复制" },
      { key: "finished", label: "完成" },
    ];
    var stageOrder = ["scanning","quality","dedup","balance","copying","finished"];
    var currentIdx = stageOrder.indexOf(s.stage);
    var list = $("stageList");
    list.innerHTML = "";
    stages.forEach(function (st, i) {
      var cls = "stage-item";
      if (i < currentIdx) cls += " done";
      else if (i === currentIdx) cls += " active";
      if (s.status === "error" && i === currentIdx) cls += " error";
      list.appendChild(el("span", { cls: cls, text: st.label }));
    });
  }

  function stageLabel(s) {
    var map = { scanning: "扫描中", quality: "质量筛选", dedup: "去重", balance: "构图均衡", copying: "复制文件", finished: "完成" };
    return map[s] || s;
  }

  // ===== 取消 =====
  async function cancelFilter() {
    if (!state.taskId) return;
    try {
      await api("/api/filter/cancel/" + state.taskId, { method: "POST" });
      clearInterval(state.pollTimer);
      state.pollTimer = null;
      $("progressText").textContent = "已取消";
      setUIState("idle");
    } catch (e) {
      alert("取消失败: " + e.message);
    }
  }

  // ===== 加载结果 =====
  async function loadResult() {
    var data = await api("/api/filter/result/" + state.taskId);
    state.resultData = data;
    renderStats(data);
    renderTable();
    $("resultPanel").style.display = "block";
  }

  function renderStats(data) {
    var grid = $("statGrid");
    grid.innerHTML = "";
    var items = [
      { cls: "total", num: data.input_count, label: "输入" },
      { cls: "selected", num: data.selected_count, label: "保留" },
      { cls: "reject", num: data.rejected_count, label: "质量剔除" },
      { cls: "dup", num: data.duplicate_count, label: "重复剔除" },
      { cls: "balance", num: data.cluster_removed_count, label: "构图挤出" },
    ];
    items.forEach(function (it) {
      grid.appendChild(el("div", { cls: "stat-card " + it.cls }, [
        el("div", { cls: "num", text: it.num }),
        el("div", { cls: "label", text: it.label }),
      ]));
    });
  }

  function renderTable() {
    var data = state.resultData;
    if (!data) return;
    var images = data.images;
    if (state.tabFilter !== "all") {
      images = images.filter(function (img) { return img.stage === state.tabFilter; });
    }

    var tbody = $("resultTable");
    tbody.innerHTML = "";
    images.forEach(function (img) {
      var tagCls = "tag-ok";
      var tagText = "保留";
      if (img.stage === "rejected") { tagCls = "tag-rej"; tagText = "剔除"; }
      else if (img.stage === "duplicate") { tagCls = "tag-dup"; tagText = "重复"; }
      else if (img.stage === "cluster_removed") { tagCls = "tag-bal"; tagText = "挤出"; }

      tbody.appendChild(el("tr", {}, [
        el("td", { text: img.filename }),
        el("td", { text: img.quality_score !== null ? img.quality_score.toFixed(4) : "-" }),
        el("td", { text: img.composition || "-" }),
        el("td", { text: img.composition_source || "-" }),
        el("td", {}, [el("span", { cls: "tag " + tagCls, text: tagText })]),
        el("td", { text: img.reason || "-" }),
      ]));
    });
  }

  // ===== 打开目录 / 下载 =====
  function openOutputDir() {
    if (state.resultData && state.resultData.output_dir) {
      alert("输出目录: " + state.resultData.output_dir + "\n请在文件管理器中手动打开。");
    }
  }

  function downloadReport() {
    if (!state.resultData) return;
    var blob = new Blob([JSON.stringify(state.resultData, null, 2)], { type: "application/json" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "report.json";
    a.click();
    URL.revokeObjectURL(a.href);
  }

  // ===== 错误 =====
  function showError(msg) {
    $("errorMsg").style.display = "block";
    $("errorMsg").textContent = msg;
    $("progressPanel").style.display = "block";
    setTimeout(function () { $("errorMsg").style.display = "none"; }, 8000);
  }

  // ===== UI 状态切换 =====
  function setUIState(s) {
    if (s === "running") {
      $("btnStart").disabled = true;
      $("btnCancel").disabled = false;
      $("inputDir").disabled = true;
      $("outputDir").disabled = true;
      $("qualityThreshold").disabled = true;
      $("hammingThreshold").disabled = true;
      $("enableBalance").disabled = true;
      $("progressPanel").style.display = "block";
      $("errorMsg").style.display = "none";
    } else {
      $("btnStart").disabled = false;
      $("btnCancel").disabled = true;
      $("inputDir").disabled = false;
      $("outputDir").disabled = false;
      $("qualityThreshold").disabled = false;
      $("hammingThreshold").disabled = false;
      $("enableBalance").disabled = false;
    }
  }

  // ===== 重置 =====
  function resetDefaults() {
    $("inputDir").value = "output/character/_flat_玄幻修仙";
    $("outputDir").value = "";
    $("qualityThreshold").value = "0.15";
    $("qualityVal").textContent = "0.15";
    $("hammingThreshold").value = "5";
    $("hammingVal").textContent = "5";
    $("enableBalance").checked = true;
    $("compTargets").style.opacity = "1";
    $("comp_full").value = "45";
    $("comp_half").value = "25";
    $("comp_bust").value = "15";
    $("comp_closeup").value = "10";
    $("comp_env").value = "5";
    $("resultPanel").style.display = "none";
    $("progressPanel").style.display = "none";
    $("errorMsg").style.display = "none";
    state.taskId = null;
    state.resultData = null;
    state.tabFilter = "all";
    setUIState("idle");
    savePrefs({});
  }

  // ===== 初始化 =====
  function init() {
    bindEvents();
    var prefs = loadPrefs();
    if (prefs.inputDir) $("inputDir").value = prefs.inputDir;
    if (prefs.outputDir) $("outputDir").value = prefs.outputDir;
    if (prefs.qualityThreshold !== undefined) { $("qualityThreshold").value = prefs.qualityThreshold; $("qualityVal").textContent = parseFloat(prefs.qualityThreshold).toFixed(2); }
    if (prefs.hammingThreshold !== undefined) { $("hammingThreshold").value = prefs.hammingThreshold; $("hammingVal").textContent = prefs.hammingThreshold; }
    if (prefs.enableBalance !== undefined) {
      $("enableBalance").checked = prefs.enableBalance;
      $("compTargets").style.opacity = prefs.enableBalance ? "1" : "0.4";
    }
    if (prefs.targets) {
      var map = { "全身":"comp_full","半身":"comp_half","胸像":"comp_bust","特写":"comp_closeup","环境人像":"comp_env" };
      Object.keys(prefs.targets).forEach(function (k) {
        if (map[k]) $(map[k]).value = Math.round(prefs.targets[k] * 100);
      });
    }

    // 检查服务状态
    fetch(API + "/api/health")
      .then(function (r) { return r.json(); })
      .then(function () { $("svcStatus").innerHTML = "&#x25CF; 就绪"; })
      .catch(function () { $("svcStatus").innerHTML = "&#x25CB; 离线"; });
  }

  return { init: init };
})();

document.addEventListener("DOMContentLoaded", FilterPage.init);