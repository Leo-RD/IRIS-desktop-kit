import cv2

video_url = "http://127.0.0.1:4747/video"
cap = cv2.VideoCapture(video_url)

if not cap.isOpened():
    print("Erreur : Impossible de se connecter a DroidCam.")
    exit()

print("Niveau 1 actif : Analyse OpenCV en cours... (Appuie sur 'q' pour quitter)")

# Variable pour memoriser l'image de l'instant t-1
prev_frame = None

while True:
    ret, frame = cap.read()
    if not ret:
        print("Erreur de lecture du flux.")
        break

    # 1. Optimisation : Niveaux de gris et flou
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)

    # 2. Initialisation au tout premier tour de boucle
    if prev_frame is None:
        prev_frame = gray
        continue

    # 3. Calcul de la difference entre t et t-1
    frame_delta = cv2.absdiff(prev_frame, gray)

    # 4. On accentue les differences (seuil binaire)
    thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]

    # 5. On cherche les contours des zones modifiees
    contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    mouvement_detecte = False

    for contour in contours:
        # Si la zone en mouvement est trop petite (bruit ou objet lointain), on l'ignore
        if cv2.contourArea(contour) < 10000: # Tu pourras ajuster ce nombre !
            continue
        
        mouvement_detecte = True
        
        # Dessiner un rectangle vert autour du mouvement pour la demo
        (x, y, w, h) = cv2.boundingRect(contour)
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

    if mouvement_detecte:
        print("MOUVEMENT DETECTE ! -> Pret a lancer le Niveau 2")

    # Mise a jour de l'image de reference pour le prochain tour
    prev_frame = gray

    # Affichage de l'image finale
    cv2.imshow("Vue IRIS", frame)
    
    # ASTUCE : Decommente la ligne ci-dessous pour voir l'image en "negatif" analysee par le Pi !
    # cv2.imshow("Vue Ordinateur (Filtre Threshold)", thresh)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
