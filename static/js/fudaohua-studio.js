// -*- coding: utf-8 -*-
// 服道化素材工作室 - 统一前端模块
// 服装/道具/妆容训练 + 模板管理 + 预览图 + 批量生成
// v2.0: 统一模板方案 — 三个子标签全部改为「自由输入+模板管理」模式

class FudaohuaStudio {
    constructor(app) {
        this.app = app;
        this.activeType = 'costume';  // costume | prop | makeup
        this.templates = {};          // { costume: [...], prop: [...], makeup: [...] }
        this.models = [];             // 底模列表
        this.total = 200;
        this.batchSize = 10;
        this.baseModel = 'flux2_klein_9b';
        this.previewTaskId = null;
        this.batchTaskIds = [];
        this.generating = false;
        this._init();
    }

    // ===== 初始化 =====
    _init() {
        this._bindSubTabs();
        this._bindScaleButtons();
        this._bindControls();
        this._bindButtons();
        this._bindTemplateButtons();
        this.loadTemplates();
    }

    _bindSubTabs() {
        var self = this;
        var tabs = document.querySelectorAll('#fdh-subtab-bar .fdh-subtab');
        tabs.forEach(function(tab) {
            tab.addEventListener('click', function() {
                var type = tab.dataset.type;
                if (type) self._switchTab(type);
            });
        });
    }

    _bindScaleButtons() {
        var self = this;
        var btns = document.querySelectorAll('#fdh-scale-btns .fdh-scale-btn');
        btns.forEach(function(btn) {
            btn.addEventListener('click', function() {
                var count = parseInt(btn.dataset.count);
                if (count) {
                    self.total = count;
                    var slider = document.getElementById('fdh-total-slider');
                    var display = document.getElementById('fdh-total-display');
                    if (slider) slider.value = count;
                    if (display) display.textContent = count;
                    self._updateScaleActive();
                }
            });
        });
        var slider = document.getElementById('fdh-total-slider');
        var display = document.getElementById('fdh-total-display');
        if (slider && display) {
            slider.addEventListener('input', function() {
                self.total = parseInt(slider.value);
                display.textContent = self.total;
                self._updateScaleActive();
            });
        }
    }

    _bindControls() {
        var self = this;
        var modelSel = document.getElementById('fdh-base-model');
        if (modelSel) modelSel.addEventListener('change', function() { self.baseModel = modelSel.value; });
        var batchSel = document.getElementById('fdh-batch-size');
        if (batchSel) batchSel.addEventListener('change', function() { self.batchSize = parseInt(batchSel.value); });
    }

    _bindButtons() {
        var self = this;
        var btnPreview = document.getElementById('btn-fdh-preview');
        var btnGenerate = document.getElementById('btn-fdh-generate');
        var btnStop = document.getElementById('btn-fdh-stop');
        var btnRePreview = document.getElementById('btn-fdh-repreview');
        var btnPromptPreview = document.getElementById('btn-fdh-prompt-preview');
        var btnExport = document.getElementById('btn-fdh-export');
        var btnQuality = document.getElementById('btn-fdh-quality');
        var btnDedup = document.getElementById('btn-fdh-dedup');
        var btnFilter = document.getElementById('btn-fdh-filter');

        if (btnPreview) btnPreview.addEventListener('click', function() { self.previewImage(); });
        if (btnGenerate) btnGenerate.addEventListener('click', function() { self.startGenerate(); });
        if (btnStop) btnStop.addEventListener('click', function() { self.stopGenerate(); });
        if (btnRePreview) btnRePreview.addEventListener('click', function() { self.rePreview(); });
        if (btnPromptPreview) btnPromptPreview.addEventListener('click', function() { self.showPromptPreview(); });
        if (btnExport) btnExport.addEventListener('click', function() { self.exportDataset(); });
        if (btnQuality) btnQuality.addEventListener('click', function() { self.qualityScore(); });
        if (btnDedup) btnDedup.addEventListener('click', function() { self.autoDedup(); });
        if (btnFilter) btnFilter.addEventListener('click', function() { self.filterLowQuality(); });
    }

    _bindTemplateButtons() {
        var self = this;
        var btnSave = document.getElementById('btn-fdh-save-template');
        var btnDelete = document.getElementById('btn-fdh-delete-template');
        if (btnSave) btnSave.addEventListener('click', function() { self._saveTemplate(); });
        if (btnDelete) btnDelete.addEventListener('click', function() { self._deleteTemplate(); });
    }

