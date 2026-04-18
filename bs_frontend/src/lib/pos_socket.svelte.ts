import type { Order } from '$lib/api/orders';
import type { Table } from '$lib/api/tables';

export type SocketStatus = 'connecting' | 'open' | 'closed';

class PosSocketManager {
    socket = $state<WebSocket | null>(null);
    status = $state<SocketStatus>('closed');
    
    // Topics data
    kitchenOrders = $state<Order[]>([]);
    recentOrders = $state<Order[]>([]);
    tables = $state<Table[]>([]);
    dashboardStats = $state<any>(null);

    private subscribedTopics = new Set<string>();
    private reconnectTimeout: any = null;
    private isManuallyClosed = false;

    connect() {
        if (typeof window === 'undefined') return;
        this.isManuallyClosed = false;
        
        // Prevent duplicate connection attempts
        if (this.status === 'connecting' || this.status === 'open') return;

        const token = localStorage.getItem('X-Omni-Token');
        if (!token) {
            console.warn("SOCKET: No token found. Could not connect.");
            return;
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const url = `${protocol}//${host}/api/v1/pos/ws/pos?token=${encodeURIComponent(token)}`;

        console.log("🔌 SOCKET: Conectando...");
        this.status = 'connecting';
        
        this.socket = new WebSocket(url);

        this.socket.onopen = () => {
            console.log("🔌 SOCKET: Conectado");
            this.status = 'open';
            
            // Re-subscribe to all active topics on reconnect
            for (const topic of this.subscribedTopics) {
                this.socket?.send(JSON.stringify({ action: "subscribe", topic }));
            }
        };

        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.error) {
                    console.error("SOCKET: Error desde el servidor:", data.detail);
                } else {
                    // We need to figure out which topic this data belongs to.
                    // Since the current backend just sends raw data without wrappers, 
                    // we might need to guess based on active subscriptions or data shape.
                    // A better approach is to wrap data {topic: "xx", data: []} on the backend.
                    // But for now, we'll try to infer based on active topics and data structure 
                    
                    // IF it's an array and we are subscribed to tables and it has a 'number' and 'capacity' property
                    if (Array.isArray(data) && data.length > 0 && data[0].hasOwnProperty('number') && data[0].hasOwnProperty('capacity')) {
                        this.tables = data;
                    } 
                    // Else if it has preparingCount, it is dashboard_stats
                    else if (!Array.isArray(data) && data && data.hasOwnProperty('preparingCount')) {
                        this.dashboardStats = data;
                    }
                    // Else it's orders. This is tricky because kitchen_orders and recent_orders have similar structure.
                    // Ideally the backend should tell us the topic. 
                    // However, we can just update all order collections if they are arrays.
                    // The backend just broadcasts raw json arrays for orders.
                    else if (Array.isArray(data)) {
                        // Just update both to be safe for now since they are just different filters of the same data mostly
                        // But wait, they are different subsets.
                        // I will update both if we don't have a reliable way to differentiate right now.
                        // Wait, kitchen_orders are only PENDING and PREPARING.
                        // We can filter it here on the client from the unified array if needed, but since backend pushes it, let's update both.
                        const hasOnlyKitchenStatus = data.every(o => o.status === 'PENDING' || o.status === 'PREPARING');
                        if (hasOnlyKitchenStatus && this.subscribedTopics.has('kitchen_orders')) {
                            this.kitchenOrders = data;
                        } 
                        if (this.subscribedTopics.has('recent_orders')) {
                            this.recentOrders = data;
                        }
                    } else if (Array.isArray(data) && data.length === 0) {
                        // Empty states
                        if (this.subscribedTopics.has('kitchen_orders')) this.kitchenOrders = [];
                        if (this.subscribedTopics.has('recent_orders')) this.recentOrders = [];
                        if (this.subscribedTopics.has('tables')) this.tables = [];
                    }
                }
            } catch (e) {
                console.error("SOCKET: Error parseando datos", e);
            }
        };

        this.socket.onclose = () => {
            if (this.isManuallyClosed) return;
            console.log("🔌 SOCKET: Desconectado");
            this.status = 'closed';
            this.socket = null;
            // Reintentar en 3 segundos
            clearTimeout(this.reconnectTimeout);
            this.reconnectTimeout = setTimeout(() => this.connect(), 3000);
        };

        this.socket.onerror = (err) => {
            console.error("❌ SOCKET: Error", err);
            this.status = 'closed';
        };
    }

    subscribe(topic: string) {
        this.subscribedTopics.add(topic);
        if (this.status === 'open' && this.socket) {
            this.socket.send(JSON.stringify({ action: "subscribe", topic }));
        } else if (this.status === 'closed') {
            this.connect();
        }
    }

    unsubscribe(topic: string) {
        // En una app tipo POS es mejor mantener el socket vivo permanentemente
        // tras el login, en lugar de desconectar entre cambios de ruta.
        // this.subscribedTopics.delete(topic);
    }

    close() {
        this.isManuallyClosed = true;
        clearTimeout(this.reconnectTimeout);
        if (this.socket) {
            this.socket.close();
            this.socket = null;
        }
        this.status = 'closed';
    }
}

export const posSocket = new PosSocketManager();
