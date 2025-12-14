#!/usr/bin/env python3
"""
Main.py - Assistente Videoconferenze
"""

import asyncio
import sys
import argparse
import warnings
from pipeline import Config, ConferenceAssistant
from Audio import AudioCapture
from pynput import keyboard

warnings.filterwarnings('ignore', message='pkg_resources is deprecated')

class GlobalHotkeyManager:
    """Gestisce hotkey globali"""
    
    def __init__(self, assistant: ConferenceAssistant, loop: asyncio.AbstractEventLoop):
        self.assistant = assistant
        self.loop = loop
        self.listener = None
        self.current_keys = set()
        self.should_exit = False
        
        # Hotkey combinations
        self.hotkeys = {
            frozenset([keyboard.KeyCode.from_char('s')]): self.on_suggestions,
            frozenset([keyboard.Key.ctrl_l, keyboard.Key.alt_l, keyboard.KeyCode.from_char('r')]): self.on_summary,
            frozenset([keyboard.Key.ctrl_l, keyboard.Key.alt_l, keyboard.KeyCode.from_char('c')]): self.on_clear,
            frozenset([keyboard.KeyCode.from_char('q')]): self.on_quit,
            # Supporta anche ctrl/alt destro
            frozenset([keyboard.Key.ctrl_r, keyboard.Key.alt_r, keyboard.KeyCode.from_char('s')]): self.on_suggestions,
            frozenset([keyboard.Key.ctrl_r, keyboard.Key.alt_r, keyboard.KeyCode.from_char('r')]): self.on_summary,
            frozenset([keyboard.Key.ctrl_r, keyboard.Key.alt_r, keyboard.KeyCode.from_char('c')]): self.on_clear,
            frozenset([keyboard.Key.ctrl_r, keyboard.Key.alt_r, keyboard.KeyCode.from_char('q')]): self.on_quit,
        }
    
    def on_press(self, key):
        """Callback tasto premuto"""
        try:
            if hasattr(key, 'char') and key.char:
                normalized_key = keyboard.KeyCode.from_char(key.char.lower())
            else:
                normalized_key = key
            
            self.current_keys.add(normalized_key)
            
            for hotkey_combo, action in self.hotkeys.items():
                if hotkey_combo.issubset(self.current_keys):
                    asyncio.run_coroutine_threadsafe(action(), self.loop)
        except:
            pass
    
    def on_release(self, key):
        """Callback tasto rilasciato"""
        try:
            if hasattr(key, 'char') and key.char:
                normalized_key = keyboard.KeyCode.from_char(key.char.lower())
            else:
                normalized_key = key
            
            if normalized_key in self.current_keys:
                self.current_keys.remove(normalized_key)
        except:
            pass
    
    async def on_suggestions(self):
        """Hotkey: Suggerimenti"""
        print("\n🔥 [S] Richiesta suggerimenti...")
        await self.assistant.get_suggestions_from_conversation()
    
    async def on_summary(self):
        """Hotkey: Riassunto"""
        print("\n📋 [Ctrl+Alt+R] Richiesta riassunto...")
        await self.assistant.get_summary()
    
    async def on_clear(self):
        """Hotkey: Pulisci"""
        print("\n🗑️  [Ctrl+Alt+C] Pulizia conversazione...")
        self.assistant.clear_conversation()
    
    async def on_quit(self):
        """Hotkey: Esci"""
        print("\n👋 [Q] Uscita richiesta...")
        self.should_exit = True
    
    def start(self):
        """Avvia listener"""
        self.listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        )
        self.listener.start()
        print("✅ Hotkey globali attivate")
    
    def stop(self):
        """Ferma listener"""
        if self.listener:
            self.listener.stop()


def parse_args():
    """Parser argomenti"""
    parser = argparse.ArgumentParser(
        description='Assistente videoconferenze con AI',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--model', default='base',
                       choices=['tiny', 'base', 'small', 'medium'],
                       help='Modello Whisper (default: base)')
    
    parser.add_argument('--language', default='it',
                       help='Lingua trascrizione (default: it)')
    
    parser.add_argument('--device', default='cpu',
                       choices=['cpu', 'cuda'],
                       help='Dispositivo inferenza (default: cpu)')
    
    parser.add_argument('--sample-rate', type=int, default=16000,
                       help='Sample rate audio (default: 16000)')
    
    parser.add_argument('--audio-device', type=int, default=None,
                       help='ID dispositivo audio')
    
    parser.add_argument('--list-devices', action='store_true',
                       help='Lista dispositivi audio')
    
    parser.add_argument('--debug', action='store_true',
                       help='Output debug')
    
    return parser.parse_args()