    _updateScaleActive() {
        var self = this;
        var btns = document.querySelectorAll('#fdh-scale-btns .fdh-scale-btn');
        btns.forEach(function(b) {
            b.classList.toggle('active', parseInt(b.dataset.count) === self.total);
        });
    }

    // ===== 子标签切换 =====
    _switchTab(type) {
        this.activeType = type;
        this.previewTaskId = null;
        // 更新 UI 激活状态
        var tabs = document.querySelectorAll('#fdh-subtab-bar .fdh-subtab');
        tabs.forEach(function(t) { t.classList.toggle('active', t.dataset.type === type); });
        // 更新标题
        var label = document.getElementById('fdh-preset-label');
        var names = { costume: '服装训练', prop: '道具训练', makeup: '妆容训练' };
        if (label) label.textContent = names[type] || '训练配置';
        // 清空输入框
        var titleEl = document.getElementById('fdh-template-title');
        var posEl = document.getElementById('fdh-positive');
        var negEl = document.getElementById('fdh-negative');
        if (titleEl) titleEl.value = '';
        if (posEl) posEl.value = '';
        if (negEl) negEl.value = '';
        // 刷新模板标签
        this._refreshTemplateTags();
        this._updateStatus('已切换: ' + (names[type] || type));
    }

    // ===== 模板管理 =====
    async loadTemplates() {
        try {
            var res = await API.get('/api/fudaohua/presets');
            this.models = res._models || [];
            this._populateModels();
            // 加载模板列表
            await this._loadTemplateList();
        } catch (e) {
            console.error('加载预设失败:', e);
            this._updateStatus('加载预设失败');
        }
    }

    async _loadTemplateList() {
        try {
            var res = await API.get('/api/fudaohua/templates?preset_type=' + this.activeType);
            this.templates[this.activeType] = res.templates || [];
            this._refreshTemplateTags();
        } catch (e) {
            console.error('加载模板列表失败:', e);
            this.templates[this.activeType] = [];
            this._refreshTemplateTags();
        }
    }

    _refreshTemplateTags() {
        var container = document.getElementById('fdh-template-tags');
        if (!container) return;
        var list = this.templates[this.activeType] || [];
        var self = this;
        var html = '';
        for (var i = 0; i < list.length; i++) {
            var t = list[i];
            html += '<button class="fdh-template-tag" data-title="' + this._escapeAttr(t.title) + '" style="padding:4px 10px;background:var(--bg-card);border:1px solid var(--border);border-radius:4px;color:var(--text-secondary);cursor:pointer;font-size:12px;white-space:nowrap;">' + this._escapeHtml(t.title) + '</button>';
        }
        html += '<button class="fdh-template-tag fdh-template-new" data-title="__new__" style="padding:4px 10px;background:transparent;border:1px dashed var(--border);border-radius:4px;color:var(--text-muted);cursor:pointer;font-size:12px;">+ 新建</button>';
        container.innerHTML = html;

        // 绑定点击事件
        var tags = container.querySelectorAll('.fdh-template-tag');
        tags.forEach(function(tag) {
            tag.addEventListener('click', function() {
                var title = tag.dataset.title;
                if (title === '__new__') {
                    self._clearInputs();
                } else {
                    self._selectTemplate(title);
                }
            });
        });
    }

    _selectTemplate(title) {
        var list = this.templates[this.activeType] || [];
        for (var i = 0; i < list.length; i++) {
            if (list[i].title === title) {
                var t = list[i];
                var titleEl = document.getElementById('fdh-template-title');
                var posEl = document.getElementById('fdh-positive');
                var negEl = document.getElementById('fdh-negative');
                if (titleEl) titleEl.value = t.title;
                if (posEl) posEl.value = t.positive_template || '';
                if (negEl) negEl.value = t.negative_prompt || '';
                this._updateStatus('已选: ' + t.title);
                return;
            }
        }
    }

    _clearInputs() {
        var titleEl = document.getElementById('fdh-template-title');
        var posEl = document.getElementById('fdh-positive');
        var negEl = document.getElementById('fdh-negative');
        if (titleEl) titleEl.value = '';
        if (posEl) posEl.value = '';
        if (negEl) negEl.value = '';
        this._updateStatus('自由输入模式');
    }

