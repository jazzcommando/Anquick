import genanki
import re
import subprocess
import os
import json

# setup genanki (global car le modele est fixe)

my_model_id = 1607392319
my_deck_id = 2059400110  # id du deck pour mise a jour
card_css = """
.card {
    font-family: Arial;
    font-size: 24px;
    text-align: center;
    color: black;
    background-color: white;
}
.question {
    padding: 10px;
    max-width: 800px;
    margin: auto;
    word-wrap: break-word;
    box-sizing: border-box;
}
"""

model = genanki.Model(
    my_model_id,
    'Text+Sound Auto Model',
    fields=[
        {'name': 'Question'},
        {'name': 'Answer'},
        {'name': 'AudioQ'},
        {'name': 'AudioA'}
    ],
    templates=[
        {
            'name': 'Card Template',
            'qfmt': '<div class="question">{{Question}}</div><br>{{AudioQ}}',
            'afmt': '{{FrontSide}}<hr id="answer"><div class="question">{{Answer}}</div><br>{{AudioA}}',
        },
    ],
    css=card_css
)


# fonctions utilitaires
def convert_wav_to_mp3(wav_path, ffmpeg_path):
    mp3_path = wav_path.replace('.wav', '.mp3')
    if not os.path.exists(ffmpeg_path) and ffmpeg_path.lower() != "ffmpeg":
        raise FileNotFoundError(f"ffmpeg introuvable au chemin specifie : {ffmpeg_path}. verifie ta config.")

    ffmpeg_cmd = [ffmpeg_path, "-y", "-i", wav_path, "-codec:a", "libmp3lame", "-qscale:a", "2", mp3_path]

    if not os.path.exists(mp3_path) or os.path.getmtime(wav_path) > os.path.getmtime(mp3_path):
        print(f"🔄 conversion wav ➜ mp3 : {os.path.basename(wav_path)} ➜ {os.path.basename(mp3_path)}")
        try:
            subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            error_message = f"er conversion {os.path.basename(wav_path)} :\n  stdout: {e.stdout}\n  stderr: {e.stderr}"
            print(error_message)
            raise Exception(f"erreur de conversion audio : {error_message}")
        except FileNotFoundError:
            raise FileNotFoundError("ffmpeg introuvable. assure-toi qu'il est installe et dans ton path.")
    return mp3_path


def extract_audio_path(text):
    match = re.search(r'"([^"]+\.(?:mp3|wav))"', text)
    return match.group(1) if match else None


def process_side(text, sounds_dir, ffmpeg_path):
    audio_filename = extract_audio_path(text)
    audio_tag = ''
    full_audio_path = None
    cleaned_text = text.strip()

    if audio_filename:
        # Important : Assurez-vous que le remplacement se fait sur le texte original pour ne pas laisser de traces
        # et que l'extraction du nom du fichier audio est robuste.
        cleaned_text = cleaned_text.replace(f'"{audio_filename}"', '').strip()
        full_audio_path = os.path.join(sounds_dir, os.path.basename(audio_filename))

        if full_audio_path.lower().endswith('.wav'):
            try:
                full_audio_path = convert_wav_to_mp3(full_audio_path, ffmpeg_path)
                audio_tag = f"[sound:{os.path.basename(full_audio_path)}]"
            except Exception as e:
                print(f"⚠️ conversion echouee : {os.path.basename(full_audio_path)} ➜ {e}")
                # Si la conversion échoue, nous n'incluons pas l'audio et continuons avec le texte seul.
                return cleaned_text, '', None
        else:
            audio_tag = f"[sound:{os.path.basename(full_audio_path)}]"

    return cleaned_text, audio_tag, full_audio_path


# logique principale de generation de deck
def generate_deck(cards_file, deck_name, ffmpeg_path, output_filepath):
    print("🚀 generation du deck anki...")

    # initialisation de deck et media_files pour chaque generation
    current_deck = genanki.Deck(my_deck_id, deck_name)
    current_media_files = []

    sounds_dir = os.path.join(os.path.dirname(cards_file), 'resources/sounds')

    if not os.path.exists(sounds_dir):
        print(f"⚠️ dossier 'sounds' manquant : {sounds_dir}. aucun audio ne sera ajoute.")
        os.makedirs(sounds_dir, exist_ok=True)  # creer le dossier s'il n'existe pas

    all_cards_data = []  # stockage

    try:
        with open(cards_file, 'r', encoding='utf-8') as f:
            all_cards_data = json.load(f)

        if not isinstance(all_cards_data, list):
            raise TypeError("Le fichier JSON des cartes doit contenir une liste d'objets (cartes).")

        for line_num, card_dict in enumerate(all_cards_data, 1):

            if not isinstance(card_dict, dict) or "question" not in card_dict or "answer" not in card_dict:
                print(f"❌ ligne {line_num} ✖️\n   '{card_dict}'\n   erreur : format de carte JSON invalide. Ignorée.")
                continue

            try:
                q_raw = card_dict["question"]
                a_raw = card_dict["answer"]

                q_text, q_tag, q_path = process_side(q_raw, sounds_dir, ffmpeg_path)
                a_text, a_tag, a_path = process_side(a_raw, sounds_dir, ffmpeg_path)

                for path in (q_path, a_path):
                    if path:
                        if os.path.exists(path):
                            current_media_files.append(path)
                        else:
                            print(f"❌ fichier audio introuvable (mentionne dans la carte) : {path}")

                note = genanki.Note(
                    model=model,
                    fields=[q_text, a_text, q_tag, a_tag]
                )
                current_deck.add_note(note)

            except Exception as e:
                # Adaptez le message d'erreur pour le format JSON
                print(
                    f"\nCarte #{line_num} ✖️\n   '{card_dict}'\n   erreur lors du traitement : {e}\n   format attendu"
                    f": {{'question': 'texte \"audio.mp3\"', 'answer': 'reponse \"audio.mp3\"'}}")
    except FileNotFoundError:
        print(f"❌ erreur : le fichier '{cards_file}' n'a pas ete trouve.")
        raise
    except json.JSONDecodeError as e:
        print(f"❌ erreur : le fichier '{cards_file}' est mal formate JSON : {e}")
        raise
    except Exception as e:
        print(f"❌ erreur generale lors de la lecture/traitement de '{cards_file}' : {e}")
        raise

    # sauvegarde du package anki
    genanki.Package(current_deck, current_media_files).write_to_file(output_filepath)
    print(f"\n🎉 deck cree avec succes ➜ '{output_filepath}'")
    print(f"📦 cartes : {len(current_deck.notes)} | medias : {len(current_media_files)}")