def list_audio_devices():
    """Lista dispositivi audio"""
    import sounddevice as sd
    devices = sd.query_devices()
    
    print("\n" + "="*80)
    print("🎧 DISPOSITIVI AUDIO DISPONIBILI")
    print("="*80)
    
    for i, dev in enumerate(devices):
        channels = dev['max_input_channels']
        status = "🎤 " if channels > 0 else "🔇 "
        dev_type = "INPUT" if channels > 0 else "OUTPUT"
        name = dev['name']
        
        print(f"\n{status}ID {i}: {name}")
        print(f"   Tipo: {dev_type}")
        print(f"   Canali input: {channels}")
        print(f"   Sample rate: {dev['default_samplerate']}Hz")
        
        if 'monitor' in name.lower() or 'loopback' in name.lower():
            print(f"   💡 SUGGERIMENTO: --audio-device {i}")
    
    print("\n" + "="*80)


def print_banner():
    """Banner applicazione"""
    banner = """
    ╔═══════════════════════════════════════════════════════╗
    ║          🎯 ASSISTENTE VIDEOCONFERENZE               ║
    ║       Trascrizione Real-time + DeepSeek AI           ║
    ║          🔔 Notifiche Zenity Adattive                ║
    ╚═══════════════════════════════════════════════════════╝
    """
    print(banner)


async def main():
    
    args = parse_args()
    
    if args.list_devices:
        list_audio_devices()
        return
    
    print_banner()
    
    # Configurazione
    config = Config(
        whisper_model=args.model,
        language=args.language,
        device=args.device,
        sample_rate=args.sample_rate,
        chunk_duration=20.0,
        vad_enabled=True,
        vad_parameters={
            "min_silence_duration_ms": 1000,
            "threshold": 0.5,
            "speech_pad_ms": 300,
            "min_speech_duration_ms": 300
        }
    )
    
    if not config.validate():
        sys.exit(1)
    
    # Mostra configurazione
    print("\n" + "╔" * 60)
    print("⚙️  CONFIGURAZIONE")
    print("╔" * 60)
    print(f"• Modello Whisper:      {config.whisper_model}")
    print(f"• Lingua:               {config.language}")
    print(f"• Dispositivo:          {config.device}")
    print(f"• Sample rate:          {config.sample_rate} Hz")
    print(f"• Dispositivo audio:    {args.audio_device or 'Auto'}")
    print(f"• API Key:              {'✅ Configurata' if config.deepseek_api_key else '❌ Non configurata'}")
    print("╔" * 60 + "\n")
    
    # Inizializza componenti
    assistant = None
    audio_capture = None
    hotkey_manager = None
    
    try:
        assistant = ConferenceAssistant(config)
        loop = asyncio.get_running_loop()
        
        # Audio capture
        audio_capture = AudioCapture(assistant, loop)
        if args.audio_device is not None:
            audio_capture.device_id = args.audio_device
        
        # Hotkey manager
        hotkey_manager = GlobalHotkeyManager(assistant, loop)
        hotkey_manager.start()
        
    except Exception as e:
        print(f"❌ Errore inizializzazione: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    
    try:
        # Avvia cattura audio
        print("\n" + "─" * 60)
        print("🚀 Avvio cattura audio...")
        if not audio_capture.start_capture():
            print("❌ Impossibile avviare cattura audio")
            print("\n💡 Suggerimenti:")
            print("1. Usa '--list-devices'")
            print("2. Specifica '--audio-device X'")
            return
        
        # Istruzioni
        print("\n" + "─" * 60)
        print("✅ TUTTO PRONTO!")
        print("\n🎙️  Parla nella videoconferenza...")
        print("📝 Le trascrizioni appariranno nel terminale")
        print("🪟 I suggerimenti AI appariranno in notifica")
        
        print("\n⌨️  HOTKEY GLOBALI (sempre attive):")
        print("   • S - Suggerimenti AI 💡")
        print("   • Ctrl+Alt+R - Riassunto meeting 📋")
        print("   • Ctrl+Alt+C - Pulisci conversazione 🗑️")
        print("   • Q - Esci dal programma 👋")
        
        print("\n💡 TIP: Puoi minimizzare questa finestra!")
        print("   Le finestre di notifica continueranno ad apparire.")
        print("─" * 60 + "\n")
        
        # Loop principale
        while not hotkey_manager.should_exit:
            await asyncio.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Ctrl+C rilevato. Arresto...")
    except Exception as e:
        print(f"\n❌ Errore esecuzione: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
    finally:
        print("\n⏳ Pulizia in corso...")
        
        if hotkey_manager:
            hotkey_manager.stop()
        
        if audio_capture:
            audio_capture.stop()
        
        if assistant:
            await assistant.stop_async()
        
        print("✅ Pulizia completata")
        print("👋 Arrivederci!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Programma terminato")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Errore fatale: {e}")
        sys.exit(1)