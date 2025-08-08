import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import json
import os
import webbrowser
import winshell
import re

import DeckGenerator

# --- Configuration des chemins de fichiers ---
# Détecte si le script est en mode développement via une variable d'environnement

IS_DEV_MODE = os.getenv("ANKI_DEV_MODE", "False").lower() == "true"

if IS_DEV_MODE:
    RESOURCES_DIR = "resources_dev"  # Dossier pour le mode développement
    print("Mode DÉVELOPPEMENT ACTIVÉ. Fichiers ressources utilisés : 'resources_dev'.")
else:
    RESOURCES_DIR = "resources"  # Dossier par défaut pour la production
    print("Mode PRODUCTION ACTIVÉ. Fichiers ressources utilisés : 'resources'.")

# Assurez-vous que le dossier ressources (dev ou production) existe
os.makedirs(RESOURCES_DIR, exist_ok=True)

CONFIG_FILE = os.path.join(RESOURCES_DIR, "config.json")
CARDS_FILE = os.path.join(RESOURCES_DIR, "cards.json")  # Le fichier de cartes est maintenant un JSON
# --- Fin de la configuration des chemins ---


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            messagebox.showerror("Oopsie",
                                 f"Fichier de config '{CONFIG_FILE}' est corrompu, relancer setup")
            os.remove(CONFIG_FILE)  # Supprime le fichier corrompu pour qu'on puisse le recréer
    return None


def save_config(config_data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4)


def create_desktop_shortcut():
    try:
        exe_path = os.path.abspath(__file__)

        # direct sur le bureau
        desktop = winshell.desktop()
        shortcut_name = "Anki Deck Generator"
        shortcut_path = os.path.join(desktop, f"{shortcut_name}.lnk")

        with winshell.shortcut(shortcut_path) as link:
            link.path = exe_path
            link.description = "scuffed mais fonctionne"

        messagebox.showinfo("Raccourci Créé!",
                            f"c'est quand même plus pratique :)")
    except ImportError:
        messagebox.showerror("Erreur de Module",
                             'BIG FUCK\n'
                             f'Merci de contacter le dév :)))\n\n'
                             f'SI TU TE SENS BRAVE:\n'
                             f'1) installe python (google juste python installeur windows)'
                             f'2) ouvre ton terminal (appuie sur win+r et tape cmd.exe)\n'
                             f'3) tape: \'pip install winshell\n'
                             f'4) redémarre le programme et prie.')
    except Exception as e:
        messagebox.showerror("oopsie", f"Impossible de créer le raccourci.\n"
                                       f"Essaie de relancer en adminstrateur?\nErreur : {e}")


def run_setup():
    config = {}

    # --- ÉTAPE 1 : Nom du Deck  ---
    deck_name = simpledialog.askstring("Nom du Deck (Étape 1/3)",
                                       "Comme il apparaitra dans Anki", parent=root)
    if not deck_name:
        messagebox.showwarning("Annulé", "sans nom ça marchera pas trop")
        return
    config["deck_name"] = deck_name

    # --- ÉTAPE 2 : Chemin FFMPEG  ---
    messagebox.showinfo(
        "FFMPEG : IMPORTANT AS FUCK (Étape 2/3)",
        "ETAPE 2: Configurer et installer FFMPEG.`\n\n"
        "FFMPEG est un programme qui permet de convertir un format audio en autre, GLOBALEMENT.\n."
        "Important car Anki déteste les fichier wav\n"
        "Donc, on converti tout en MP3.",
        parent=root
    )
    # Proposer d'ouvrir le site FFMPEG avant de demander le chemin
    if messagebox.askyesno("Télécharger FFMPEG ?", "Telecharger directement FFMPEG? (indice: oui)",
                           parent=root):
        webbrowser.open("https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip")

    # --- quick explication de comment unzip --- #
    messagebox.showinfo(
        "Installer FFMPEG",
        f"Extrait le zip que tu viens de télécharger dans un nouveau dossier. Idéalement,\n"
        "à un endroit où il sera hors de vue (par exemple, dans C:).\n\n"
        "L'étape suivante demandera accés à ce nouveau dossier.\n"
        "Il faudrat selectionner FFMPEG.EXE, quelquepart dans BIN."
        "",
        parent=root)

    ffmpeg_path = filedialog.askopenfilename(
        title="Trouver executable FFMPEG ? (Regarde dans le dossier 'bin')",
        filetypes=[("Exécutable FFMPEG", "ffmpeg.exe"), ("Tous les fichiers", "*.*")],
        parent=root
    )
    # valeur par defaut "ffmpeg" pour PATH
    config["ffmpeg_path"] = ffmpeg_path if ffmpeg_path else "ffmpeg"

    # --- ÉTAPE 3 : Dossier d'Export (NOUVEAU DIALOGUE + Nom du fichier) ---
    messagebox.showinfo(
        "Dossier de Sortie (Étape 3/3)",
        f'Dernière étape, choisi donc où ton deck sera sauvegardé.\n\n'
        '(choisis un endroit facile à retrouver,\n'
        'je pense pas avoir codé une manière de le changer)',
        parent=root
    )

    # nom de l'output = nom selectionné au début
    output_filepath = filedialog.asksaveasfilename(
        title=f"Sauvegarder le deck Anki '{deck_name}'",
        defaultextension=".apkg",
        filetypes=[("Deck Anki", "*.apkg")],
        initialfile=f"{deck_name}.apkg",  # APKG match le nom du deck
        parent=root
    )
    if not output_filepath:
        messagebox.showwarning("Annulé !", ":(.")
        return

    config["output_filepath"] = output_filepath

    save_config(config)
    messagebox.showinfo("Setup Terminé!",
                        "oh mon dieu ça a marché. ready to go bitches")
    update_generate_button_state()


