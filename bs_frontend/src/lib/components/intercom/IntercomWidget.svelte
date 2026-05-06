<script lang="ts">
    import { onMount } from 'svelte';
    import { fade, fly, scale } from 'svelte/transition';
    import { posSocket } from '$lib/pos_socket.svelte';
    import { audioService } from '$lib/audio_service';
    import { IntercomService } from '$lib/api/intercom';
    import { ProductionAreaService, type ProductionArea } from '$lib/api/production_areas';
    import { appState, setIntercomOpen, setIntercomEnabled } from '$lib/app_state.svelte';

    let isRecording = $state(false);
    let selectedAreaIds = $state<number[]>([]);
    let isGlobal = $state(false);
    let areas = $state<ProductionArea[]>([]);
    let isLoadingAreas = $state(false);

    // Audio status
    let audioBlocked = $state(false);

    onMount(async () => {
        // Initialize Intercom history and settings
        await posSocket.initIntercom();
        
        // Subscribe to real-time events
        posSocket.subscribe('intercom');
        
        // Load production areas
        try {
            isLoadingAreas = true;
            areas = await ProductionAreaService.getAll();
        } catch (e) {
            console.error("Error loading areas for intercom:", e);
        } finally {
            isLoadingAreas = false;
        }
    });

    async function toggleRecording() {
        if (!isRecording) {
            try {
                await audioService.startRecording();
                isRecording = true;
            } catch (e) {
                console.error("Failed to start recording:", e);
                alert("Error al acceder al micrófono.");
            }
        } else {
            isRecording = false;
            try {
                const blob = await audioService.stopRecording();
                if (blob.size > 100) { // Avoid sending tiny/empty files
                    await IntercomService.sendVoiceMessage(blob, selectedAreaIds, isGlobal);
                }
            } catch (e) {
                console.error("Failed to stop/send recording:", e);
            }
        }
    }

    function toggleArea(id: number) {
        if (selectedAreaIds.includes(id)) {
            selectedAreaIds = selectedAreaIds.filter(aid => aid !== id);
        } else {
            selectedAreaIds = [...selectedAreaIds, id];
        }
        isGlobal = false;
    }

    function toggleGlobal() {
        isGlobal = !isGlobal;
        if (isGlobal) selectedAreaIds = [];
    }

    function setMode(mode: 'Live' | 'Inbox' | 'Muted') {
        posSocket.intercomSettings.mode = mode;
        localStorage.setItem('bs_intercom_mode', mode);
    }

    function setMyArea(areaId: number | null) {
        posSocket.intercomSettings.currentAreaId = areaId;
        if (areaId) localStorage.setItem('bs_intercom_area', areaId.toString());
        else localStorage.removeItem('bs_intercom_area');
    }

    const SILENT_SOUND = 'data:audio/wav;base64,UklGRigAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQQAAAAAAA==';

    function playMessage(url: string) {
        if (!url) return;
        const absoluteUrl = url.startsWith('http') ? url : window.location.origin + url;
        audioService.playAudio(absoluteUrl).catch(err => {
            console.error("Playback failed:", err);
            if (err.name === 'NotAllowedError' || err.name === 'NotSupportedError') {
                audioBlocked = true;
            }
        });
    }

    async function unlockAudio() {
        try {
            await audioService.playAudio(SILENT_SOUND);
            audioBlocked = false;
        } catch (e) {
            console.error("Failed to unlock audio:", e);
        }
    }

    function formatDate(dateStr: string) {
        const date = new Date(dateStr);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
</script>

{#if appState.intercomOpen}
    <div class="fixed inset-0 z-[100] flex items-center justify-center p-4">
        <!-- Backdrop -->
        <div 
            class="absolute inset-0 bg-base-300/60 backdrop-blur-sm" 
            onclick={() => setIntercomOpen(false)}
            transition:fade
        ></div>

        <!-- Panel -->
        <div 
            class="intercom-panel w-full max-w-md bg-base-100 rounded-3xl shadow-2xl border border-base-300 overflow-hidden relative"
            transition:fly={{ y: 20, duration: 300 }}
        >
            <div class="panel-header px-6 py-4 bg-primary text-primary-content flex justify-between items-center">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center">
                        <svg class="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M16 2v4" />
                            <rect x="7" y="6" width="10" height="14" rx="2" />
                            <path d="M10 10h4" />
                            <path d="M10 12h4" />
                            <path d="M10 14h4" />
                            <path d="M7 9H5v4h2" />
                            <path d="M9 2v4" />
                        </svg>
                    </div>
                    <div>
                        <h3 class="font-black text-lg tracking-tight">Blackshot Intercom</h3>
                        <p class="text-[10px] uppercase tracking-widest opacity-70 font-bold">Comunicación en Tiempo Real</p>
                    </div>
                </div>
                <button class="btn btn-circle btn-ghost btn-sm text-primary-content hover:bg-white/10" onclick={() => setIntercomOpen(false)}>
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
                </button>
            </div>

            <div class="panel-body p-6 flex flex-col gap-4 max-h-[70vh] overflow-hidden">
                <!-- Master Toggle -->
                <div class="flex items-center justify-between bg-base-200/50 p-4 rounded-2xl border border-base-300/50">
                    <div class="flex items-center gap-3">
                        <div class="w-3 h-3 rounded-full {appState.intercomEnabled ? 'bg-success animate-pulse' : 'bg-base-300 shadow-inner'}"></div>
                        <div class="flex flex-col">
                            <span class="text-xs font-black uppercase tracking-widest">Servicio de Intercom</span>
                            <span class="text-[9px] opacity-50 font-bold uppercase">{appState.intercomEnabled ? 'Activo y escuchando' : 'Desactivado'}</span>
                        </div>
                    </div>
                    <input 
                        type="checkbox" 
                        class="toggle toggle-primary" 
                        checked={appState.intercomEnabled} 
                        onchange={(e) => setIntercomEnabled(e.currentTarget.checked)}
                    />
                </div>

                <!-- Settings: My Area & Mode -->
                <div class="grid grid-cols-2 gap-3">
                    <div class="flex flex-col gap-1">
                        <label class="text-[10px] font-black uppercase opacity-50 ml-1" for="my-area">Mi Estación</label>
                        <select 
                            id="my-area" 
                            class="select select-bordered select-sm w-full font-bold bg-base-200 border-none rounded-xl"
                            value={posSocket.intercomSettings.currentAreaId} 
                            onchange={(e) => setMyArea(e.currentTarget.value ? parseInt(e.currentTarget.value) : null)}
                        >
                            <option value={null}>General / Ventas</option>
                            {#each areas as area}
                                <option value={area.id}>{area.name}</option>
                            {/each}
                        </select>
                    </div>
                    <div class="flex flex-col gap-1">
                        <label class="text-[10px] font-black uppercase opacity-50 ml-1" for="mode">Recepción</label>
                        <select 
                            id="mode" 
                            class="select select-bordered select-sm w-full font-bold bg-base-200 border-none rounded-xl"
                            value={posSocket.intercomSettings.mode} 
                            onchange={(e) => setMode(e.currentTarget.value as any)}
                        >
                            <option value="Live">🔈 En Vivo</option>
                            <option value="Inbox">📥 Solo Buzón</option>
                            <option value="Muted">🔕 Silenciado</option>
                        </select>
                    </div>
                </div>

                {#if audioBlocked}
                    <div class="alert alert-warning text-xs py-2 px-3 rounded-xl cursor-pointer hover:bg-warning/80 transition-colors" onclick={unlockAudio}>
                        <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-4 w-4" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
                        <span>El navegador bloqueó el audio. <b>Toca aquí para activar.</b></span>
                    </div>
                {/if}


                <!-- Message History -->
                <div class="flex-1 overflow-y-auto pr-2 flex flex-col gap-3 min-h-[200px]">
                    {#if posSocket.intercomMessages.length === 0}
                        <div class="flex flex-col items-center justify-center h-full opacity-30 gap-2">
                            <svg class="w-12 h-12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                            <p class="text-sm font-medium italic text-center">Sin actividad en el canal</p>
                        </div>
                    {:else}
                        {#each posSocket.intercomMessages as msg}
                            <div class="message-item flex flex-col gap-1" class:is-mine={msg.sender_name.toLowerCase() === appState.userName?.toLowerCase()}>
                                <div class="flex items-center gap-2" class:justify-end={msg.sender_name.toLowerCase() === appState.userName?.toLowerCase()}>
                                    <span class="text-[10px] font-black opacity-50 uppercase tracking-widest">{msg.sender_name}</span>
                                    <span class="text-[9px] opacity-30">{formatDate(msg.timestamp)}</span>
                                </div>
                                <div 
                                    class="p-3 rounded-2xl flex items-center gap-3 shadow-sm {msg.sender_name.toLowerCase() === appState.userName?.toLowerCase() ? 'bg-primary text-primary-content rounded-tr-none self-end' : 'bg-base-200 rounded-tl-none self-start'}"
                                >
                                    <button 
                                        class="btn btn-circle btn-sm {msg.sender_name.toLowerCase() === appState.userName?.toLowerCase() ? 'btn-ghost bg-white/20' : 'btn-primary'}" 
                                        onclick={() => playMessage(msg.audio_url)}
                                    >
                                        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
                                    </button>
                                    
                                    <div class="flex flex-col">
                                        <span class="text-[10px] font-bold opacity-60">Mensaje de Voz</span>
                                        <div class="flex gap-1 mt-0.5">
                                            {#if msg.is_global}
                                                <span class="px-1.5 py-0.5 rounded bg-success/20 text-success text-[8px] font-black uppercase">Global</span>
                                            {:else}
                                                {#each msg.target_areas as aid}
                                                    <span class="px-1.5 py-0.5 rounded bg-base-300 text-base-content/50 text-[8px] font-black uppercase">
                                                        {areas.find(a => a.id === aid)?.name || aid}
                                                    </span>
                                                {/each}
                                            {/if}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        {/each}
                    {/if}
                </div>

                <!-- PTT Controls -->
                <div class="mt-2 pt-4 border-t border-base-200 flex flex-col gap-4">
                    <div class="flex flex-wrap gap-1.5 justify-center">
                        <button 
                            class="btn btn-xs rounded-full font-black uppercase tracking-widest {isGlobal ? 'btn-primary' : 'btn-ghost bg-base-200'}" 
                            onclick={toggleGlobal}
                        >
                            🌍 Todos
                        </button>
                        {#each areas as area}
                            <button 
                                class="btn btn-xs rounded-full font-black uppercase tracking-widest {selectedAreaIds.includes(area.id) ? 'btn-primary' : 'btn-ghost bg-base-200'}" 
                                onclick={() => toggleArea(area.id)}
                            >
                                {area.name}
                            </button>
                        {/each}
                    </div>

                    <div class="flex flex-col items-center gap-2">
                        <button 
                            class="w-20 h-20 rounded-full flex items-center justify-center transition-all duration-75 relative group"
                            class:bg-error={isRecording}
                            class:text-error-content={isRecording}
                            class:bg-primary={!isRecording}
                            class:text-primary-content={!isRecording}
                            class:scale-95={isRecording}
                            class:shadow-2xl={isRecording}
                            onmousedown={toggleRecording}
                            onmouseup={toggleRecording}
                            ontouchstart={(e) => { e.preventDefault(); toggleRecording(); }}
                            ontouchend={(e) => { e.preventDefault(); toggleRecording(); }}
                        >
                            {#if isRecording}
                                <div class="absolute inset-0 rounded-full animate-ping bg-error/40"></div>
                                <svg class="w-8 h-8 relative z-10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                                    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/>
                                </svg>
                            {:else}
                                <svg class="w-8 h-8 group-hover:scale-110 transition-transform" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                                    <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/>
                                </svg>
                            {/if}
                        </button>
                        <p class="text-[10px] font-black uppercase tracking-[0.2em] opacity-40">
                            {isRecording ? 'Transmitiendo...' : 'Mantener para hablar'}
                        </p>
                    </div>
                </div>
            </div>
        </div>
    </div>
{/if}

<style>
    .intercom-panel {
        max-height: 90vh;
    }
    
    .message-item.is-mine .message-bubble {
        background-color: var(--p);
        color: var(--pc);
    }

    /* Hide scrollbar for cleaner look but allow scrolling */
    .overflow-y-auto {
        scrollbar-width: thin;
        scrollbar-color: var(--fallback-p,oklch(var(--p)/0.2)) transparent;
    }
</style>
