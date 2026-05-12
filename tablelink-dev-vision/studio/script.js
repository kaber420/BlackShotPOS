const CONFIG = {
    napkin: {
        img: 'assets/napkin_holder.png',
        label: 'Napkin Holder - Table Proto V1',
        view: { width: 320, height: 240, top: '232px', left: '161px' }
    },
    robot: {
        img: 'assets/robot.png',
        label: 'Desktop Robot - Social Bot A1',
        view: { width: 320, height: 240, top: '215px', left: '139px' }
    },
    kiosk: {
        img: 'assets/kiosk.png',
        label: 'Service Kiosk - Floor Stand K3',
        view: { width: 320, height: 240, top: '82px', left: '141px' }
    }
};

let currentMockup = 'napkin';
let socket = null;

// UI Elements
const logContent = document.getElementById('log-content');
const sdlContainer = document.getElementById('sdl-container');
const mockupView = document.getElementById('mockup-view');
const deviceLabel = document.getElementById('device-label');
const valX = document.getElementById('val-x');
const valY = document.getElementById('val-y');

function addLog(msg, type = 'system') {
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
    logContent.appendChild(entry);
    logContent.scrollTop = logContent.scrollHeight;
}

function updateMockup(type) {
    currentMockup = type;
    const cfg = CONFIG[type];
    
    mockupView.style.backgroundImage = `url(${cfg.img})`;
    deviceLabel.textContent = cfg.label;
    
    // Update placeholder position
    sdlContainer.style.width = cfg.view.width + 'px';
    sdlContainer.style.height = cfg.view.height + 'px';
    sdlContainer.style.top = cfg.view.top;
    sdlContainer.style.left = cfg.view.left;

    // Notify bridge about position change
    const rect = sdlContainer.getBoundingClientRect();
    valX.textContent = Math.round(window.screenX + rect.left);
    valY.textContent = Math.round(window.screenY + rect.top);

    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
            type: 'ALIGN',
            x: Math.round(window.screenX + rect.left),
            y: Math.round(window.screenY + rect.top)
        }));
    }
}

function connectBridge() {
    socket = new WebSocket('ws://localhost:8765');

    socket.onopen = () => {
        addLog('Connected to Studio Bridge', 'system');
        updateMockup(currentMockup);
    };

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'LOG') {
            addLog(data.payload, 'device');
        } else if (data.type === 'STATUS') {
             addLog(`Device Status: ${data.payload}`, 'system');
        }
    };

    socket.onclose = () => {
        addLog('Bridge disconnected. Retrying...', 'error');
        setTimeout(connectBridge, 3000);
    };
}

// Event Listeners
document.querySelectorAll('.mockup-btn').forEach(btn => {
    btn.onclick = () => {
        document.querySelector('.mockup-btn.active').classList.remove('active');
        btn.classList.add('active');
        updateMockup(btn.dataset.mockup);
    };
});

document.getElementById('btn-kill-net').onclick = () => {
    addLog('Injecting Network Fault...', 'error');
    socket.send(JSON.stringify({ type: 'COMMAND', command: 'FAULT:OFFLINE' }));
};

document.getElementById('btn-rebrand').onclick = () => {
    addLog('Simulating Remote Rebrand...', 'system');
    // Enviar evento de config simulado vía bridge
};

document.getElementById('btn-align').onclick = () => {
    updateMockup(currentMockup);
};

// Start
updateMockup('napkin');
connectBridge();