def run_generator():
    config = load_config()
    if not config:
        messagebox.showerror("oopsie", "Fichier config manquant. Lance le setup queen.")
        return

    # fetch back à partir du cfg
    output_filepath = config.get("output_filepath")
    if not output_filepath:
        messagebox.showerror("oopsie", "Dossier de sortie du deck non configuré.\n\n"
                                       "relance le setup queen")
        return

    # Pas besoin de vérifier le format ici, DeckGenerator le gérera en JSON
    if not os.path.exists(CARDS_FILE):  # Typo here, should be os.path.exists
        messagebox.showerror("oopsie",
                             f"{CARDS_FILE}' n'a pas été trouvé.\n\n"
                             f"Il devrait être dans le même dossier que ce .exe ou le dossier resources.")
        return

    try:
        # verification de l'existance du dossier
        output_dir = os.path.dirname(output_filepath)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)  # crée le s'il existe pas

        DeckGenerator.generate_deck(
            cards_file=CARDS_FILE,
            deck_name=config["deck_name"],
            ffmpeg_path=config["ffmpeg_path"],
            output_filepath=output_filepath
        )
        messagebox.showinfo("Succès!", "Deck généré avec succés. LETS FUCKING GO.")
    except Exception as e:
        messagebox.showerror("oh non",
                             f"erreur pendant la génération. very not good. \n\nErreur détaillée : {e}")
        # je prie que que ce message ne pop up jamais


# Renommée et modifiée pour créer un fichier JSON par défaut si absent
def create_default_cards_json():
    """
    Crée un fichier cards.json par défaut avec une structure JSON vide ou exemple,
    si le fichier n'existe pas.
    """
    if not os.path.exists(CARDS_FILE):
        default_cards_content = [
            {"question": "2+2?", "answer": "4"},
            {"question": "Le chiffre quatre se prononce: ", "answer": "\"four.wav\""},
            {"question": "wat dat sound: \"meow.mp3\"", "answer": "the gato."}
        ]
        try:
            with open(CARDS_FILE, "w", encoding="utf-8") as f:
                json.dump(default_cards_content, f, indent=4)
            messagebox.showinfo("Fichier de Cartes Créé",
                                f"Le fichier de cartes '{CARDS_FILE}' a été créé avec quelques exemples.\n"
                                f"Tu peux maintenant l'éditer via le GUI !", parent=root)
        except Exception as e:
            messagebox.showerror("Oopsie",
                                 f"Impossible de créer '{CARDS_FILE}'. \n\n"
                                 f"Vérifie que le dossier n'est pas en lecture seule?\nErreur : {e}", parent=root)
    # Plus besoin d'ouvrir le fichier texte, l'édition se fait via le GUI
    # os.startfile(CARDS_FILE) # Cette ligne est commentée car l'édition se fait via GUI


