"""
ImprovedNotifier.py - Sistema di notifiche per Ubuntu
"""

import subprocess
import re
import threading
import time
import tempfile
import os

class ZenityNotifier:
    """Notifiche usando Zenity """
    
    @staticmethod
    def get_screen_dimensions():
        """Ottiene le dimensioni dello schermo"""
        try:
            result = subprocess.run(
                ['xrandr', '--current'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            for line in result.stdout.split('\n'):
                if ' connected primary' in line or '* connected' in line or ' connected' in line:
                    match = re.search(r'(\d+)x(\d+)', line)
                    if match:
                        return int(match.group(1)), int(match.group(2))
            return 1920, 1080
        except:
            return 1366, 768
    
    @staticmethod
    def format_text(text: str):
        """Formatta il testo rimuovendo markdown e migliorando leggibilità"""
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'\*\*(.+?)\*\*', lambda m: m.group(1).upper(), text)
        text = re.sub(r'\*(.+?)\*', r'\1', text)
        text = re.sub(r'`(.+?)`', r'\1', text)
        text = re.sub(r'^\s*[-*•]\s+', '• ', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*(\d+)\.\s+', r'\1. ', text, flags=re.MULTILINE)
        text = re.sub(r'\n\n+', '\n\n', text)
        return text.strip()
    
    @staticmethod
    def show_info_dialog_simple(title: str, message: str, width: int = 500, height: int = 400, timeout: int = 25):
        
        try:
            formatted_message = ZenityNotifier.format_text(message)
            
            screen_width, screen_height = ZenityNotifier.get_screen_dimensions()
            
            # Calcola dimensioni sicure
            safe_width = min(width, int(screen_width * 0.8))
            safe_height = min(height, int(screen_height * 0.7))
            
            # Usa --info normale (che non ha problemi di finestra nera)
            cmd = [
                'zenity',
                '--info',
                '--title', title,
                '--text', formatted_message,
                '--width', str(safe_width),
                '--height', str(safe_height),
                '--no-wrap',
                '--ok-label', 'OK'
            ]
            
            if timeout > 0:
                cmd.extend(['--timeout', str(timeout)])
            
            def run_zenity():
                subprocess.run(cmd, check=False, 
                             stderr=subprocess.DEVNULL, 
                             stdout=subprocess.DEVNULL)
            
            thread = threading.Thread(target=run_zenity, daemon=True)
            thread.start()
            
            return True
            
        except Exception as e:
            print(f"⚠️  Errore notifica: {e}")
            return False
    
    @staticmethod
    def show_info_dialog_large_font(title: str, message: str, width: int = 700, height: int = 500, timeout: int = 25):
       
        try:
            formatted_message = ZenityNotifier.format_text(message)
            
            screen_width, screen_height = ZenityNotifier.get_screen_dimensions()
            
            # Calcola dimensioni sicure
            safe_width = min(width, int(screen_width * 0.8))
            safe_height = min(height, int(screen_height * 0.7))
            
            # Crea un file temporaneo per il testo
            # Questo evita problemi con caratteri speciali sulla command line
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(formatted_message)
                temp_file = f.name
            
            try:
                # Usa --text-info leggendo da file
                cmd = [
                    'zenity',
                    '--text-info',
                    '--title', title,
                    '--width', str(safe_width),
                    '--height', str(safe_height),
                    '--filename', temp_file,
                    '--font', 'Sans 12',  # Font leggermente più grande
                    '--ok-label', 'Chiudi'
                ]
                
                if timeout > 0:
                    cmd.extend(['--timeout', str(timeout)])
                
                def run_zenity():
                    subprocess.run(cmd, check=False, 
                                 stderr=subprocess.DEVNULL, 
                                 stdout=subprocess.DEVNULL)
                    # Pulisci il file temporaneo
                    try:
                        os.unlink(temp_file)
                    except:
                        pass
                
                thread = threading.Thread(target=run_zenity, daemon=True)
                thread.start()
                
                return True
            except:
                # Fallback se qualcosa va storto
                try:
                    os.unlink(temp_file)
                except:
                    pass
                return False
                
        except Exception as e:
            print(f"⚠️  Errore notifica con font grande: {e}")
            return False
    
    @staticmethod
    def show_info_dialog(title: str, message: str, width: int = 500, height: int = 400, timeout: int = 25):
        """
        Mostra finestra di dialogo - decide automaticamente quale metodo usare
        """
        # Per messaggi brevi, usa versione semplice
        # Per messaggi lunghi, prova quella con font grande
        lines = message.split('\n')
        num_lines = len(lines)
        
        if num_lines > 20 or len(message) > 1500:
            # Prova con font grande per messaggi lunghi
            success = ZenityNotifier.show_info_dialog_large_font(
                title, message, width, height, timeout
            )
            
            if not success:
                # Fallback a versione semplice
                return ZenityNotifier.show_info_dialog_simple(
                    title, message, width, height, timeout
                )
            return success
        else:
            # Per messaggi brevi, usa versione semplice
            return ZenityNotifier.show_info_dialog_simple(
                title, message, width, height, timeout
            )
    
    @staticmethod
    def show_notification(title: str, message: str, notification_type: str = "info", timeout: int = 25):
        """
        Mostra notifica con dimensioni ottimizzate
        """
        emoji_map = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "question": "❓",
            "suggestion": "💡"
        }
        
        emoji = emoji_map.get(notification_type, "ℹ️")
        full_title = f"{emoji} {title}"
        
        lines = message.split('\n')
        num_lines = len(lines)
        
        if num_lines > 15 or len(message) > 1000:
            # Messaggio lungo: dimensioni più grandi
            screen_width, screen_height = ZenityNotifier.get_screen_dimensions()
            max_height = min(600, int(screen_height * 0.7))
            height = min(300 + (num_lines * 20), max_height)
            height = max(height, 400)
            
            adjusted_timeout = min(timeout + 15, 60)
            
            # Per messaggi lunghi, preferisci il metodo con font grande
            return ZenityNotifier.show_info_dialog_large_font(
                full_title, 
                message, 
                width=800,
                height=height,
                timeout=adjusted_timeout
            )
        else:
            # Messaggio normale
            return ZenityNotifier.show_info_dialog_simple(
                full_title, 
                message, 
                width=700,
                height=450,
                timeout=timeout
            )
    
    @staticmethod
    def show_text_dialog(title: str, text: str, width: int = 700, height: int = 500):
        """Alias per compatibilità"""
        return ZenityNotifier.show_info_dialog(title, text, width, height, timeout=0)
    
    @staticmethod
    def show_notification_with_fallback(title: str, message: str, notification_type: str = "info"):
        """Prova Zenity, se fallisce usa notify-send"""
        success = ZenityNotifier.show_notification(title, message, notification_type)
        
        if not success:
            try:
                short_msg = message[:500] + ("..." if len(message) > 500 else "")
                subprocess.run([
                    'notify-send',
                    '-u', 'normal',
                    '-t', '15000',
                    title,
                    short_msg
                ], check=False, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            except:
                print(f"⚠️  Impossibile mostrare notifica: {title}")


class SimpleNotifier:
    """Notifiche semplici con notify-send"""
    
    @staticmethod
    def send_simple_notification(title: str, message: str, duration: int = 10000):
        """Notifica breve con notify-send"""
        try:
            short_message = message[:200] + "..." if len(message) > 200 else message
            
            subprocess.run([
                'notify-send',
                '-u', 'normal',
                '-t', str(duration),
                '-i', 'dialog-information',
                title,
                short_message
            ], check=False, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            
        except Exception as e:
            print(f"⚠️  Errore notifica: {e}")


# Test con finestre funzionanti
if __name__ == "__main__":
    print("Test notifiche con caratteri più grandi (finestra funzionante)...")
    
    # Test 1: Notifica breve semplice
    SimpleNotifier.send_simple_notification(
        "Test Finestra Funzionante",
        "Questa notifica usa il metodo semplice senza problemi"
    )
    
    time.sleep(1)
    
    # Test 2: Notifica media con caratteri normali
    medium_message = """
**PROMEMORIA RIUNIONE**

• Data: Oggi, 15:00
• Luogo: Sala Conferenze A
• Argomento: Revisione Progetto Q4

**DA PORTARE:**
1. Report di avanzamento
2. Presentazione 10 min
3. Budget allocato
"""
    
    print("Mostrando notifica media (metodo semplice)...")
    ZenityNotifier.show_notification(
        "Promemoria Riunione",
        medium_message,
        notification_type="warning",
        timeout=30
    )
    
    time.sleep(2)
    
    # Test 3: Notifica lunga con font più grande (se supportato)
    long_message = """
**ISTRUZIONI DETTAGLIATE PER IL PROGETTO:**

**FASE 1 - ANALISI (COMPLETATA)**
• Raccolta requisiti utente
• Analisi fattibilità tecnica
• Stima risorse necessarie

**FASE 2 - PROGETTAZIONE (IN CORSO)**
• Design architetturale
• Definizione API
• Scelta tecnologie

**FASE 3 - SVILUPPO (PROSSIMA)**
• Implementazione core
• Testing unità
• Documentazione codice

**SCADENZE IMPORTANTI:**
- 15 Novembre: Review design
- 30 Novembre: Inizio sviluppo
- 15 Dicembre: Prima release beta

**NOTE TECNICHE:**
• Usare Python 3.9+
• Database PostgreSQL 14
• API REST con FastAPI
• Frontend React 18

**CONTATTI:**
• PM: Maria Rossi (maria@azienda.com)
• Tech Lead: Luca Bianchi (luca@azienda.com)
• Supporto: help@azienda.com
"""
    
    print("Mostrando notifica lunga (tenterà font più grande)...")
    success = ZenityNotifier.show_notification(
        "Istruzioni Progetto Dettagliate",
        long_message,
        notification_type="info",
        timeout=40
    )
    
    if success:
        print("✅ Test completato! Notifiche mostrate correttamente.")
    else:
        print("⚠️  Fallback a metodo semplice...")
        # Prova con metodo semplice come fallback
        ZenityNotifier.show_notification(
            "Istruzioni Progetto Dettagliate",
            "Vedi il documento completo per le istruzioni dettagliate.",
            notification_type="info",
            timeout=30
        )