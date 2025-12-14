import asyncio
import numpy as np
import os
from dataclasses import dataclass
from typing import List, Dict, Optional
import aiohttp
import datetime
from ImprovedNotifier import ZenityNotifier, SimpleNotifier

@dataclass
class Config:
    """Configurazione dell'assistente"""
    
    # Audio settings
    sample_rate: int = 16000
    chunk_duration: float = 10.0
    whisper_model: str = "base"
    
    # DeepSeek settings
    @property
    def deepseek_api_key(self) -> str:
        """Ottiene API key da variabile d'ambiente"""
        api_key = os.getenv('DEEPSEEK_API_KEY', '')
        if not api_key:
            api_key = self._read_api_key_from_env_file()
        return api_key
    
    # Device settings
    device: str = "cpu"
    compute_type: str = "int8"
    language: str = "it"
    
    # Advanced settings
    vad_enabled: bool = True
    beam_size: int = 3
    temperature: float = 0.0
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def _read_api_key_from_env_file(self) -> str:
        """Legge API key da file .env"""
        env_file = os.path.join(os.path.dirname(__file__), '.env')
        if os.path.exists(env_file):
            try:
                with open(env_file, 'r') as f:
                    for line in f:
                        if line.strip() and not line.startswith('#'):
                            key, value = line.strip().split('=', 1)
                            if key == 'DEEPSEEK_API_KEY':
                                return value.strip('"\'')
            except:
                pass
        return ""
    
    def validate(self) -> bool:
        """Valida la configurazione"""
        if not self.deepseek_api_key:
            print("❌ ERRORE: API key non configurata!")
            print("\nPer configurarla:")
            print("1. export DEEPSEEK_API_KEY='tua-api-key'")
            print("2. O crea file .env: DEEPSEEK_API_KEY=\"tua-api-key\"")
            return False
        
        if self.whisper_model not in ['tiny', 'base', 'small', 'medium']:
            print(f"❌ Modello non valido: {self.whisper_model}")
            return False
        
        return True


