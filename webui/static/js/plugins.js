document.addEventListener('DOMContentLoaded', function() {
    loadPluginList();
});

async function loadPluginList() {
    try {
        const response = await fetch('/api/config');
        if (!response.ok) throw new Error('加载插件列表失败');
        const config = await response.json();
        const plugins = config.plugins || {};
        const pluginList = document.getElementById('plugin-list');
        let html = '';
        for (const [name, pluginConfig] of Object.entries(plugins)) {
            html += `
                <div class="plugin-item">
                    <h4>${name}</h4>
                    <p>状态: ${pluginConfig.enabled ? '启用' : '禁用'}</p>
                    <button class="btn btn-secondary" onclick="editPluginConfig('${name}')">编辑配置</button>
                </div>
            `;
        }
        pluginList.innerHTML = html;
    } catch (error) {
        document.getElementById('plugin-list').innerHTML = '加载插件列表失败: ' + error.message;
    }
}

function editPluginConfig(pluginName) {
    alert('编辑插件配置功能待实现');
}
