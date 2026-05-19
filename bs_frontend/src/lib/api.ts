
/**
 * Cliente base para hacer peticiones al backend FastAPI
 */

// Cliente base para hacer peticiones al backend FastAPI (usando Credentials: include para Cookies)
const getAuthHeaders = (isFormData: boolean = false) => {
	const headers: Record<string, string> = {};
	
	if (!isFormData) {
		headers['Content-Type'] = 'application/json';
	}
	
	return headers;
};

export async function fetchApi<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
	// Asegurar que endpoint empiece con /
	const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
	const url = path;
	const isFormData = options.body instanceof FormData;

	try {
		const response = await fetch(url, {
			...options,
			credentials: 'include',
			headers: {
				...getAuthHeaders(isFormData),
				...options.headers
			}
		});

		if (!response.ok) {
			if (response.status === 401) {
				if (typeof window !== 'undefined') {
					// Redirigir al login si no estamos en la página de login
					if (!window.location.pathname.startsWith('/login')) {
						window.location.href = '/login';
					}
				}
			}
			const errorData = await response.json().catch(() => null);
			let errorMessage = errorData?.detail || `Error HTTP: ${response.status}`;
			
			// Si el detalle es un array (errores de validación de FastAPI), lo aplanamos a string
			if (Array.isArray(errorMessage)) {
				errorMessage = errorMessage
					.map((err: any) => typeof err === 'string' ? err : (err.msg || JSON.stringify(err)))
					.join(', ');
			}
			
			throw new Error(errorMessage);
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
