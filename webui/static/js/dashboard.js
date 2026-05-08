document.addEventListener('DOMContentLoaded', function() {
    updateStatus();
    initChart();
    setInterval(updateStatus, 5000);
});

async function updateStatus() {
    try {
        const response = await fetch('/api/statistics');
        if (!response.ok) return;
        const stats = await response.json();
        document.getElementById('service-status').textContent = '运行中';
        document.getElementById('character-count').textContent = stats.total_characters || 0;
        document.getElementById('relationship-count').textContent = stats.total_relationships || 0;
        const config = await fetch('/api/config').then(r => r.json());
        const pluginCount = Object.keys(config.plugins || {}).length;
        document.getElementById('plugin-count').textContent = pluginCount;
        document.getElementById('session-count').textContent = '0';
        document.getElementById('model-status').textContent = '正常';
    } catch (error) {
        console.error('更新状态失败:', error);
    }
}

function initChart() {
    const canvas = document.getElementById('characterStatsChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const data = [12, 19, 8, 15, 22, 10, 18];
    const labels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
    const maxVal = Math.max(...data);
    const padding = 40;
    const chartWidth = rect.width - padding * 2;
    const chartHeight = rect.height - padding * 2;
    const barWidth = chartWidth / data.length * 0.6;
    const gap = chartWidth / data.length * 0.4;

    ctx.clearRect(0, 0, rect.width, rect.height);

    data.forEach((value, i) => {
        const x = padding + i * (barWidth + gap) + gap / 2;
        const barHeight = (value / maxVal) * chartHeight;
        const y = rect.height - padding - barHeight;

        const gradient = ctx.createLinearGradient(0, y, 0, rect.height - padding);
        gradient.addColorStop(0, '#a78bfa');
        gradient.addColorStop(1, '#8b5cf6');

        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.roundRect(x, y, barWidth, barHeight, 6);
        ctx.fill();

        ctx.fillStyle = '#6b7280';
        ctx.font = '11px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(labels[i], x + barWidth / 2, rect.height - padding + 18);
        ctx.fillStyle = '#8b5cf6';
        ctx.font = 'bold 12px sans-serif';
        ctx.fillText(value, x + barWidth / 2, y - 8);
    });
}
