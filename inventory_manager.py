# inventory_manager.py

import re
import streamlit as st
# import os # Retiré car chemin_fichier est maintenant un objet fichier, plus un chemin

# INVENTORY_FILE est retiré de config.py, donc pas besoin ici.

@st.cache_data(ttl=3600*24) # Cache le résultat du chargement de l'inventaire pour 24h
def load_inventory_from_txt(uploaded_file): # <-- MODIFIÉ: Accepte l'objet fichier téléversé
    """
    Charge l'inventaire de cartes à partir d'un fichier .txt téléversé.
    Format attendu : "quantité nom de la carte (SET) no de carte *F* si foil"
    Retourne un dictionnaire de type {cache_key: {'name': str, ...}}.
    """
    inventaire = {}
    errors = []
    regex_ligne_carte = re.compile(r"(\d+)\s(.+?)\s\((.*?)\)\s*(\d+)(\s*\*([Ff])\*)?\s*$")

    if uploaded_file is None:
        st.error("❌ Aucun fichier d'inventaire n'a été téléversé.")
        return {} # Retourne un inventaire vide

    # Lire le contenu du fichier téléversé
    # uploaded_file.getvalue() retourne des bytes, il faut les décoder
    file_content = uploaded_file.getvalue().decode("utf-8")
    lignes = file_content.splitlines() # Diviser en lignes

    for ligne_num, ligne in enumerate(lignes, 1):
        ligne = ligne.strip()
        if not ligne:
            continue

        match = regex_ligne_carte.match(ligne)
        if match:
            quantite_lue = int(match.group(1))
            full_card_name_from_txt = match.group(2).strip()
            set_code_from_txt = match.group(3).strip().upper()
            numero_carte_from_txt = match.group(4).strip()
            est_foil_in_txt = bool(match.group(5))

            if "//" in full_card_name_from_txt:
                clean_name_for_scryfall = full_card_name_from_txt.split('//')[0].strip()
            else:
                clean_name_for_scryfall = full_card_name_from_txt
            
            cache_key = f"{clean_name_for_scryfall} ({set_code_from_txt}) {numero_carte_from_txt}"

            if cache_key not in inventaire:
                inventaire[cache_key] = {
                    'name': clean_name_for_scryfall,
                    'original_full_name': full_card_name_from_txt,
                    'set': set_code_from_txt,
                    'collector_number': numero_carte_from_txt,
                    'foil_in_txt': est_foil_in_txt,
                    'quantity_owned': quantite_lue
                }
        else:
            errors.append(f"Ligne {ligne_num} ignorée (format non reconnu) : '{ligne}'")

    if errors:
        st.warning("--- ⚠️ Erreurs de format dans le fichier téléversé ---")
        for error in errors:
            st.warning(error)
        st.warning("Veuillez corriger ces lignes pour une meilleure précision du deck.")

    return inventaire

def get_inventory(uploaded_file): # <-- MODIFIÉ: Accepte le fichier téléversé
    """Fonction principale pour obtenir l'inventaire avec un indicateur de cache."""
    with st.spinner("Chargement de l'inventaire et pré-analyse..."):
        inventory_data = load_inventory_from_txt(uploaded_file)
    return inventory_data
