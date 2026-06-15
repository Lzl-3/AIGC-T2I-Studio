// ============================================================
// 图库管理模块 (gallery.js)
// 职责：图片浏览 / 筛选 / 删除 / 预览 / 分组
// 金字塔原则：顶层 API → 中层操作 → 底层渲染
// ============================================================

class GalleryManager {
  constructor(app) {
    this.app = app;
    this.selectedImages = new Set();
  }

  async load() {
    try {
      var genre = document.getElementById('gallery-filter-genre')?.value || '';
      var category = document.getElementById('gallery-filter-category')?.value || '';
      var search = document.getElementById('gallery-filter-search')?.value || '';
      var groupBy = document.getElementById('gallery-group-by')?.value || '';
      var params = [];
      if (genre) params.push('genre=' + encodeURIComponent(genre));
      if (category) params.push('category=' + encodeURIComponent(category));
      if (search) params.push('search=' + encodeURIComponent(search));
      var url = '/api/output';
      if (params.length) url += '?' + params.join('&');
      const data = await API.get(url);
      const container = document.getElementById('gallery-grid');
      if (!data.files || data.files.length === 0) {
        container.innerHTML = '<div class=empty-state>暂无生成图片</div>';
        return;
      }
      if (groupBy === 'character') {
        container.innerHTML = this._renderGroupedByCharacter(data.files);
      } else if (groupBy === 'time') {
        container.innerHTML = this._renderGroupedByTime(data.files);
      } else {
        container.innerHTML = data.files.slice(-60).map((f) => UI.renderGalleryItem(f)).join('');
      }
      this._updateSelectUI();
    } catch (e) {
      console.error('加载图库失败:', e);
    }
  }

  debounceLoad() {
    if (window._galleryDebounce) clearTimeout(window._galleryDebounce);
    window._galleryDebounce = setTimeout(() => this.load(), 300);
  }

  async viewImage(path) {
    try {
      var img = document.getElementById('modal-img');
      img.src = '/output/' + encodeURI(path);
      document.getElementById('image-modal').style.display = 'flex';
      document.getElementById('modal-label').textContent = '加载中...';
      const data = await API.get('/api/output/label?path=' + encodeURIComponent(path));
      if (data && data.content) {
        document.getElementById('modal-label').innerHTML = '<pre style=white-space:pre-wrap;font-size:13px;color:var(--text-secondary);max-height:100px;overflow-y:auto>' + data.content + '</pre>';
      }
    } catch (e) {
      console.error('查看图片失败:', e);
    }
  }

  async deleteImage(path, event) {
    if (event) event.stopPropagation();
    if (!confirm('确认删除 ' + path + '？')) return;
    try {
      await API.deleteOutput(path);
      this.load();
      this.app.refreshTasks();
    } catch (e) {
      alert('删除失败: ' + e.message);
    }
  }

  async batchDeleteSelected() {
    if (this.selectedImages.size === 0) return;
    if (!confirm('确认删除选中的 ' + this.selectedImages.size + ' 张图片？')) return;
    try {
      for (var path of this.selectedImages) {
        await API.deleteOutput(path);
      }
      this.selectedImages.clear();
      this._updateSelectUI();
      this.load();
      this.app.refreshTasks();
    } catch (e) {
      alert('批量删除失败: ' + e.message);
    }
  }

  _updateSelectUI() {
    var btn = document.getElementById('btn-clear-gallery-selection');
    if (btn) {
      btn.style.display = this.selectedImages.size > 0 ? 'inline-block' : 'none';
      btn.textContent = '删除选中(' + this.selectedImages.size + ')';
    }
  }

  toggleSelect(path) {
    if (this.selectedImages.has(path)) {
      this.selectedImages.delete(path);
    } else {
      this.selectedImages.add(path);
    }
    this._updateSelectUI();
  }

  _extractProject(path) {
    var parts = path.split('/');
    return parts.length >= 3 ? parts[parts.length - 2] : '未分类';
  }

  _formatDateGroup(mtime) {
    if (!mtime) return '未知时间';
    var d = new Date(mtime * 1000);
    var now = new Date();
    var today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    var fileDay = new Date(d.getFullYear(), d.getMonth(), d.getDate());
    var diffDays = Math.floor((today - fileDay) / 86400000);
    if (diffDays === 0) return '今天';
    if (diffDays === 1) return '昨天';
    if (diffDays < 7) return diffDays + '天前';
    var y = d.getFullYear();
    var m = String(d.getMonth() + 1).padStart(2, '0');
    var day = String(d.getDate()).padStart(2, '0');
    return y + '-' + m + '-' + day;
  }

  _renderGroupedByCharacter(files) {
    var groups = {};
    files.forEach(function(f) {
      var project = this._extractProject(f.path);
      if (!groups[project]) groups[project] = [];
      groups[project].push(f);
    }, this);
    return this._renderGroups(groups, '人物');
  }

  _renderGroupedByTime(files) {
    var groups = {};
    files.forEach(function(f) {
      var label = this._formatDateGroup(f.mtime);
      if (!groups[label]) groups[label] = [];
      groups[label].push(f);
    }, this);
    return this._renderGroups(groups, '时间');
  }

  _renderGroups(groups, labelType) {
    var keys = Object.keys(groups);
    if (labelType === '时间') {
      var order = { '今天': 0, '昨天': 1 };
      keys.sort(function(a, b) {
        var oa = order[a] !== undefined ? order[a] : 100;
        var ob = order[b] !== undefined ? order[b] : 100;
        if (oa !== ob) return oa - ob;
        return a.localeCompare(b);
      });
    } else {
      keys.sort();
    }

    var html = '';
    keys.forEach(function(key) {
      var items = groups[key];
      var itemCount = items.length;
      html += '<div class=gallery-group>';
      html += '<div class=gallery-group-header>';
      html += '<span class=gallery-group-title>' + key + '</span>';
      html += '<span class=gallery-group-count>' + itemCount + ' 张</span>';
      html += '</div>';
      html += '<div class=gallery-group-items>';
      html += items.map(function(f) { return UI.renderGalleryItem(f); }).join('');
      html += '</div>';
      html += '</div>';
    });
    return html;
  }
}
