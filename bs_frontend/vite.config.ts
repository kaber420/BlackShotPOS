import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
	// Carga variables del archivo .env en el directorio raíz (..)
	const env = loadEnv(mode, '../', '');
	const host = env.HOST || '127.0.0.1';
	const port = env.PORT || '8400';

	return {
		plugins: [tailwindcss(), sveltekit()],
		server: {
			proxy: {
				'/api': {
					target: `http://${host}:${port}`,
					changeOrigin: true
				},
				'/uploads': {
					target: `http://${host}:${port}`,
					changeOrigin: true
				}
			}
		}
	};
});
