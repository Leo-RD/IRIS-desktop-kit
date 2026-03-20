# 👁️ IRIS - Raspberry Pi Desktop Module

Ce dépôt contient le code source du module bureau (IoT) pour l'assistant IA multimodale **IRIS**. 
Le Raspberry Pi agit comme les yeux et les oreilles du système, gérant l'acquisition audio/vidéo locale et la communication sécurisée avec l'API Elixir centralisée.

## ✨ Fonctionnalités

### 🎙️ Module Audio (`wake_wordFULL.py`)
* **Détection locale (Wake Word)** : Utilisation de PocketSphinx hors-ligne pour détecter le mot-clé *"IRIS"* sans surcharger le réseau.
* **Traitement du signal (DSP)** : Intégration de **WebRTC APM** pour le nettoyage de la voix en temps réel (Suppression de bruit et Contrôle Automatique du Gain par blocs de 10ms).
* **Routage Bluetooth natif** : Délégation de la lecture audio (TTS) au système d'exploitation via `SoX` pour contourner les limitations d'ALSA avec les enceintes sans fil.

### 📷 Module Vision (`vision.py`)
* **Architecture en cascade (Économie CPU)** : 
  1. *Niveau 1* : Détection de mouvement ultra-légère par soustraction d'images (OpenCV).
  2. *Niveau 2* : Suivi squelettique des mains (MediaPipe) activé **uniquement** si un mouvement est détecté (avec un délai de maintien de 2s).
* **Détection de gestes** : Reconnaissance mathématique des articulations pour les gestes "Pouce en l'air" (Validation) et "Signe V" (Scan visuel).
* **Scan de documents** : Capture haute définition, encodage JPEG/Base64, et envoi à l'API pour analyse multimodale par le LLM.

## 🏗️ Architecture Technique (Micro-services)

Pour éviter les conflits de dépendances matérielles (notamment MediaPipe qui n'est pas encore compilé pour Python 3.13 sur architecture ARM64), le projet est divisé en **deux micro-services indépendants** qui communiquent en parallèle avec l'API HTTPS :

```text
iris-pi/
├── venv_iris/          # Python 3.13 (Audio / WebRTC / Sphinx)
├── venv_vision/        # Python 3.11 (Vision / OpenCV / MediaPipe via UV)
├── wake_wordFULL.py    # Service Audio (Micro UGREEN -> Enceinte Bose)
├── vision.py           # Service Vision (Caméra -> Geste/Scan)
├── iris.dict           # Dictionnaire phonétique pour le Wake Word
└── start_iris.sh       # Script Bash de lancement simultané
```text



⚙️ Prérequis
Matériel :

Raspberry Pi 5 (OS Bookworm)

Microphone USB (ex: UGREEN)

Enceinte Bluetooth (ex: Bose)

Caméra (Webcam USB ou flux IP/DroidCam)

Dépendances Système :

Bash
sudo apt update
sudo apt install sox libsox-fmt-all -y
🚀 Installation
Cloner le dépôt :

Bash
git clone [https://github.com/TON_NOM/iris-pi.git](https://github.com/TON_NOM/iris-pi.git)
cd iris-pi
Configuration de l'API :
Dans wake_wordFULL.py et vision.py, remplacez les variables suivantes :

Python
API_URL = "[https://iris.qoyri.fr](https://iris.qoyri.fr)" # Sans le port pour le reverse proxy
PI_KEY = "irpi_votre_cle_api_generee" # Clé API de l'utilisateur
Environnement Audio (Python 3.13) :

Bash
python3 -m venv venv_iris
source venv_iris/bin/activate
pip install pyaudio requests pocketsphinx webrtc-noise-gain
deactivate
Environnement Vision (Python 3.11 via uv) :

Bash
curl -LsSf [https://astral.sh/uv/install.sh](https://astral.sh/uv/install.sh) | sh
source ~/.bashrc
uv venv --python 3.11 venv_vision
source venv_vision/bin/activate
uv pip install opencv-python mediapipe requests
deactivate
🎯 Utilisation
Pour lancer les deux modules simultanément en arrière-plan, exécutez le script principal :

Bash
chmod +x start_iris.sh
./start_iris.sh
Interactions possibles :

Parler à l'IA : Dites "IRIS" (la console indique l'enregistrement), puis posez votre question. La réponse sera lue sur l'enceinte Bluetooth.

Valider une action : Faites un pouce en l'air (👍) face à la caméra.

Scanner un document : Placez le document, faites le signe de la victoire (✌️). L'image sera envoyée à l'API. (Alternative: Appuyez sur la touche P de la fenêtre vidéo).

🔒 Sécurité
Le Raspberry Pi ne stocke aucune donnée sensible et aucun audio/image de manière permanente. Les fichiers temporaires sont supprimés post-traitement. Toute l'intelligence (LLM) est déportée sur le serveur Proxmox.

Projet développé dans le cadre du Challenge IA,3ème édition.
