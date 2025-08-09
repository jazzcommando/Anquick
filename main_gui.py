import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import json
import os
import re

import DeckGenerator

IS_DEV_MODE = os.getenv("DEV_MODE", "False").lower() == "true"

if IS_DEV_MODE:
    RESOURCES_DIR = "resources_dev"  # dossier temp debug
    print("!MODE DEV ACTIF!")
else:
    RESOURCES_DIR = "resources"  # dossier par défaut pour end user
CONFIG_FILE = os.path.join(RESOURCES_DIR, "config.json")
CARDS_FILE = os.path.join(RESOURCES_DIR, "cards.json")
FFMPEG_PATH = os.path.join(os.path.dirname(__file__), 'bin', 'ffmpeg.exe')

os.makedirs(RESOURCES_DIR, exist_ok=True)


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            messagebox.showerror("!",
                                 f"'{CONFIG_FILE}' est corrompu, relancer setup")  # à modifier?
            os.remove(CONFIG_FILE)
    return None


# structure par défaut de cards.json
def create_default_cards_json():
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


def save_config(config_data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4)


def run_setup():  # A SIMPLIFIER!
    config = {}

    # 1: Nom du Deck
    deck_name = simpledialog.askstring("Nom du Deck",
                                       "Comme il apparaitra dans Anki", parent=root)
    if not deck_name:
        messagebox.showwarning("Annulé", "Pas de nom inséré")
        return
    config["deck_name"] = deck_name

    messagebox.showinfo(
        "Dossier de Sortie",
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
                        "ready to go")
    update_generate_button_state()


def run_generator():
    config = load_config()
    if not config:
        messagebox.showerror("oopsie", "Fichier config manquant.")
        return

    # fetch back à partir du cfg
    output_filepath = config.get("output_filepath")
    if not output_filepath:
        messagebox.showerror("oopsie", "Dossier de sortie du deck non configuré.")
        return

    if not os.path.exists(CARDS_FILE):
        messagebox.showerror("oopsie",
                             f"{CARDS_FILE}' n'a pas été trouvé.")
        return

    try:
        # verification de l'existence du dossier
        output_dir = os.path.dirname(output_filepath)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)  # crée le s'il existe pas

        # création du fichier .apkg
        DeckGenerator.generate_deck(
            cards_file=CARDS_FILE,
            deck_name=config["deck_name"],
            ffmpeg_path=config["ffmpeg_path"],
            output_filepath=output_filepath
        )
        messagebox.showinfo("Succès!", "Deck généré avec succés. LETS GO.")
    except Exception as e:
        messagebox.showerror("!!!",
                             f"Erreur lors de la création du deck: {e}")


def open_output_folder():
    config = load_config()
    if config:
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
        if config and \
                config.get("deck_name") and \
                config.get("ffmpeg_path") and \
                config.get("output_filepath"):  # chemin custom
            btn_generate.config(state="normal")
            btn_open_output.config(state="normal")
            return
    btn_generate.config(state="disabled")
    btn_open_output.config(state="disabled")


# Card Editor Dialog
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


