document.addEventListener('DOMContentLoaded', function() {
    startLogStream();
});

function startLogStream() {
    const logsContent = document.getElementById('logs-content');
    try {
        const ws = new WebSocket(`ws://${window.location.host}/ws/logs`);
        ws.onmessage = function(event) {
            logsContent.innerHTML += event.data + '\n';
            logsContent.scrollTop = logsContent.scrollHeight;
        };
        ws.onerror = function(error) {
            logsContent.innerHTML += '日志流连接失败\n';
        };
    } catch (error) {
        logsContent.innerHTML += '日志流启动失败: ' + error.message + '\n';
    }
}
