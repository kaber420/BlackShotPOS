/**
 * Blackshot POS - Audio Service
 * -----------------------------
 * Handles microphone capture (Opus) and real-time audio playback.
 */

export class AudioService {
    private mediaRecorder: MediaRecorder | null = null;
    private chunks: Blob[] = [];
    private stream: MediaStream | null = null;
    private currentAudio: HTMLAudioElement | null = null;

    async getMicrophoneStream(): Promise<MediaStream> {
        if (this.stream) return this.stream;
        this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        return this.stream;
    }

    async startRecording(): Promise<void> {
        console.log("🎤 AudioService: Iniciando grabación...");
        const stream = await this.getMicrophoneStream();
        this.chunks = [];
        
        // Prefer Opus if available
        const mimeType = MediaRecorder.isTypeSupported('audio/webm; codecs=opus') 
            ? 'audio/webm; codecs=opus' 
            : 'audio/webm';
        
        console.log("🎤 AudioService: Usando mimeType", mimeType);
            
        this.mediaRecorder = new MediaRecorder(stream, { mimeType });
        
        this.mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) {
                console.log("🎤 AudioService: Data recibida", e.data.size, "bytes");
                this.chunks.push(e.data);
            }
        };

        this.mediaRecorder.onerror = (e) => {
            console.error("❌ AudioService: Error en MediaRecorder", e);
        };

        this.mediaRecorder.start(100); // Enviar data cada 100ms
    }

    async stopRecording(): Promise<Blob> {
        return new Promise((resolve, reject) => {
            if (!this.mediaRecorder) return reject('No recorder active');

            this.mediaRecorder.onstop = () => {
                const blob = new Blob(this.chunks, { type: this.mediaRecorder?.mimeType });
                console.log("🎤 AudioService: Grabación terminada. Total:", blob.size, "bytes");
                
                // Stop all tracks to release the microphone (removes the browser icon)
                if (this.stream) {
                    this.stream.getTracks().forEach(track => track.stop());
                    this.stream = null;
                }
                
                resolve(blob);
            };

            this.mediaRecorder.stop();
        });
    }

    async playAudio(url: string): Promise<void> {
        console.log("🔊 AudioService: Intentando reproducir", url);
        
        return new Promise((resolve, reject) => {
            // Stop previous audio if any
            if (this.currentAudio) {
                try {
                    this.currentAudio.pause();
                    this.currentAudio.src = "";
                    this.currentAudio.load();
                } catch (e) {
                    console.warn("Error stopping previous audio:", e);
                }
                this.currentAudio = null;
            }

            if (!url) {
                resolve();
                return;
            }

            const audio = new Audio();
            this.currentAudio = audio;
            
            // For cross-origin if needed, but here same-origin is expected
            audio.crossOrigin = "anonymous";
            audio.src = url;
            audio.load();

            audio.onended = () => {
                console.log("🔊 AudioService: Reproducción terminada");
                this.currentAudio = null;
                resolve();
            };

            audio.onerror = (e) => {
                console.error("❌ AudioService: Error en audio element", e, audio.error);
                this.currentAudio = null;
                reject(audio.error || new Error("Unknown audio error"));
            };

            audio.play().then(() => {
                console.log("🔊 AudioService: Reproducción iniciada con éxito");
            }).catch((err) => {
                console.error("❌ AudioService: play() rechazado", err);
                reject(err);
            });
        });
    }
    
    stopAll() {
        if (this.currentAudio) {
            this.currentAudio.pause();
            this.currentAudio = null;
        }
    }
}

export const audioService = new AudioService();