    async _saveTemplate() {
        var title = document.getElementById('fdh-template-title').value.trim();
        var pos = document.getElementById('fdh-positive').value.trim();
        var neg = document.getElementById('fdh-negative').value.trim();

        if (!title) { alert('请输入模板标题'); return; }
        if (!pos) { alert('请输入正面提示词'); return; }

        try {
            var res = await API.post('/api/fudaohua/template/save', {
                type: this.activeType,
                title: title,
                positive_template: pos,
                negative_prompt: neg,
            });
            this._updateStatus('模板已保存: ' + title);
            await this._loadTemplateList();
        } catch (e) {
            console.error('保存模板失败:', e);
            alert('保存失败: ' + (e.message || '未知错误'));
        }
    }

    async _deleteTemplate() {
        var title = document.getElementById('fdh-template-title').value.trim();
        if (!title) { alert('请先选择或输入要删除的模板标题'); return; }
        if (!confirm('确定删除模板「' + title + '」？此操作不可撤销。')) return;

        try {
            var encoded = encodeURIComponent(title);
            await API.del('/api/fudaohua/template/' + this.activeType + '/' + encoded);
            this._clearInputs();
            this._updateStatus('模板已删除: ' + title);
            await this._loadTemplateList();
        } catch (e) {
            console.error('删除模板失败:', e);
            alert('删除失败: ' + (e.message || '未知错误'));
        }
    }

    // ===== 底模加载 =====
    _populateModels() {
        var sel = document.getElementById('fdh-base-model');
        if (!sel) return;
        sel.innerHTML = '';
        var self = this;
        this.models.forEach(function(m) {
            var opt = document.createElement('option');
            opt.value = m.key;
            opt.textContent = m.name;
            if (m.key === self.baseModel) opt.selected = true;
            sel.appendChild(opt);
        });
    }

    // ===== 预览 =====
    async previewImage() {
        var pos = document.getElementById('fdh-positive').value.trim();
        if (!pos) { alert('请输入正面提示词'); return; }
        this._updateStatus('正在生成预览图...');
        try {
            var body = this._buildRequest();
            var res = await API.post('/api/fudaohua/preview', body);
            this.previewTaskId = res.task_id;
            this._updateStatus('预览任务已提交: ' + (res.preset_name || ''));
            this._pollPreviewResult();
        } catch (e) {
            console.error('预览失败:', e);
            this._updateStatus('预览失败: ' + e.message);
        }
    }

    async rePreview() {
        await this.previewImage();
    }

    _pollPreviewResult() {
        var self = this;
        var attempts = 0;
        var maxAttempts = 60;
        var interval = setInterval(async function() {
            attempts++;
            if (attempts > maxAttempts) {
                clearInterval(interval);
                self._updateStatus('预览超时');
                return;
            }
            try {
                var tasks = await API.get('/api/tasks');
                var found = false;
                for (var i = 0; i < tasks.length; i++) {
                    if (tasks[i].id === self.previewTaskId) {
                        found = true;
                        if (tasks[i].status === 'completed') {
                            clearInterval(interval);
                            self._updateStatus('预览完成');
                            self._showPreviewImage(tasks[i]);
                        } else if (tasks[i].status === 'failed') {
                            clearInterval(interval);
                            self._updateStatus('预览失败');
                        }
                        break;
                    }
                }
            } catch (e) {
                clearInterval(interval);
            }
        }, 2000);
    }

    _showPreviewImage(task) {
        var container = document.getElementById('fdh-preview-area');
        if (!container) return;
        if (task.output_path) {
            container.innerHTML = '<img src="' + task.output_path + '" style="max-width:100%;border-radius:8px;">';
        }
    }

    // ===== Prompt 预览 =====
    async showPromptPreview() {
        var pos = document.getElementById('fdh-positive').value.trim();
        if (!pos) { alert('请输入正面提示词'); return; }
        this._updateStatus('正在加载 Prompt 预览...');
        try {
            var body = this._buildRequest();
            body.preview_count = Math.min(this.total, 30);
            var res = await API.post('/api/fudaohua/prompts', body);
            var list = document.getElementById('fdh-prompt-list');
            var section = document.getElementById('fdh-prompt-section');
            if (list && res.prompts) {
                list.innerHTML = '';
                var self = this;
                res.prompts.forEach(function(p, i) {
                    var div = document.createElement('div');
                    div.className = 'fdh-prompt-item';
                    div.innerHTML = '<span class="fdh-prompt-idx">#' + (i + 1) + '</span> ' + self._escapeHtml(p);
                    list.appendChild(div);
                });
            }
            if (section) section.style.display = '';
            this._updateStatus('Prompt 预览已加载 (' + (res.total || 0) + ' 条)');
        } catch (e) {
            console.error('Prompt预览失败:', e);
            this._updateStatus('Prompt 预览失败');
        }
    }

