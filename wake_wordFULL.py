import os
import pyaudio
import requests
import base64
import subprocess
import wave
import time
from pocketsphinx import Decoder, Config
from webrtc_noise_gain import AudioProcessor

# --- CONFIGURATION API IRIS ---
API_URL = "https://iris.qoyri.fr"
PI_KEY = "irpi_llaXj8DrXfFs9rNVs4QhmB5cCFtW_7R4sUNGL-DAMIs"
HEADERS = {"X-Pi-Key": PI_KEY, "Content-Type": "application/json"}

def envoyer_evenement(type_event):
    try:
        requests.post(f"{API_URL}/api/pi/event", json={"type": type_event}, headers=HEADERS, timeout=5)
    except Exception as e:
        print(f"Erreur reseau (Event): {e}")

def save_audio_to_wav(pcm_bytes, rate=48000):
    """Sauvegarde le PCM brut de l'API en un vrai fichier WAV lisible partout."""
    # On cree un nom de fichier unique avec l'heure actuelle
    nom_fichier = f"reponse_iris_{int(time.time())}.wav"
    
    # On fabrique le fichier WAV avec les specifications de l'API IRIS
    with wave.open(nom_fichier, 'wb') as wf:
        wf.setnchannels(1)        # 1 canal (Mono)
        wf.setsampwidth(2)        # 2 octets pour du 16-bit
        wf.setframerate(rate)     # Frequence d'echantillonnage (48kHz)
        wf.writeframes(pcm_bytes) # On injecte le son brut
        
    print(f" [DEBUG] Fichier audio sauvegarde avec succes : {nom_fichier}")
    return nom_fichier

def main():
    print("Initialisation du pipeline audio IRIS avec WebRTC...")
    
    # 1. Configuration WebRTC APM (Noise Suppression max, leger Auto Gain)
    processor = AudioProcessor(3, 4)

    # 2. Configuration PocketSphinx (Syntaxe propre avec kwargs)
    config = Config(
        hmm='/home/iris/iris_vision/venv_iris/lib/python3.13/site-packages/pocketsphinx/model/fr-fr/fr-fr',
        dict='/home/iris/iris_vision/venv_iris/lib/python3.13/site-packages/pocketsphinx/model/fr-fr/fr-fr.dict',
        keyphrase='iris',
        kws_threshold=1e-15,
        lm=None,              # <-- Le secret est ici : on detruit le parametre par defaut !
        logfn='/dev/null'     # <-- On cache les logs techniques illisibles
    )
    
    decoder = Decoder(config)

    # 3. Ouverture de l'UNIQUE flux micro UGREEN
    p = pyaudio.PyAudio()
    rate = 16000
    frames_per_10ms = int(rate / 100) # 160 frames

    stream = p.open(format=pyaudio.paInt16, 
                    channels=1, 
                    rate=rate, 
                    input=True, 
                    input_device_index=0, # <-- Le micro UGREEN est le 0
                    frames_per_buffer=frames_per_10ms)

    decoder.start_utt()
    print("\nIRIS est pret et a l'ecoute. (Dis 'iris')")

    try:
        while True:
            # On lit un bloc de 10ms depuis le micro
            raw_chunk = stream.read(frames_per_10ms, exception_on_overflow=False)
            
            # On le nettoie avec WebRTC
            webrtc_result = processor.Process10ms(raw_chunk)
            clean_chunk = bytes(webrtc_result.audio)
            
            # On donne le bloc propre a analyser a PocketSphinx
            decoder.process_raw(clean_chunk, False, False)
            
            # Si PocketSphinx a reconnu le mot...
            if decoder.hyp() is not None:
                print("\n--- WAKE WORD DETECTE ! ---")
                envoyer_evenement("wake_word")
                
                # On cloture la recherche du mot pour cette fois
                decoder.end_utt() 
                
                print("ENREGISTREMENT EN COURS (5 sec)... Parle maintenant !")
                
                # On va enregistrer 5 secondes en utilisant le meme micro ouvert
                clean_audio_buffer = bytearray()
                total_chunks = int((rate * 5) / frames_per_10ms) # 500 blocs de 10ms
                
                for _ in range(total_chunks):
                    r_chunk = stream.read(frames_per_10ms, exception_on_overflow=False)
                    res = processor.Process10ms(r_chunk)
                    clean_audio_buffer.extend(res.audio)
                
                print("Enregistrement termine. Envoi a l'API Elixir...")
                
                # Envoi a l'API
                try:
                    reponse = requests.post(f"{API_URL}/api/pi/voice", json={
                        "audio": base64.b64encode(clean_audio_buffer).decode('utf-8')
                    }, headers=HEADERS, timeout=30)
                    
                    if reponse.status_code == 200:
                        data = reponse.json()
                        print(f"Vous : {data.get('transcript', '')}")
                        print(f"IRIS : {data.get('response', '')}")
                        
                        if data.get("audio"):
                            audio_bytes = base64.b64decode(data["audio"])
                            fichier_wav = save_audio_to_wav(audio_bytes)
                            
                            print("Lecture de la reponse sur l'enceinte Bose (via SoX)...")
                            # La commande 'play' de SoX gere nativement le Bluetooth
                            subprocess.run(["play", "-q", fichier_wav]) 
                            
                            # Nettoyage
                            import os
                            os.remove(fichier_wav)
                    else:
                        print(f"Erreur API: Code {reponse.status_code}")
                except Exception as e:
                    print(f"Erreur de communication API: {e}")
                
                print("\nRetour au mode ecoute. (Dis 'iris')")
                # On relance la recherche du wake word
                decoder.start_utt()

    except KeyboardInterrupt:
        print("\nArret du systeme...")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

if __name__ == '__main__':
    main()