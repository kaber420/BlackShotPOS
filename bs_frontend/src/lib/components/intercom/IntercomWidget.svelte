<script lang="ts">
    import { onMount } from 'svelte';
    import { fade, fly, scale } from 'svelte/transition';
    import { posSocket } from '$lib/pos_socket.svelte';
    import { audioService } from '$lib/audio_service';
    import { IntercomService } from '$lib/api/intercom';
    import { ProductionAreaService, type ProductionArea } from '$lib/api/production_areas';
    import { appState } from '$lib/app_state.svelte';

    let isOpen = $state(false);
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

        // Try to get mic stream early to avoid blocking
        try {
            await audioService.getMicrophoneStream();
        } catch (e) {
            console.warn("Microphone access denied or not available:", e);
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
            // Si falla por autoplay, marcamos como bloqueado
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

<div class="intercom-container" class:open={isOpen}>
    {#if isOpen}
        <div class="intercom-panel" transition:fly={{ y: 20, duration: 300 }}>
            <div class="panel-header">
                <div class="header-info">
                    <span class="icon">📻</span>
                    <h3>Radio Intercom</h3>
                </div>
                <button class="btn-close" onclick={() => isOpen = false}>×</button>
            </div>

            <div class="panel-body">
                <!-- Settings: My Area & Mode -->
                <div class="settings-row">
                    <div class="setting-group">
                        <label for="my-area">Mi Área:</label>
                        <select id="my-area" value={posSocket.intercomSettings.currentAreaId} onchange={(e) => setMyArea(e.currentTarget.value ? parseInt(e.currentTarget.value) : null)}>
                            <option value={null}>General / Ventas</option>
                            {#each areas as area}
                                <option value={area.id}>{area.name}</option>
                            {/each}
                        </select>
                    </div>
                    <div class="setting-group">
                        <label for="mode">Modo:</label>
                        <select id="mode" value={posSocket.intercomSettings.mode} onchange={(e) => setMode(e.currentTarget.value as any)}>
                            <option value="Live">🔈 Vivo</option>
                            <option value="Inbox">📥 Buzón</option>
                            <option value="Muted">🔕 Mudo</option>
                        </select>
                    </div>
                </div>

                {#if audioBlocked}
                    <div class="alert-audio" onclick={unlockAudio}>
                        ⚠️ El navegador bloqueó el audio automático. Haz clic aquí para activar.
                    </div>
                {/if}

                <!-- Message History -->
                <div class="message-list">
                    {#if posSocket.intercomMessages.length === 0}
                        <p class="empty-state">No hay mensajes recientes.</p>
                    {:else}
                        {#each posSocket.intercomMessages as msg}
                            <div class="message-item" class:is-mine={msg.sender_name.toLowerCase() === appState.userName?.toLowerCase()}>
                                <div class="msg-header">
                                    <span class="sender">{msg.sender_name}</span>
                                    <span class="time">{formatDate(msg.timestamp)}</span>
                                </div>
                                <div class="msg-content">
                                    <button class="btn-play" onclick={() => playMessage(msg.audio_url)}>
                                        ▶️ Escuchar
                                    </button>
                                    {#if msg.is_global}
                                        <span class="badge global">Global</span>
                                    {:else}
                                        <div class="target-areas">
                                            {#each msg.target_areas as aid}
                                                <span class="badge">{areas.find(a => a.id === aid)?.name || aid}</span>
                                            {/each}
                                        </div>
                                    {/if}
                                </div>
                            </div>
                        {/each}
                    {/if}
                </div>

                <!-- PTT Controls -->
                <div class="ptt-controls">
                    <div class="channel-selector">
                        <button class="chip" class:active={isGlobal} onclick={toggleGlobal}>🌍 Todos</button>
                        {#each areas as area}
                            <button class="chip" class:active={selectedAreaIds.includes(area.id)} onclick={() => toggleArea(area.id)}>
                                {area.name}
                            </button>
                        {/each}
                    </div>

                    <div class="ptt-button-wrapper">
                        <button 
                            class="ptt-button" 
                            class:recording={isRecording}
                            onmousedown={toggleRecording}
                            onmouseup={toggleRecording}
                            ontouchstart={(e) => { e.preventDefault(); toggleRecording(); }}
                            ontouchend={(e) => { e.preventDefault(); toggleRecording(); }}
                        >
                            <div class="inner-circle">
                                {#if isRecording}
                                    <div class="waves"></div>
                                    🎤
                                {:else}
                                    🔘
                                {/if}
                            </div>
                        </button>
                        <p class="ptt-hint">{isRecording ? 'Hablando...' : 'Presiona para hablar'}</p>
                    </div>
                </div>
            </div>
        </div>
    {/if}

    <button class="intercom-toggle" class:active={isOpen} onclick={() => isOpen = !isOpen}>
        <span class="toggle-icon">📻</span>
        {#if !isOpen && posSocket.intercomMessages.length > 0}
             <span class="badge-count" transition:scale>{posSocket.intercomMessages.length > 9 ? '9+' : posSocket.intercomMessages.length}</span>
        {/if}
    </button>
</div>

<style>
    .intercom-container {
        position: fixed;
        bottom: 1.5rem;
        right: 1.5rem;
        z-index: 9999;
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        gap: 1rem;
    }

    /* Toggle Button */
    .intercom-toggle {
        width: 60px;
        height: 60px;
        border-radius: 50%;
        background: var(--primary, #6366f1);
        color: white;
        border: none;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
        transition: transform 0.2s, background 0.2s;
        position: relative;
    }

    .intercom-toggle:hover {
        transform: scale(1.05);
        background: var(--primary-focus, #4f46e5);
    }

    .intercom-toggle.active {
        background: #ef4444;
    }

    .badge-count {
        position: absolute;
        top: -5px;
        right: -5px;
        background: #ef4444;
        color: white;
        font-size: 0.75rem;
        padding: 2px 6px;
        border-radius: 10px;
        font-weight: bold;
        border: 2px solid white;
    }

    /* Panel */
    .intercom-panel {
        width: 350px;
        height: 500px;
        background: var(--base-100, #ffffff);
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        display: flex;
        flex-direction: column;
        overflow: hidden;
        border: 1px solid rgba(0,0,0,0.1);
    }

    .panel-header {
        padding: 1rem;
        background: var(--primary, #6366f1);
        color: white;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .header-info {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .header-info h3 {
        margin: 0;
        font-size: 1rem;
        font-weight: 600;
    }

    .btn-close {
        background: rgba(255,255,255,0.2);
        border: none;
        color: white;
        width: 24px;
        height: 24px;
        border-radius: 50%;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .panel-body {
        flex: 1;
        display: flex;
        flex-direction: column;
        padding: 1rem;
        gap: 1rem;
        overflow: hidden;
    }

    /* Settings */
    .settings-row {
        display: flex;
        gap: 0.5rem;
        font-size: 0.8rem;
    }

    .setting-group {
        display: flex;
        flex-direction: column;
        flex: 1;
        gap: 0.2rem;
    }

    .setting-group select {
        padding: 0.2rem;
        border-radius: 5px;
        border: 1px solid #ccc;
    }

    .alert-audio {
        background: #fef3c7;
        color: #92400e;
        padding: 0.5rem;
        border-radius: 8px;
        font-size: 0.8rem;
        cursor: pointer;
        text-align: center;
    }

    /* Message List */
    .message-list {
        flex: 1;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
        padding-right: 0.5rem;
    }

    .empty-state {
        text-align: center;
        color: #888;
        margin-top: 2rem;
        font-style: italic;
    }

    .message-item {
        background: #f3f4f6;
        padding: 0.5rem 0.75rem;
        border-radius: 12px;
        max-width: 90%;
        align-self: flex-start;
    }

    .message-item.is-mine {
        background: #e0e7ff;
        align-self: flex-end;
    }

    .msg-header {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        margin-bottom: 0.25rem;
    }

    .sender {
        font-weight: bold;
        font-size: 0.8rem;
    }

    .time {
        font-size: 0.7rem;
        color: #666;
    }

    .msg-content {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .btn-play {
        background: white;
        border: 1px solid #ddd;
        border-radius: 20px;
        padding: 0.2rem 0.6rem;
        font-size: 0.8rem;
        cursor: pointer;
    }

    .btn-play:hover {
        background: #f9fafb;
    }

    .target-areas {
        display: flex;
        gap: 0.2rem;
        flex-wrap: wrap;
    }

    .badge {
        font-size: 0.65rem;
        background: #e5e7eb;
        padding: 1px 4px;
        border-radius: 4px;
        color: #4b5563;
    }

    .badge.global {
        background: #dcfce7;
        color: #166534;
    }

    /* PTT Controls */
    .ptt-controls {
        padding-top: 1rem;
        border-top: 1px solid #eee;
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }

    .channel-selector {
        display: flex;
        gap: 0.4rem;
        flex-wrap: wrap;
        max-height: 80px;
        overflow-y: auto;
    }

    .chip {
        padding: 0.25rem 0.6rem;
        border-radius: 20px;
        background: #f3f4f6;
        border: 1px solid #ddd;
        font-size: 0.75rem;
        cursor: pointer;
        transition: all 0.2s;
    }

    .chip:hover {
        background: #e5e7eb;
    }

    .chip.active {
        background: var(--primary, #6366f1);
        color: white;
        border-color: var(--primary, #6366f1);
    }

    .ptt-button-wrapper {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.5rem;
    }

    .ptt-button {
        width: 70px;
        height: 70px;
        border-radius: 50%;
        background: #eee;
        border: 4px solid #ddd;
        cursor: pointer;
        padding: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: transform 0.1s;
    }

    .ptt-button:active, .ptt-button.recording {
        transform: scale(0.95);
        background: #fee2e2;
        border-color: #ef4444;
    }

    .inner-circle {
        font-size: 1.5rem;
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;
    }

    .ptt-hint {
        font-size: 0.75rem;
        color: #666;
        margin: 0;
    }

    /* Recording animation */
    .waves {
        position: absolute;
        width: 100%;
        height: 100%;
        background: rgba(239, 68, 68, 0.2);
        border-radius: 50%;
        animation: pulse 1.5s infinite;
        z-index: -1;
    }

    @keyframes pulse {
        0% { transform: scale(1); opacity: 0.8; }
        100% { transform: scale(1.5); opacity: 0; }
    }
</style>