def open_output_folder():
    config = load_config()
    if config:
        # Extraire chemin complet APKG
        folder = os.path.dirname(config.get("output_filepath", ""))
        if folder and os.path.exists(folder):
            os.startfile(folder)
        else:
            messagebox.showwarning("oopsie: dossier introuvable",
                                   "Le dossier de sortie n'existe pas ou n'a pas été configuré. Setup encore ?")
    else:
        messagebox.showerror("oopsie", "fichier de config manquant, faut faire le setup d'abord.")


def update_generate_button_state():
    if os.path.exists(CONFIG_FILE):
        config = load_config()
        # check clés pour générer les cartes
        if config and \
                config.get("deck_name") and \
                config.get("ffmpeg_path") and \
                config.get("output_filepath"):  # chemin custom
            btn_generate.config(state="normal")
            btn_open_output.config(state="normal")
            return
    btn_generate.config(state="disabled")
    btn_open_output.config(state="disabled")


# --- Card Editor Dialog ---

class CardEditorDialog(tk.Toplevel):

    def __init__(self, parent, card_data=None):
        super().__init__(parent)
        self.transient(parent)
        self.grab_set()  # Make this dialog modal
        self.result = None  # Stores the result: a dict for success, None for cancel

        self.title("Ajouter/Modifier une Carte" if card_data is None else "Modifier une Carte")

        self._create_widgets(card_data)
        self.wait_window(self)  # Wait until this window is destroyed

    def _create_widgets(self, card_data):
        # Renommé 'frame' en 'main_frame' pour éviter le shadowing
        main_frame = tk.Frame(self, padx=10, pady=10)
        main_frame.pack(expand=True, fill="both")

        tk.Label(main_frame, text="Question :", font=("Arial", 10, "bold")).pack(anchor="w", pady=(5, 0))
        self.entry_q = tk.Entry(main_frame, width=50, font=("Arial", 10))
        self.entry_q.pack(fill="x", pady=(0, 2))

        tk.Label(main_frame, text="Réponse :", font=("Arial", 10, "bold")).pack(anchor="w", pady=(5, 0))
        self.entry_a = tk.Entry(main_frame, width=50, font=("Arial", 10))
        self.entry_a.pack(fill="x", pady=(0, 2))

        tk.Label(main_frame,
                 text="ASTUCE SONS : Pour ajouter un son, écris après ton texte : \"nom_de_ton_audio.mp3\"\n(ex: "
                      "'Bonjour \"hello.mp3\"'). Tes fichiers audios vont dans le dossier 'sounds' !",
                 font=("Arial", 8, "italic"), fg="gray", wraplength=380, justify="left").pack(anchor="w", pady=(5, 10))

        if card_data:
            self.entry_q.insert(0, card_data.get("question", ""))
            self.entry_a.insert(0, card_data.get("answer", ""))

        button_frame = tk.Frame(main_frame)  # button_frame est enfant de main_frame
        button_frame.pack(pady=10)
        tk.Button(button_frame, text="Valider", command=self._on_validate, width=12).pack(side="left", padx=5)
        tk.Button(button_frame, text="Annuler", command=self._on_cancel, width=12).pack(side="right", padx=5)

    def _on_validate(self):
        q_val = self.entry_q.get().strip()
        a_val = self.entry_a.get().strip()
        if not q_val or not a_val:
            messagebox.showwarning("Attention !",
                                   "Question ET Réponse ne peuvent pas être vides, voyons ! Complète les champs.",
                                   parent=self)
            return
        self.result = {"question": q_val, "answer": a_val}
        self.destroy()

    def _on_cancel(self):
        self.result = None  # Explicitly set to None
        self.destroy()


# --- Main Deck Editor Window ---

class DeckEditorWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.transient(parent)
        self.grab_set()
        self.title("CREATEUR DE CARTE")
        self.geometry("650x450")

        self.cards_data = []  # List of {'question': '...', 'answer': '...'} dicts
        self._load_cards()  # Load existing cards on startup

        self._create_widgets()

        self.wait_window(self)  # Keep window open until closed

    def _load_cards(self):
        """
        Charge les données des cartes depuis le fichier JSON.
        Crée un fichier JSON par défaut si CARDS_FILE n'existe pas.
        """
        create_default_cards_json()  # S'assure que cards.json existe (ou le crée)

        try:
            with open(CARDS_FILE, 'r', encoding='utf-8') as f:
                self.cards_data = json.load(f)  # Charge toutes les cartes depuis le JSON

            # Assurez-vous que c'est bien une liste
            if not isinstance(self.cards_data, list):
                messagebox.showerror("Erreur de format",
                                     f"Le fichier '{CARDS_FILE}' est mal formé.\n"
                                     f"Il devrait contenir une liste de cartes.",
                                     parent=self)
                self.cards_data = []  # Vide la liste si le format est incorrect

        except FileNotFoundError:
            # Cette erreur ne devrait plus se produire si create_default_cards_json() a bien fonctionné
            messagebox.showwarning("Fichier non trouvé",
                                   f"Le fichier '{CARDS_FILE}' n'existe pas. Deck vide créé à la place",
                                   parent=self)
            self.cards_data = []  # Assure que la liste est vide
        except json.JSONDecodeError as e:
            messagebox.showerror("Erreur de lecture JSON",
                                 f"Le fichier '{CARDS_FILE}' est corrompu ou mal formé JSON : {e}. Le deck sera vide.",
                                 parent=self)
            self.cards_data = []  # Vide la liste si le JSON est corrompu
        except Exception as e:
            messagebox.showerror("Erreur de lecture",
                                 f"Impossible de lire '{CARDS_FILE}'. Erreur inattendue : {e}",
                                 parent=self)
            self.cards_data = []

    def _save_cards(self):
        """
        Sauvegarde les cartes actuelles dans le fichier JSON.
        """
        try:
            with open(CARDS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.cards_data, f, indent=4)  # Sauvegarde les cartes au format JSON
            messagebox.showinfo("Sauvegarde réussie !",
                                "Modifications bien enregistrées! (miraculeusement)",
                                parent=self)
            return True
        except Exception as e:
            messagebox.showerror("Erreur de sauvegarde",
                                 f"Impossible de sauvegarder les cartes dans '{CARDS_FILE}'. Problème de droits "
                                 f"?\nErreur : {e}",
                                 parent=self)
            return False

    def _create_widgets(self):
        main_frame = tk.Frame(self, padx=10, pady=10)
        main_frame.pack(expand=True, fill="both")

        # Left side: Card List
        list_frame = tk.Frame(main_frame)
        list_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        tk.Label(list_frame, text="Tes cartes actuelles :", font=("Arial", 11, "bold")).pack(anchor="w", pady=(0, 5))

        self.listbox = tk.Listbox(list_frame, width=40, height=20, font=("Arial", 10), selectmode="SINGLE")
        self.listbox.pack(expand=True, fill="both")

        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=scrollbar.set)

        # Right side: Action Buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack(side="right", fill="y")

        tk.Button(button_frame, text="➕ Ajouter une Carte", command=self._add_card, width=25, height=2).pack(pady=5)
        tk.Button(button_frame, text="✏️ Modifier la Carte Sélectionnée", command=self._modify_card, width=25,
                  height=2).pack(pady=5)
        tk.Button(button_frame, text="❌ Supprimer la Carte Sélectionnée", command=self._delete_card, width=25,
                  height=2).pack(pady=5)

        tk.Frame(button_frame, height=1, bg="gray").pack(fill="x", pady=10)  # Visual separator

        tk.Button(button_frame, text="💾 Sauvegarder et Fermer", command=self._save_and_close, width=25, height=2,
                  bg="#d4edda", fg="#155724").pack(pady=5)
        tk.Button(button_frame, text="🚫 Annuler (Perdre les changements)", command=self._cancel_editor, width=25,
                  height=2, bg="#f8d7da", fg="#721c24").pack(pady=5)

        self._update_listbox()  # Populate the listbox on creation

    def _update_listbox(self):
        self.listbox.delete(0, tk.END)
        for i, card in enumerate(self.cards_data):
            # Assurez-vous que les clés 'question' et 'answer' existent et sont des chaînes
            question_text = card.get("question", "")
            answer_text = card.get("answer", "")

            # Extraire les noms de fichiers audio s'ils existent
            q_audio_name = self._extract_audio_name_from_text(question_text)
            a_audio_name = self._extract_audio_name_from_text(answer_text)

            # Préparer les parties affichables (sans le nom du fichier audio dans le texte principal)
            display_q = question_text.split('"')[0].strip()
            display_a = answer_text.split('"')[0].strip()

            # Construire la chaîne d'affichage
            audio_info = ""
            if q_audio_name:
                audio_info += f" [Q: {q_audio_name}]"
            if a_audio_name:
                audio_info += f" [A: {a_audio_name}]"

            display_text = f"{i + 1}. {display_q} >> {display_a}{audio_info}"
            self.listbox.insert(tk.END, display_text)

    # NOUVELLE MÉTHODE D'AIDE : Pour extraire le nom du fichier audio
    @staticmethod
    def _extract_audio_name_from_text(text):
        # Utilise la même regex que dans DeckGenerator.py pour la cohérence
        match = re.search(r'"([^"]+\.(?:mp3|wav))"', text)
        return match.group(1) if match else None

    def _add_card(self):
        dialog = CardEditorDialog(self)
        if dialog.result is not None:
            self.cards_data.append(dialog.result)
            self._update_listbox()
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(tk.END)  # Select new card
            self.listbox.see(tk.END)  # Scroll to new card

    def _modify_card(self):
        selected_indices = self.listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Sélection requise",
                                   "Sélectionne une carte dans la liste pour la modifier, tête en l'air !", parent=self)
            return

        index = selected_indices[0]
        current_card_data = self.cards_data[index]

        dialog = CardEditorDialog(self, card_data=current_card_data)
        if dialog.result is not None:
            self.cards_data[index] = dialog.result
            self._update_listbox()
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(index)  # Reselect modified card

    def _delete_card(self):
        selected_indices = self.listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Sélection requise", "Sélectionne une carte à virer de la liste, allez !",
                                   parent=self)
            return

        index = selected_indices[0]
        # Get the displayed text for confirmation, careful if listbox is empty
        display_text = self.listbox.get(index) if index < self.listbox.size() else f"carte #{index + 1}"

        if messagebox.askyesno("Confirmer Suppression",
                               f"Sûr de vouloir supprimer la carte: '{display_text}' ?\nLa carte sera irrécupérable.",
                               parent=self):
            del self.cards_data[index]
            self._update_listbox()

    def _save_and_close(self):
        if self._save_cards():  # Attempt to save
            self.destroy()

    def _cancel_editor(self):
        if messagebox.askyesno("Annuler les modifications ?",
                               "Sûr? Toutes les modifs seront perdues.",
                               parent=self):
            self.destroy()


