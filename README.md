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
