document.addEventListener('DOMContentLoaded', function() {
    // 加载配置
    loadConfig();
    
    // 加载插件列表
    loadPluginList();
    
    // 加载模型列表
    loadModelList();
    
    // 启动日志流
    startLogStream();
    
    // 保存配置按钮
    document.getElementById('save-config').addEventListener('click', saveConfig);
    
    // 定期更新状态
    setInterval(updateStatus, 5000);
});

// 加载配置
async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        if (!response.ok) {
            throw new Error('加载配置失败');
        }
        const config = await response.json();
        document.getElementById('config-json').textContent = JSON.stringify(config, null, 2);
    } catch (error) {
        document.getElementById('config-json').textContent = '加载配置失败: ' + error.message;
    }
}

// 保存配置
async function saveConfig() {
    try {
        const configText = document.getElementById('config-json').textContent;
        const config = JSON.parse(configText);
        
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
        
        if (!response.ok) {
            throw new Error('保存配置失败');
        }
        
        alert('配置保存成功！');
    } catch (error) {
        alert('保存配置失败: ' + error.message);
    }
}

// 加载插件列表
async function loadPluginList() {
    try {
        const response = await fetch('/api/config');
        if (!response.ok) {
            throw new Error('加载插件列表失败');
        }
        const config = await response.json();
        const plugins = config.plugins || {};
        
        const pluginList = document.getElementById('plugin-list');
        let html = '';
        
        for (const [name, pluginConfig] of Object.entries(plugins)) {
            html += `
                <div class="plugin-item">
                    <h4>${name}</h4>
                    <p>状态: ${pluginConfig.enabled ? '启用' : '禁用'}</p>
                    <button onclick="editPluginConfig('${name}')">编辑配置</button>
                </div>
            `;
        }
        
        pluginList.innerHTML = html;
    } catch (error) {
        document.getElementById('plugin-list').innerHTML = '加载插件列表失败: ' + error.message;
    }
}

// 加载模型列表
async function loadModelList() {
    try {
        const response = await fetch('/api/models');
        if (!response.ok) {
            throw new Error('加载模型列表失败');
        }
        const models = await response.json();
        
        const modelList = document.getElementById('model-list');
        let html = '';
        
        for (const [provider, providerInfo] of Object.entries(models)) {
            html += `
                <div class="model-item">
                    <h4>${provider}</h4>
                    <p>状态: ${providerInfo.status}</p>
                    <div class="models">
                        ${Object.entries(providerInfo.models || {}).map(([role, model]) => `
                            <div>${role}: ${model}</div>
                        `).join('')}
                    </div>
                </div>
            `;
        }
        
        modelList.innerHTML = html;
    } catch (error) {
        document.getElementById('model-list').innerHTML = '加载模型列表失败: ' + error.message;
    }
}

// 启动日志流
function startLogStream() {
    const logsContent = document.getElementById('logs-content');
    
    try {
        const ws = new WebSocket(`ws://${window.location.host}/ws/logs`);
        
        ws.onmessage = function(event) {
            logsContent.innerHTML += event.data + '\n';
            logsContent.scrollTop = logsContent.scrollHeight;
        };
        
        ws.onerror = function(error) {
            logsContent.innerHTML += '日志流连接失败: ' + error.message + '\n';
        };
    } catch (error) {
        logsContent.innerHTML += '日志流启动失败: ' + error.message + '\n';
    }
}

// 更新状态
async function updateStatus() {
    try {
        const response = await fetch('/api/config');
        if (!response.ok) {
            return;
        }
        const config = await response.json();
        
        // 更新服务状态
        document.getElementById('service-status').textContent = '运行中';
        
        // 更新插件数量
        const pluginCount = Object.keys(config.plugins || {}).length;
        document.getElementById('plugin-count').textContent = pluginCount;
        
        // 其他状态更新
        document.getElementById('session-count').textContent = '0';
        document.getElementById('model-status').textContent = '正常';
    } catch (error) {
        console.error('更新状态失败:', error);
    }
}

// 编辑插件配置
function editPluginConfig(pluginName) {
    alert('编辑插件配置功能待实现');
}