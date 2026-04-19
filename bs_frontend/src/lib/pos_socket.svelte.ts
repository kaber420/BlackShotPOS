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
                    if (data.topic && data.data !== undefined) {
                        switch (data.topic) {
                            case 'kitchen_orders':
                                this.kitchenOrders = data.data;
                                break;
                            case 'recent_orders':
                                this.recentOrders = data.data;
                                break;
                            case 'dashboard_stats':
                                this.dashboardStats = data.data;
                                break;
                            case 'tables':
                                this.tables = data.data;
                                break;
                        }
                    } else {
                        console.warn("SOCKET: Formato de mensaje desconocido (faltaban topic/data)");
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
