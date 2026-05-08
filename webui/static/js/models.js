document.addEventListener('DOMContentLoaded', function() {
    loadModelList();
});

async function loadModelList() {
    try {
        const response = await fetch('/api/models');
        if (!response.ok) throw new Error('加载模型列表失败');
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