class ConferenceAssistant:
    """Assistente per videoconferenze"""
    
    def __init__(self, config: Config):
        self.config = config
        self.is_running = True
        
        # Buffer conversazione
        self.current_audio_buffer = []
        self.buffer_duration = 0
        self.buffer_max_duration = 5.0
        self.full_conversation = []
        self.max_conversation_items = 50
        self.log_file = "conversazione_log.txt"
        
        # Tracker silenzio
        self.last_speech_time = 0
        self.silence_start_time = 0
        self.in_speech = False
        self.speech_threshold = 0.01
        self.silence_threshold = 1.5
        
        # Session HTTP
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Inizializza trascrittore
        self.transcriber = self._init_transcriber()
        
        # Notifica di avvio
        SimpleNotifier.send_simple_notification(
            "🎯 Assistente Meeting Attivo",
            "Pronto! Usa S per suggerimenti",
            duration=5000
        )
    
    def _init_transcriber(self):
        """Inizializza il modello di trascrizione"""
        try:
            from faster_whisper import WhisperModel
            
            print(f"🎙️  Caricamento modello Whisper ({self.config.whisper_model})...")
            
            model = WhisperModel(
                model_size_or_path=self.config.whisper_model,
                device=self.config.device,
                compute_type=self.config.compute_type,
                cpu_threads=4,
                num_workers=2
            )
            
            print(f"✅ Modello caricato su {self.config.device.upper()}")
            return model
            
        except ImportError:
            raise ImportError("Installa faster-whisper: pip install faster-whisper")
    
    async def start_session(self):
        """Avvia sessione HTTP"""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession()
    
    async def stop_session(self):
        """Chiude sessione HTTP"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    async def process_audio_chunk_immediate(self, audio_data: np.ndarray):
        """Processa immediatamente un chunk di audio"""
        if not self.is_running or audio_data.size == 0:
            return
        
        duration = len(audio_data) / self.config.sample_rate
        print(f"📊 Audio ricevuto: {duration:.2f} secondi")
        
        # Normalizza
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
        
        max_val = np.abs(audio_data).max()
        if max_val > 0:
            audio_data = audio_data / max_val
        
        await self._transcribe_and_display_immediate(audio_data, duration)
    
    async def _transcribe_and_display_immediate(self, audio_data: np.ndarray, duration: float):
        """Trascrizione immediata e display"""
        try:
            vad_params = {
                "min_silence_duration_ms": 500,
                "threshold": 0.3,
                "speech_pad_ms": 200,
                "min_speech_duration_ms": 200
            }
            
            segments, _ = self.transcriber.transcribe(
                audio_data,
                language=self.config.language,
                beam_size=self.config.beam_size,
                vad_filter=True,
                vad_parameters=vad_params,
                temperature=self.config.temperature,
                word_timestamps=False,
                condition_on_previous_text=False
            )
            
            for seg in segments:
                text = seg.text.strip()
                seg_duration = seg.end - seg.start
                
                if len(text) > 1 and seg_duration > 0.2:
                    print(f"\n💬 [{self.config.language.upper()}] (durata: {seg_duration:.1f}s): {text}")
                    
                    self._save_to_file(text)
                    self.full_conversation.append(text)
                    
                    if len(self.full_conversation) > self.max_conversation_items:
                        self.full_conversation = self.full_conversation[-self.max_conversation_items:]
        
        except Exception as e:
            print(f"❌ Errore trascrizione: {e}")
    
    def _save_to_file(self, transcript: str):
        """Salva trascrizione su file"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {transcript}\n")
        except Exception as e:
            print(f"⚠️  Errore salvataggio: {e}")
    
    async def get_suggestions_from_conversation(self):
        """Ottieni suggerimenti con finestra Zenity grande"""
        if not self.full_conversation:
            ZenityNotifier.show_notification(
                "Nessuna Conversazione",
                "Non c'è ancora nulla da analizzare.\n\nParla nella videochiamata e riprova.",
                notification_type="warning",
                timeout=10
            )
            return
        
        # Notifica breve di attesa
        SimpleNotifier.send_simple_notification(
            "⏳ Analisi in Corso",
            "DeepSeek AI sta analizzando...",
            duration=3000
        )
        
        recent_conversation = self.full_conversation[-20:] if len(self.full_conversation) > 20 else self.full_conversation
        context = "\n".join([f"{i+1}. {text}" for i, text in enumerate(recent_conversation)])
        
        messages = [
            {
                "role": "system",
                "content": "Sei un assistente per meeting professionali. Analizza la conversazione e fornisci 3 suggerimenti pratici per rispondere o procedere. Sii conciso."
                },
            {
                "role": "user",
                "content": f"Analizza questa conversazione e suggerisci le prossime mosse:\n\n{context}\n\nFornisci 3 suggerimenti brevi e pratici:"
            }
        ]
        
        await self._call_deepseek_api(
            messages, 
            max_tokens=400, 
            title="💡 SUGGERIMENTI AI",
            notification_title="Suggerimento"
        )
    
    async def get_summary(self):
        """Ottieni riassunto con finestra Zenity grande"""
        if not self.full_conversation:
            ZenityNotifier.show_notification(
                "Nessuna Conversazione",
                "Non c'è nulla da riassumere.\n\nParla nella videochiamata prima.",
                notification_type="warning",
                timeout=10
            )
            return
        
        # Notifica breve di attesa
        SimpleNotifier.send_simple_notification(
            "⏳ Generazione Riassunto",
            "Sto analizzando il meeting...",
            duration=3000
        )
        
        context = "\n".join(self.full_conversation)
        
        messages = [
            {
                "role": "system", 
                "content": "Sei un assistente che crea riassunti di meeting professionali. Fornisci un riassunto strutturato con massimo 5 punti chiave. Usa bullet points."
            },
            {
                "role": "user",
                "content": f"Crea un riassunto professionale di questo meeting:\n\n{context}\n\nRiassumi in 5 punti chiave:"
            }
        ]
        
        await self._call_deepseek_api(
            messages, 
            max_tokens=350, 
            title="📋 RIASSUNTO MEETING",
            notification_title="Riassunto del Meeting"
        )
    
    def clear_conversation(self):
        """Pulisce la conversazione"""
        count = len(self.full_conversation)
        self.full_conversation = []
        print(f"\n🗑️  Conversazione pulita ({count} elementi rimossi)")
        
        SimpleNotifier.send_simple_notification(
            "🗑️ Conversazione Pulita",
            f"Cronologia cancellata: {count} messaggi",
            duration=3000
        )
    
    async def _call_deepseek_api(self, messages: List[Dict], max_tokens: int = 150, 
                                  title: str = "💡 RISPOSTA", 
                                  notification_title: str = "Risposta AI"):
        """Chiamata API con finestra Zenity grande"""
        if not self.config.deepseek_api_key:
            ZenityNotifier.show_notification(
                "Errore Configurazione",
                "API Key DeepSeek non configurata.\n\nConfigura DEEPSEEK_API_KEY",
                notification_type="error",
                timeout=15
            )
            return
        
        try:
            await self.start_session()
            
            async with self.session.post(
                "https://api.deepseek.com/v1/chat/completions",
                json={
                    "model": "deepseek-chat",
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.1
                },
                headers={
                    "Authorization": f"Bearer {self.config.deepseek_api_key}",
                    "Content-Type": "application/json"
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    suggestion = result["choices"][0]["message"]["content"]
                    
                    # Stampa su terminale
                    print("\n" + "╔" * 70)
                    print(title)
                    print("╔" * 70)
                    print(suggestion)
                    print("╔" * 70 + "\n")
                    
                    # Finestra Zenity GRANDE per leggere bene
                    ZenityNotifier.show_notification(
                        notification_title,
                        suggestion,
                        notification_type="suggestion",
                        timeout=30  # 30 secondi per leggere
                    )
                    
                else:
                    error = await response.text()
                    print(f"⚠️  Errore API ({response.status}): {error[:200]}")
                    ZenityNotifier.show_notification(
                        "Errore API",
                        f"Errore {response.status}\n\n{error[:150]}",
                        notification_type="error",
                        timeout=15
                    )
                    
        except asyncio.TimeoutError:
            print("⏰ Timeout connessione API")
            ZenityNotifier.show_notification(
                "Timeout API",
                "La richiesta ha impiegato troppo tempo.\n\nRiprova tra qualche secondo.",
                notification_type="warning",
                timeout=10
            )
        except Exception as e:
            print(f"⚠️  Errore API: {e}")
            ZenityNotifier.show_notification(
                "Errore Connessione",
                f"Impossibile connettersi a DeepSeek.\n\nErrore: {str(e)[:100]}",
                notification_type="error",
                timeout=15
            )
    
    async def stop_async(self):
        """Arresto ordinato"""
        print("\n🛑 Arresto assistente...")
        self.is_running = False
        
        if self.current_audio_buffer:
            await self._process_buffer_immediate()
        
        if self.session and not self.session.closed:
            try:
                await asyncio.wait_for(self.stop_session(), timeout=2.0)
            except:
                pass
        
        # Notifica chiusura
        SimpleNotifier.send_simple_notification(
            "👋 Assistente Arrestato",
            "Grazie per aver usato l'assistente!",
            duration=3000
        )
        
        print("✅ Assistente arrestato")
    
    async def _process_buffer_immediate(self):
        """Processa buffer immediato (placeholder per compatibilità)"""
        pass
