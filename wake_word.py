import os
from pocketsphinx import LiveSpeech

def main():
    print("Initialisation de PocketSphinx en Francais...")
    
    # Le chemin vers le dossier de ton modele acoustique (celui qui marchait tout a l'heure)
    hmm_dir = "/home/iris/iris_vision/venv_iris/lib/python3.13/site-packages/pocketsphinx/model/fr-fr/fr-fr"
    
    # Le chemin vers TON nouveau dictionnaire magique
    dict_file = "/home/iris/iris_vision/venv_iris/lib/python3.13/site-packages/pocketsphinx/model/fr-fr/fr-fr.dict"
    
    speech = LiveSpeech(
        hmm=hmm_dir,         
        dic=dict_file,       # <-- On utilise ton fichier perso ici !
        lm=False,            
        keyphrase='iris',
        kws_threshold=1e-15
    )

    print("IRIS est a l'ecoute... (Dis 'iris' pour tester. Ctrl+C pour quitter)")

    for phrase in speech:
        print("Wake word detecte ! -> Pret a enregistrer la commande.")

if __name__ == '__main__':
    main()
