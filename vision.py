import cv2
import mediapipe as mp
import requests
import time
import base64

# --- CONFIGURATION API IRIS ---
API_URL = "https://iris.qoyri.fr"
PI_KEY = "irpi_llaXj8DrXfFs9rNVs4QhmB5cCFtW_7R4sUNGL-DAMIs" # A REMPLACER PAR TA VRAIE CLE
HEADERS = {"X-Pi-Key": PI_KEY, "Content-Type": "application/json"}

# --- CONFIGURATION CAMERA ---
# Utilise l'URL de DroidCam ou remplace par 0 si tu branches une webcam USB
VIDEO_SOURCE = "http://127.0.0.1:4747/video" 

def send_image_to_api(frame):
    """Encode l'image OpenCV en JPEG Base64 et l'envoie a l'API."""
    print("\n[VISION] Preparation de l'image pour l'API...")
    
    # 1. On compresse l'image brute d'OpenCV en format JPEG
    succes, buffer = cv2.imencode('.jpg', frame)
    if not succes:
        print("Erreur: Impossible d'encoder l'image en JPEG.")
        return
    
    img_bytes = buffer.tobytes()
    
    # 2. On l'encode en Base64 pour le transfert JSON
    img_base64 = base64.b64encode(img_bytes).decode('utf-8')
    
    # 3. On envoie a la route /api/pi/image de ton serveur HTTPS
    print("Envoi en cours...")
    try:
        response = requests.post(
            f"{API_URL}/api/pi/image",
            json={"image": img_base64},
            headers=HEADERS,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            # L'API renvoie l'URL de l'image stockee
            print(f"-> Succes ! Image sauvegardee : {data.get('url', 'URL inconnue')}")
        else:
            print(f"-> Erreur API lors de l'envoi d'image: {response.status_code}")
            
    except Exception as e:
        print(f"-> Erreur reseau : {e}")

def main():
    print("Initialisation de la Vision IRIS...")
    
    # 1. Initialisation de MediaPipe (L'Expert)
    mp_hands = mp.solutions.hands
    # max_num_hands=1 pour economiser le CPU, on ne cherche qu'une main
    hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.7)
    mp_draw = mp.solutions.drawing_utils

    # 2. Initialisation de la Camera (Le Vigile)
    cap = cv2.VideoCapture(VIDEO_SOURCE)
    
    prev_frame = None
    last_event_time = 0
    COOLDOWN = 5 # On attend 5 secondes entre chaque envoi de geste a l'API

    # --- NOUVEAU : Variables pour le maintien de l'éveil ---
    temps_dernier_mouvement = 0 
    DELAI_MAINTIEN_EVEIL = 2.0 # On garde MediaPipe allumé 2s après l'arrêt du mouvement

    print("Pipeline Vision actif ! Appuie sur 'q' pour quitter.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Erreur de lecture du flux video.")
            break

        # --- NIVEAU 1 : DETECTION DE MOUVEMENT (OPENCV) ---
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if prev_frame is None:
            prev_frame = gray
            continue

        # Calcul de la difference
        delta = cv2.absdiff(prev_frame, gray)
        thresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        mouvement_detecte = False
        for c in contours:
            if cv2.contourArea(c) > 10000: # Seuil de declenchement
                mouvement_detecte = True
                temps_dernier_mouvement = time.time() # <-- NOUVEAU : On réinitialise le chrono
                break
        
        prev_frame = gray # Mise a jour pour le prochain tour

        # --- NIVEAU 2 : ANALYSE DE GESTE (MEDIAPIPE) ---
        if mouvement_detecte:
            # MediaPipe a besoin d'une image en RGB (OpenCV est en BGR par defaut)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = hands.process(rgb_frame)

            if result.multi_hand_landmarks:
                for hand_landmarks in result.multi_hand_landmarks:
                    # Dessine le squelette de la main sur l'ecran
                    mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                    
                    # LOGIQUE ROBUSTE DU "THUMBS UP" (V2)
                    lm = hand_landmarks.landmark
                    
                    # 1. Les doigts sont-ils fermes (en poing) ?
                    # On compare le bout (8, 12, 16, 20) avec la BASE du doigt (5, 9, 13, 17)
                    # Si le bout est plus bas (y plus grand) que la base, le doigt est replie.
                    index_plie = lm[8].y > lm[5].y
                    majeur_plie = lm[12].y > lm[9].y
                    annulaire_plie = lm[16].y > lm[13].y
                    auriculaire_plie = lm[20].y > lm[17].y
                    
                    doigts_fermes = index_plie and majeur_plie and annulaire_plie and auriculaire_plie

                    # 2. Le pouce est-il bien leve ?
                    # Le bout (4) doit etre plus haut (y plus petit) que sa propre jointure (3)
                    # ET il doit etre franchement au-dessus de la base de l'index (5)
                    pouce_leve = (lm[4].y < lm[3].y) and (lm[4].y < lm[5].y)

                    # 3. Validation finale
                    if doigts_fermes and pouce_leve:
                        current_time = time.time()
                        if current_time - last_event_time > COOLDOWN:
                            print("\n[VISION] Geste detecte : VRAI POUCE EN L'AIR !")
                            
                            try:
                                response = requests.post(f"{API_URL}/api/pi/event", json={
                                    "type": "gesture",
                                    "data": {"gesture": "thumbs_up"}
                                }, headers=HEADERS, timeout=5)
                                
                                if response.status_code == 200:
                                    print("-> Evenement valide par le serveur (Code 200) !")
                                else:
                                    print(f"-> Erreur API: {response.status_code}")
                                    
                                last_event_time = current_time
                                
                            except Exception as e:
                                print(f"-> Erreur de connexion API : {e}")

                    # --- LOGIQUE DU SIGNE "V" (Prise de photo) ---
                    # 1. Index et Majeur tendus (le bout [8, 12] est PLUS HAUT que la base [5, 9])
                    # Rappel : Plus haut = valeur Y plus petite
                    index_tendu = lm[8].y < lm[5].y
                    majeur_tendu = lm[12].y < lm[9].y
                    
                    # 2. Annulaire et Auriculaire replies (le bout [16, 20] est PLUS BAS que la base [13, 17])
                    annulaire_plie = lm[16].y > lm[13].y
                    auriculaire_plie = lm[20].y > lm[17].y
                    
                    signe_v = index_tendu and majeur_tendu and annulaire_plie and auriculaire_plie

                    # --- DECLENCHEMENT DES ACTIONS ---
                    current_time = time.time()
                    
                    if current_time - last_event_time > COOLDOWN:
                        
                        # Action 1 : Le Pouce en l'air (Validation)
                        if doigts_fermes and pouce_leve:
                            print("\n[VISION] Geste detecte : POUCE EN L'AIR !")
                            try:
                                requests.post(f"{API_URL}/api/pi/event", json={
                                    "type": "gesture",
                                    "data": {"gesture": "thumbs_up"}
                                }, headers=HEADERS, timeout=5)
                                print("-> Evenement 'thumbs_up' envoye !")
                                last_event_time = current_time
                            except Exception as e:
                                print(f"-> Erreur API : {e}")
                                
                        # Action 2 : Le Signe V (Scan Document / Photo)
                        elif signe_v:
                            print("\n[VISION] Geste detecte : SIGNE 'V' !")
                            print("-> Declenchement de l'appareil photo dans 1 seconde...")
                            
                            # Petite pause pour te laisser le temps de sourire ou de cadrer le document !
                            cv2.waitKey(1000) 
                            
                            # On capture une nouvelle frame bien nette apres la pause
                            ret_scan, frame_scan = cap.read()
                            if ret_scan:
                                send_image_to_api(frame_scan)
                            else:
                                print("Erreur : Impossible de capturer l'image pour le scan.")
                                
                            last_event_time = current_time

        # Affichage de la camera
        cv2.imshow("Module Vision IRIS", frame)
        
        # --- GESTION DU CLAVIER (Boutons manuels) ---
        touche = cv2.waitKey(1) & 0xFF
        
        if touche == ord('q'):
            print("Fermeture du module Vision...")
            break
        elif touche == ord('p'): # Si tu appuies sur la touche 'p'
            print("\n[VISION] Mode manuel activé : Touche 'P' pressée !")
            
            # On prend la frame actuelle et on l'envoie à la fonction qu'on a créée tout à l'heure
            send_image_to_api(frame)

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()