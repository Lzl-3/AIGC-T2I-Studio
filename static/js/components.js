// UI 组件模块

const UI = {
  // 题材选项
  genres: [
    { value: "xianxia", label: "玄幻修仙" },
    { value: "urban", label: "都市爱情" },
    { value: "transmigration", label: "穿越重生" },
    { value: "historical", label: "古代历史" },
    { value: "modern_era", label: "近现代" },
    { value: "supernatural", label: "悬疑灵异" },
    { value: "sci_fi", label: "末世科幻" },
    { value: "esports", label: "游戏电竞" },
  ],

  // 角度选项
  angles: [
    { value: "front_view", label: "正面" },
    { value: "side_view", label: "侧面" },
    { value: "back_view", label: "背面" },
    { value: "three_quarter_view", label: "斜侧" },
  ],

  // 表情选项
  expressions: [
    { value: "neutral", label: "中性" },
    { value: "smile", label: "微笑" },
    { value: "angry", label: "愤怒" },
    { value: "sad", label: "悲伤" },
    { value: "surprised", label: "惊讶" },
    { value: "determined", label: "坚定" },
  ],

  // 创建多选组
  createCheckboxGroup(items, selected, onChange) {
    const group = document.createElement("div");
    group.className = "checkbox-group";
    items.forEach((item) => {
      const el = document.createElement("div");
      el.className = "checkbox-item" + (selected.includes(item.value) ? " checked" : "");
      el.textContent = item.label;
      el.dataset.value = item.value;
      el.onclick = () => {
        el.classList.toggle("checked");
        onChange();
      };
      group.appendChild(el);
    });
    return group;
  },

  createRadioGroup(items, selected, onChange) {
    const group = document.createElement("div");
    group.className = "radio-group";
    items.forEach((item) => {
      const el = document.createElement("div");
      el.className = "radio-item" + (item.value === selected ? " selected" : "");
      el.textContent = item.label;
      el.dataset.value = item.value;
      el.onclick = () => {
        group.querySelectorAll(".radio-item").forEach((c) => c.classList.remove("selected"));
        el.classList.add("selected");
        onChange(item.value);
      };
      group.appendChild(el);
    });
    return group;
  },

  // 渲染图库图片项（带勾选框）
  renderGalleryItem(file) {
    const imgUrl = "/output/" + encodeURI(file.path);
    var escapedPath = file.path.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
    return (
      '<div class="gallery-item" onclick="App.viewImage(&quot;' + escapedPath + '&quot;)" data-path="' + escapedPath + '">' +
      '<div class="gallery-item-check" onclick="App.toggleGallerySelect(this, event)" title="选择/取消"></div>' +
      '<img src="' + imgUrl + '" loading="lazy" alt="' + file.filename + '">' +
      '<div class="img-name">' + file.filename + '</div>' +
      '<button class="img-delete-btn" onclick="App.deleteImage(&quot;' + escapedPath + '&quot;, event)" title="删除">×</button>' +
      '</div>'
    );
  },
};
