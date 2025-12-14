"""
Audio.py - Cattura audio di sistema - VERSIONE REALTIME
"""

import sounddevice as sd
import numpy as np
import asyncio
import queue
from typing import Optional

class AudioCapture:
    """Gestisce la cattura audio del sistema con buffer intelligente"""
    
    def __init__(self, assistant, loop: asyncio.AbstractEventLoop):
        self.assistant = assistant
        self.config = assistant.config
        self.stream: Optional[sd.InputStream] = None
        self.is_capturing = False
        self.audio_queue = queue.Queue()
        self.loop = loop
        self.process_task = None
        
        # Aggiungiamo per gestire device_id specifico
        self.device_id = None
        
        # Stato per il buffer intelligente
        self.audio_buffer = []
        self.buffer_start_time = None
        self.last_voice_time = None
        self.silence_start_time = None
        self.is_recording = False
        
    def find_audio_device(self) -> Optional[int]:
        """Trova dispositivo audio di monitoraggio"""
        try:
            devices = sd.query_devices()
            
            # Prima: se è stato specificato un device_id, usalo
            if self.device_id is not None:
                if 0 <= self.device_id < len(devices):
                    dev = devices[self.device_id]
                    if dev['max_input_channels'] > 0:
                        print(f"🎯 Usando dispositivo specificato #{self.device_id}: {dev['name']}")
                        return self.device_id
                    else:
                        print(f"⚠️  Dispositivo #{self.device_id} non ha input channels")
                else:
                    print(f"⚠️  Dispositivo #{self.device_id} non valido")
            
            # Cerca monitor/loopback
            for i, dev in enumerate(devices):
                name = dev['name'].lower()
                # Pattern comuni per monitor
                patterns = ['monitor', 'loopback', 'virtual', 'alsa']
                if any(p in name for p in patterns) and dev['max_input_channels'] > 0:
                    print(f"🎯 Trovato dispositivo: {dev['name']}")
                    return i
            
            # Usa default se non trovato
            default = sd.default.device[1]  # Input device
            if default is not None:
                print(f"📞 Usando dispositivo default: {devices[default]['name']}")
                return default
                
            # Prova a cercare qualsiasi dispositivo con input
            for i, dev in enumerate(devices):
                if dev['max_input_channels'] > 0:
                    print(f"📞 Usando dispositivo disponibile: {dev['name']}")
                    return i
                    
            return None
            
        except Exception as e:
            print(f"⚠️  Errore ricerca dispositivi: {e}")
            return None
    
    def start_capture(self):
        """Avvia cattura audio"""
        try:
            device_id = self.find_audio_device()
            
            if device_id is None:
                print("❌ Nessun dispositivo audio trovato!")
                return False
            
            def callback(indata, frames, time_info, status):
                """Callback sincrono - processa audio in tempo reale"""
                if status:
                    if status.input_overflow:
                        print("⚠️  Overflow input audio")
                
                if indata.size > 0:
                    # Converti a mono se stereo
                    if indata.ndim > 1 and indata.shape[1] > 1:
                        audio_mono = indata.mean(axis=1)
                    else:
                        audio_mono = indata.flatten()
                    
                    # Calcola energia audio (RMS)
                    rms = np.sqrt(np.mean(audio_mono**2))
                    current_time = time_info.inputBufferAdcTime
                    
                    # Soglia per rilevare voce
                    VOICE_THRESHOLD = 0.02
                    
                    if rms > VOICE_THRESHOLD:
                        # C'è voce
                        if not self.is_recording:
                            # Inizia una nuova registrazione
                            self.is_recording = True
                            self.audio_buffer = []
                            self.buffer_start_time = current_time
                            self.last_voice_time = current_time
                            self.silence_start_time = None
                            print("🎤 Inizio frase...")
                        
                        # Aggiorna ultimo tempo di voce
                        self.last_voice_time = current_time
                        self.silence_start_time = None
                        
                        # Aggiungi audio al buffer
                        self.audio_buffer.append(audio_mono.copy())
                        
                    else:
                        # Silenzio
                        if self.is_recording:
                            # Se è la prima volta che rileviamo silenzio
                            if self.silence_start_time is None:
                                self.silence_start_time = current_time
                            
                            # Calcola quanto silenzio abbiamo avuto
                            silence_duration = current_time - self.silence_start_time
                            
                            # Se abbiamo abbastanza audio e abbastanza silenzio, invia
                            if len(self.audio_buffer) > 0 and silence_duration > 1.0:
                                # Combina l'audio nel buffer
                                combined_audio = np.concatenate(self.audio_buffer)
                                
                                # Calcola durata effettiva
                                buffer_duration = len(combined_audio) / self.config.sample_rate
                                
                                if buffer_duration > 0.3:  # Almeno 300ms di voce
                                    # Invia alla coda per processamento asincrono
                                    try:
                                        self.audio_queue.put_nowait(combined_audio)
                                    except queue.Full:
                                        # Se la coda è piena, svuota e rimetti
                                        try:
                                            self.audio_queue.get_nowait()
                                            self.audio_queue.put_nowait(combined_audio)
                                        except:
                                            pass
                                    
                                    print(f"✅ Frase completata ({buffer_duration:.1f}s)")
                                
                                # Reset per la prossima frase
                                self.is_recording = False
                                self.audio_buffer = []
                                self.silence_start_time = None
                            else:
                                # Aggiungi comunque il silenzio al buffer (pause brevi nella frase)
                                self.audio_buffer.append(audio_mono.copy())
            
            # Configura stream
            self.stream = sd.InputStream(
                callback=callback,
                channels=1,
                samplerate=self.config.sample_rate,
                device=device_id,
                blocksize=int(self.config.sample_rate * 0.05),  # 50ms per maggiore reattività
                dtype=np.float32,
                latency='low'
            )
            
            self.stream.start()
            self.is_capturing = True
            
            # Avvia task asincrono per processare la coda
            self.process_task = self.loop.create_task(self.process_audio_queue())
            
            print(f"✅ Cattura audio avviata a {self.config.sample_rate}Hz")
            return True
            
        except Exception as e:
            print(f"❌ Errore avvio cattura audio: {e}")
            print(f"Dettagli: {type(e).__name__}")
            return False
    
    async def process_audio_queue(self):
        """Task asincrono che processa la coda audio"""
        while self.is_capturing:
            try:
                # Prende audio dalla coda con timeout breve
                audio_data = await self.loop.run_in_executor(
                    None, 
                    lambda: self.audio_queue.get(timeout=0.1)
                )
                
                if audio_data is not None and len(audio_data) > 0:
                    # Processa immediatamente
                    await self.assistant.process_audio_chunk_immediate(audio_data)
                    
            except queue.Empty:
                # Niente in coda, continua
                await asyncio.sleep(0.01)
            except Exception as e:
                print(f"⚠️  Errore processamento coda: {e}")
                await asyncio.sleep(0.1)
    
    def stop(self):
        """Ferma cattura audio"""
        self.is_capturing = False
        
        # Processa eventuale audio rimanente nel buffer
        if self.is_recording and len(self.audio_buffer) > 0:
            combined_audio = np.concatenate(self.audio_buffer)
            if len(combined_audio) > 0:
                try:
                    self.audio_queue.put_nowait(combined_audio)
                except:
                    pass
        
        if self.process_task and not self.process_task.done():
            self.process_task.cancel()
        
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
                print("⏹️  Cattura audio fermata")
            except:
                pass