# --- END New Card Editor Implementation ---

def open_deck_editor_gui():
    DeckEditorWindow(root)


# GUI principale (root)
root = tk.Tk()
root.title("Anki Deck Generator: Slightly Less Scuffed")
root.geometry("600x400")
root.resizable(True, True)

frame = tk.Frame(root, padx=20, pady=20)
frame.pack(expand=True)

tk.Label(frame, text="-Anki Deck Generator- FOR PRO HACKERS ONLY", font=("Arial", 14, "bold")).pack(pady=10)

btn_setup = tk.Button(frame, text="1. Setup (configure tout, A FAIRE EN PREMIER)", width=60, command=run_setup)
btn_setup.pack(pady=5)

# Update this button to open the GUI editor
btn_edit_cards = tk.Button(frame, text="2. Modifier/Gérer tes Cartes (GUI !)", width=60, command=open_deck_editor_gui)
btn_edit_cards.pack(pady=5)

btn_generate = tk.Button(frame, text="3. Générer/Mettre à jour le deck", width=60, command=run_generator)
btn_generate.pack(pady=5)

btn_open_output = tk.Button(frame, text="Ouvrir le Dossier de Sortie (pour trouver le fichier deck)", width=60,
                            command=open_output_folder)
btn_open_output.pack(pady=5)

btn_shortcut = tk.Button(frame, text="Créer un raccourci sur le Bureau", width=30, command=create_desktop_shortcut)
btn_shortcut.pack(pady=10)

update_generate_button_state()
root.mainloop()
