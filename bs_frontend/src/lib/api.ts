/**
 * Cliente base para hacer peticiones al backend FastAPI
 * Ya que Vite hace proxy a /api, no necesitamos poner domain
 */

// Para el prototipo rápido, simularemos un token, después lo conectaremos a omni_auth
const getAuthHeaders = () => {
	const headers: Record<string, string> = {
		'Content-Type': 'application/json'
	};
	
	// Leer token de localStorage si estamos en el navegador
	if (typeof window !== 'undefined') {
		const token = localStorage.getItem('X-Omni-Token');
		if (token) {
			headers['X-Omni-Token'] = token;
		}
	}
	
	return headers;
};

export async function fetchApi<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
	// Asegurar que endpoint empiece con /
	const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;

	try {
		const response = await fetch(path, {
			...options,
			headers: {
				...getAuthHeaders(),
				...options.headers
			}
		});

		if (!response.ok) {
			if (response.status === 401) {
				if (typeof window !== 'undefined') {
					localStorage.removeItem('X-Omni-Token');
					// Opcionalmente podemos disparar un evento para que el UI sepa
					window.location.href = '/login';
				}
			}
			const errorData = await response.json().catch(() => null);
			throw new Error(errorData?.detail || `Error HTTP: ${response.status}`);
		}

		// Para endpoints que devuelven vacío (ej. 204 No Content)
		if (response.status === 204) {
			return null as unknown as T;
		}

		return response.json();
	} catch (error) {
		console.error(`Error en API_CLIENT al llamar ${path}:`, error);
		throw error;
	}
}
