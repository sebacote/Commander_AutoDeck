# scryfall_api.py

import requests
import time
import streamlit as st
from config import SCRYFALL_RATE_LIMIT_DELAY, SCRYFALL_BATCH_SIZE # SCRYFALL_CACHE_FILE retiré

# _get_cache_key est ici car il est fondamental pour la génération de clés
def _get_cache_key(card_identifier):
    """Crée une clé unique pour le cache/identification à partir d'un dictionnaire d'identifiant."""
    if isinstance(card_identifier, str): # Pour les appels get_card_details_scryfall par nom
        return card_identifier
    
    # Pour les appels par identifiant complet
    name = card_identifier.get('name', 'N/A')
    set_code = card_identifier.get('set', 'N/A')
    collector_number = card_identifier.get('collector_number', 'N/A')
    return f"{name} ({set_code}) {collector_number}"

# load_cache et save_cache sont gérés par Streamlit
# clear_cache est déplacé dans main.py

@st.cache_data(ttl=3600*24)
def get_card_details_scryfall(card_name):
    """
    Récupère les détails d'une carte depuis l'API Scryfall par son NOM.
    Utilise le cache de Streamlit.
    NOTE: Cette fonction ne garantit pas la version exacte si plusieurs impressions existent.
    Elle est utilisée pour le commandant et pour les statistiques finales qui n'ont que le nom.
    """
    base_url = "https://api.scryfall.com/cards/named"
    params = {"exact": card_name}
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        card_data = response.json()
        time.sleep(SCRYFALL_RATE_LIMIT_DELAY)
        return card_data
    except requests.exceptions.RequestException:
        return None

@st.cache_data(ttl=3600*24)
def get_card_details_batch_scryfall(card_identifiers):
    """
    Récupère les détails de plusieurs cartes en utilisant l'endpoint /cards/collection.
    Prend une liste de dictionnaires d'identifiants.
    Utilise le cache de Streamlit.
    """
    found_cards_details = {}
    missing_cards = []
    identifiers_to_fetch = card_identifiers 

    if not identifiers_to_fetch:
        return found_cards_details, missing_cards

    base_url = "https://api.scryfall.com/cards/collection"
    
    for i in range(0, len(identifiers_to_fetch), SCRYFALL_BATCH_SIZE):
        batch = identifiers_to_fetch[i : i + SCRYFALL_BATCH_SIZE]
        try:
            response = requests.post(base_url, json={"identifiers": batch})
            response.raise_for_status()
            
            response_data = response.json()
            
            for card_data in response_data.get('data', []):
                card_name = card_data.get('name')
                set_code = card_data.get('set')
                collector_number = card_data.get('collector_number')
                precise_cache_key = f"{card_name} ({set_code.upper()}) {collector_number}"
                
                found_cards_details[precise_cache_key] = card_data
            
            for missing_ident in response_data.get('not_found', []):
                missing_name = missing_ident.get('name', 'N/A')
                missing_set = missing_ident.get('set', 'N/A')
                missing_cn = missing_ident.get('collector_number', 'N/A')
                missing_cards.append(f"{missing_name} ({missing_set}) {missing_cn}")

            time.sleep(SCRYFALL_RATE_LIMIT_DELAY)

        except requests.exceptions.RequestException as e:
            for ident in batch:
                missing_name = ident.get('name', 'N/A')
                missing_set = ident.get('set', 'N/A')
                missing_cn = ident.get('collector_number', 'N/A')
                missing_cards.append(f"{missing_name} ({missing_set}) {missing_cn}")
    
    return found_cards_details, missing_cards


def get_color_identity(card_data):
    """Extrait l'identité couleur d'une carte à partir de ses données Scryfall."""
    if card_data and 'color_identity' in card_data:
        return set(card_data['color_identity'])
    return set()

def is_basic_land(card_data):
    """Vérifie si une carte est un terrain de base."""
    return card_data and 'type_line' in card_data and "Basic Land" in card_data['type_line']

def get_mana_value(card_data):
    """Retourne le coût converti de mana (CMC) d'une carte."""
    return card_data.get('cmc', 0) if card_data else 0

def get_card_rarity(card_data):
    """Retourne la rareté d'une carte."""
    return card_data.get('rarity', 'common')

def get_card_set_code(card_data):
    """Retourne le code du set d'une carte."""
    return card_data.get('set', 'N/A').upper()

def get_card_collector_number(card_data):
    """Retourne le numéro de collection d'une carte."""
    return card_data.get('collector_number', 'N/A')

def is_foil(card_data):
    """Vérifie si la carte est foil dans ses détails Scryfall (si disponible)."""
    return card_data.get('foil', False)