#  DECK/CARD EDITOR MAIN GUI
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
        create_default_cards_json()  # S'assure que cards.json existe (ou le crée)
        try:
            with open(CARDS_FILE, 'r', encoding='utf-8') as f:
                self.cards_data = json.load(f)

            if not isinstance(self.cards_data, list):
                messagebox.showerror("Erreur de format",
                                     f"'{CARDS_FILE}' est mal formé.",
                                     parent=self)
                self.cards_data = []

        # Erreurs lecture json
        except FileNotFoundError:
            messagebox.showwarning("Fichier non trouvé",
                                   f"'{CARDS_FILE}' n'existe pas.",
                                   parent=self)
            self.cards_data = []
        except json.JSONDecodeError:
            messagebox.showerror("Erreur de lecture JSON",
                                 f"Erreur lors de la lecture de cards.json",
                                 parent=self)
            self.cards_data = []  # Vide la liste si le JSON est corrompu
        except Exception as e:
            messagebox.showerror("Erreur de lecture",
                                 f"Impossible de lire '{CARDS_FILE}'. Erreur inattendue : {e}",
                                 parent=self)
            self.cards_data = []

    def _save_cards(self):
        try:
            with open(CARDS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.cards_data, f, indent=4)
            messagebox.showinfo("Sauvegarde réussie !",
                                "Modifications bien enregistrées",
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

        # Liste des cartes à gauche
        list_frame = tk.Frame(main_frame)
        list_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        tk.Label(list_frame, text="Tes cartes actuelles :", font=("Arial", 11, "bold")).pack(anchor="w", pady=(0, 5))

        self.listbox = tk.Listbox(list_frame, width=40, height=20, font=("Arial", 10), selectmode="SINGLE")
        self.listbox.pack(expand=True, fill="both")

        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=scrollbar.set)

        # Boutons Principaux à droite
        button_frame = tk.Frame(main_frame)
        button_frame.pack(side="right", fill="y")

        tk.Button(button_frame, text="Ajouter une Carte", command=self._add_card, width=20, height=2).pack(pady=5)
        tk.Button(button_frame, text="Modifier la Carte Sélectionnée", command=self._modify_card, width=20,
                  height=2).pack(pady=5)
        tk.Button(button_frame, text="Supprimer la Carte Sélectionnée", command=self._delete_card, width=20,
                  height=2).pack(pady=5)

        tk.Frame(button_frame, height=1, bg="gray").pack(fill="x", pady=10)  # Visual separator

        tk.Button(button_frame, text="Sauvegarder et Fermer", command=self._save_and_close, width=25, height=2,
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

    # Extraction audio sans devoir spécifier l'extention
    @staticmethod
    def _extract_audio_name_from_text(text):
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
        if self._save_cards():
            self.destroy()

    def _cancel_editor(self):
        if messagebox.askyesno("Annuler les modifications ?",
                               "Sûr? Toutes les modifs seront perdues.",
                               parent=self):
            self.destroy()


def open_deck_editor_gui():
    DeckEditorWindow(root)


def wipe_dev_folder():
    create_default_cards_json()
    os.remove(CONFIG_FILE)
    tk.messagebox.showwarning(title=..., message=f"'{RESOURCES_DIR}' WIPED")


# Elements GUI Fenêtre principale
root = tk.Tk()
root.title('AnQuick: Need for Speed Edition')
root.geometry("600x400")
root.resizable(True, True)

frame = tk.Frame(root, padx=20, pady=20)
frame.pack(expand=True)

if not IS_DEV_MODE:  # moyen de faire ça plus clean? pas envie de faire un elif pour chaque variante option dev
    tk.Label(frame, text="AnQuick TEST", font=("Arial", 14, "bold")).pack(pady=10)
else:
    tk.Label(frame, text="AnQuick DEV MODE", fg='red', font=("Arial", 14, "bold")).pack(pady=10)

btn_setup = tk.Button(frame, text="Setup (configure tout)", width=60, command=run_setup)
btn_setup.pack(pady=5)

btn_edit_cards = tk.Button(frame, text="Modifier/Gérer Cartes", width=60, command=open_deck_editor_gui)
btn_edit_cards.pack(pady=5)

btn_generate = tk.Button(frame, text="Générer/Mettre à jour le deck", width=60, command=run_generator)
btn_generate.pack(pady=5)

btn_open_output = tk.Button(frame, text="Ouvrir le Dossier de Sortie du Fichier Deck)", width=60,
                            command=open_output_folder)
btn_open_output.pack(pady=5)

if IS_DEV_MODE:
    btn_generate = tk.Button(frame, text="Wipe Ressources_Dev?", width=60, bg='red', command=wipe_dev_folder)
    btn_generate.pack(pady=5)

update_generate_button_state()
root.mainloop()
