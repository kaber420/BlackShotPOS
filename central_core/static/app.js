document.addEventListener('DOMContentLoaded', () => {
    checkAllBranches();
    updateStats();
    initLiveFeed();
    
    // Actualizar estados cada 30 segundos
    setInterval(checkAllBranches, 30000);
});

async function updateStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        
        // Revenue y conteo
        const revenueEl = document.getElementById('total-revenue');
        if (revenueEl) revenueEl.textContent = 
            new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(data.total_revenue);
            
        const countEl = document.getElementById('total-sales-count');
        if (countEl) countEl.textContent = data.total_sales_count;

        // Ticket Promedio
        const avgTicket = data.total_sales_count > 0 ? (data.total_revenue / data.total_sales_count) : 0;
        const avgTicketEl = document.getElementById('avg-ticket');
        if (avgTicketEl) avgTicketEl.textContent = 
            new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(avgTicket);

        // Top Productos
        const topList = document.getElementById('top-products-list');
        if (topList && data.top_products) {
            if (data.top_products.length === 0) {
                topList.innerHTML = '<div style="opacity: 0.5; padding: 20px; text-align: center;">No hay datos de productos aún.</div>';
            } else {
                topList.innerHTML = data.top_products.map(p => `
                    <div class="top-product-item">
                        <span class="top-product-name">${p.name}</span>
                        <span class="top-product-qty">${p.quantity} vendidos</span>
                    </div>
                `).join('');
            }
        }
    } catch (error) {
        console.error('Error fetching stats:', error);
    }
}

function initLiveFeed() {
    const eventsList = document.getElementById('live-events-list');
    if (!eventsList) return; // Solo si estamos en el dashboard
    
    const eventSource = new EventSource('/api/events/feed');
    const emptyFeed = document.getElementById('empty-feed');

    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.error) return;

        if (emptyFeed) emptyFeed.style.display = 'none';

        // Crear elemento de evento
        const div = document.createElement('div');
        div.className = 'event-item';
        div.innerHTML = `
            <div class="event-icon">💰</div>
            <div class="event-details">
                <span class="event-branch">Sucursal ${data.branch_id}</span>
                <span class="event-amount">${new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(data.amount)}</span>
                <span class="event-time">¡Recién recibido!</span>
            </div>
        `;

        // Insertar al principio
        eventsList.insertBefore(div, eventsList.firstChild);

        // Limitar a los últimos 20
        if (eventsList.children.length > 20) {
            eventsList.removeChild(eventsList.lastChild);
        }

        // Actualizar estadísticas globales
        updateStats();
    };

    eventSource.onerror = () => {
        console.warn('SSE connection lost. Reconnecting...');
    };
}

async function checkAllBranches() {
    const cards = document.querySelectorAll('.branch-card');
    let onlineCount = 0;

    for (const card of cards) {
        const branchId = card.dataset.id;
        try {
            const response = await fetch(`/api/branches/${branchId}/status`);
            const data = await response.json();
            
            const statusDot = card.querySelector('.status-dot');
            const statusText = card.querySelector('.status-text');
            
            if (statusDot) statusDot.classList.remove('loading', 'online', 'offline');
            
            if (data.status === 'online') {
                if (statusDot) statusDot.classList.add('online');
                if (statusText) statusText.textContent = `En línea`;
                onlineCount++;
            } else {
                if (statusDot) statusDot.classList.add('offline');
                if (statusText) statusText.textContent = 'Desconectada';
            }
        } catch (error) {
            console.error(`Error checking branch ${branchId}:`, error);
        }
    }

    const onlineCounter = document.getElementById('online-branches');
    if (onlineCounter) onlineCounter.textContent = onlineCount;
}

// ... Rest of the functions (add branch, modals)
async function submitAddBranch(event) {
    event.preventDefault();
    const name = document.getElementById('branch-name').value;
    const url = document.getElementById('branch-url').value;
    const regionId = document.getElementById('branch-region').value;

    try {
        const response = await fetch('/api/branches', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                name, 
                base_url: url, 
                region_id: regionId ? parseInt(regionId) : null 
            })
        });
        
        const branch = await response.json();
        location.reload(); // Recargar para ver la nueva sucursal
    } catch (error) {
        alert('Error al registrar sucursal');
    }
}

function openAddBranchModal() {
    document.getElementById('add-branch-modal').style.display = 'block';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

function showConnectInfo(id, natsUrl, key) {
    const modal = document.getElementById('connect-modal');
    document.getElementById('branch-id-display').value = id;
    document.getElementById('nats-url-display').value = natsUrl;
    document.getElementById('public-key-display').value = key;
    modal.style.display = 'block';
}

async function viewProducts(branchId) {
    // Por ahora redirigimos o abrimos un modal de productos
    alert("Cargando productos de la sucursal " + branchId + " via Bridge Auth...");
}
