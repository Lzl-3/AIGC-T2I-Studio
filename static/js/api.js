// API 封装模块
// ===== 通用 fetch 超时包装 =====
// 避免 ComfyUI 离线时前端永久挂起
const FETCH_TIMEOUT_MS = 15000;

async function fetchWithTimeout(url, options = {}, timeoutMs = FETCH_TIMEOUT_MS) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const resp = await fetch(url, { ...options, signal: controller.signal });
        return resp;
    } finally {
        clearTimeout(timer);
    }
}


const API = {
  base: "",

  async get(url) {
    const resp = await fetchWithTimeout(this.base + url);
    if (!resp.ok) throw new Error(await resp.text());
    return resp.json();
  },

  async post(url, data) {
    const resp = await fetchWithTimeout(this.base + url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(err.detail || "请求失败");
    }
    return resp.json();
  },

  
  async put(url, data) {
    const resp = await fetchWithTimeout(this.base + url, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(err.detail || "请求失败");
    }
    return resp.json();
  },

  async del(url) {
    const resp = await fetchWithTimeout(this.base + url, { method: "DELETE" });
    if (!resp.ok) throw new Error(await resp.text());
    return resp.json();
  },

  // 上传图片
  async uploadImage(file) {
    const formData = new FormData();
    formData.append("file", file);
    const resp = await fetchWithTimeout(this.base + "/api/upload", {
      method: "POST",
      body: formData,
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(err.detail || "上传失败");
    }
    return resp.json();
  },

  // 删除输出图片
  async deleteOutput(path) {
    return this.del("/api/output/delete?path=" + encodeURIComponent(path));
  },

  // SSE 连接
  connectSSE(onEvent) {
    const es = new EventSource(this.base + "/api/events");
    es.addEventListener("task_progress", (e) => onEvent("task_progress", JSON.parse(e.data)));
    es.addEventListener("task_created", (e) => onEvent("task_created", JSON.parse(e.data)));
    es.addEventListener("subtask_started", (e) => onEvent("subtask_started", JSON.parse(e.data)));
    es.addEventListener("subtask_completed", (e) => onEvent("subtask_completed", JSON.parse(e.data)));
    es.addEventListener("subtask_failed", (e) => onEvent("subtask_failed", JSON.parse(e.data)));
    es.addEventListener("subtask_progress", (e) => onEvent("subtask_progress", JSON.parse(e.data)));
    es.onerror = () => {
      console.log("SSE 连接断开，3秒后重连...");
      es.close();
      setTimeout(() => this.connectSSE(onEvent), 3000);
    };
    return es;
  },
};
