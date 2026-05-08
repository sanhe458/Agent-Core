document.addEventListener('DOMContentLoaded', function() {
    loadConfig();
    document.getElementById('save-config').addEventListener('click', saveConfig);
});

async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        if (!response.ok) throw new Error('加载配置失败');
        const config = await response.json();
        document.getElementById('config-json').textContent = JSON.stringify(config, null, 2);
    } catch (error) {
        document.getElementById('config-json').textContent = '加载配置失败: ' + error.message;
    }
}

async function saveConfig() {
    try {
        const configText = document.getElementById('config-json').textContent;
        const config = JSON.parse(configText);
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        if (!response.ok) throw new Error('保存配置失败');
        showToast('配置保存成功', 'success');
    } catch (error) {
        showToast('保存配置失败: ' + error.message, 'error');
    }
}