    // ===== 生成 =====
    async startGenerate() {
        var pos = document.getElementById('fdh-positive').value.trim();
        if (!pos) { alert('请输入正面提示词'); return; }
        this.generating = true;
        this._updateStatus('正在提交生成任务...');
        var btnGen = document.getElementById('btn-fdh-generate');
        var btnStop = document.getElementById('btn-fdh-stop');
        if (btnGen) btnGen.style.display = 'none';
        if (btnStop) btnStop.style.display = '';

        try {
            var body = this._buildRequest();
            var res = await API.post('/api/fudaohua/generate', body);
            this.batchTaskIds = res.task_ids || [];
            this._updateStatus('已提交 ' + this.batchTaskIds.length + ' 批次，共 ' + (res.total_images || 0) + ' 张');
        } catch (e) {
            console.error('生成失败:', e);
            this._updateStatus('生成失败: ' + e.message);
        } finally {
            this.generating = false;
            if (btnGen) btnGen.style.display = '';
            if (btnStop) btnStop.style.display = 'none';
        }
    }

    async stopGenerate() {
        try {
            await API.post('/api/fudaohua/stop', { task_group_id: this.previewTaskId || '', task_ids: this.batchTaskIds });
            this.generating = false;
            this._updateStatus('已停止');
            var btnGen = document.getElementById('btn-fdh-generate');
            var btnStop = document.getElementById('btn-fdh-stop');
            if (btnGen) btnGen.style.display = '';
            if (btnStop) btnStop.style.display = 'none';
        } catch (e) {
            this._updateStatus('停止失败');
        }
    }

    async exportDataset() {
        var pos = document.getElementById('fdh-positive').value.trim();
        if (!pos) { alert('请输入正面提示词'); return; }
        this._updateStatus('正在导出...');
        try {
            var res = await API.post('/api/fudaohua/export', this._buildRequest());
            this._updateStatus('导出完成: ' + JSON.stringify(res));
        } catch (e) {
            this._updateStatus('导出失败');
        }
    }

    async qualityScore() {
        this._updateStatus('正在评分...');
        try {
            var res = await API.post('/api/fudaohua/quality', this._buildRequest());
            this._updateStatus('评分完成: ' + JSON.stringify(res).substring(0, 100));
        } catch (e) {
            this._updateStatus('评分失败');
        }
    }

    async autoDedup() {
        this._updateStatus('正在去重...');
        try {
            var res = await API.post('/api/fudaohua/dedup', this._buildRequest());
            this._updateStatus('去重完成');
        } catch (e) {
            this._updateStatus('去重失败');
        }
    }

    async filterLowQuality() {
        var threshold = parseFloat(prompt('过滤阈值 (0.3-0.9):', '0.5'));
        if (isNaN(threshold)) return;
        this._updateStatus('正在过滤...');
        try {
            var body = this._buildRequest();
            body.threshold = threshold;
            var res = await API.post('/api/fudaohua/filter', body);
            this._updateStatus('过滤完成: 保留 ' + (res.kept || 0) + ' 张');
        } catch (e) {
            this._updateStatus('过滤失败');
        }
    }

    // ===== 构建请求 =====
    _buildRequest() {
        var seedVal = document.getElementById('fdh-seed') ? document.getElementById('fdh-seed').value : '';
        return {
            type: this.activeType,
            title: document.getElementById('fdh-template-title') ? document.getElementById('fdh-template-title').value : '',
            positive_template: document.getElementById('fdh-positive') ? document.getElementById('fdh-positive').value : '',
            negative_prompt: document.getElementById('fdh-negative') ? document.getElementById('fdh-negative').value : '',
            total: this.total,
            batch_size: this.batchSize,
            base_model: this.baseModel,
            seed: seedVal ? parseInt(seedVal) : null,
        };
    }

    // ===== 工具方法 =====
    _updateStatus(msg) {
        var el = document.getElementById('fdh-status');
        if (el) el.textContent = msg;
        console.log('[FDH]', msg);
    }

    _escapeHtml(text) {
        var div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    _escapeAttr(text) {
        return text.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }
}

// 挂载到全局
window.FudaohuaStudio = FudaohuaStudio;
