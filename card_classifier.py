# card_classifier.py

from scryfall_api import get_card_details_scryfall, get_card_details_batch_scryfall, get_color_identity
from config import CATEGORY_KEYWORDS, COLOR_MAP
import streamlit as st # Importé pour les indicateurs de progression

def classify_card(card_details, preferred_strategy=None):
    """
    Classifie une carte en fonction de ses types, de son texte d'oracle,
    et prend en compte une stratégie préférée pour certaines catégories spécifiques.
    Retourne une liste de catégories pertinentes.
    """
    categories = set()
    oracle_text = card_details.get('oracle_text', '').lower()
    type_line = card_details.get('type_line', '').lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        is_relevant_by_keyword = False
        for keyword in keywords:
            if keyword in oracle_text or keyword in type_line:
                is_relevant_by_keyword = True
                break
        
        if is_relevant_by_keyword:
            categories.add(category)

    if "creature" in type_line or "planeswalker" in type_line:
        if not any(cat in categories for cat in ['token', 'voltron', 'aristocrats', 'reanimator', 'superfriends', 'tribal']):
            categories.add('threat')

    if ("artifact" in type_line or "enchantment" in type_line or "land" in type_line) and not categories:
        categories.add('utility')
    
    if not categories:
        categories.add('utility')

    return list(categories)


@st.cache_data(ttl=3600*24) # Cache le résultat de l'identification des commandants
def identify_commanders_in_inventory(inventory, preferences=None):
    """
    Identifie les commandants potentiels dans l'inventaire en fonction des préférences.
    Calcule un score de pertinence stratégique détaillé pour chaque commandant.
    Retourne une liste de tuples (nom_commandant, détails_scryfall, pertinence_strategique_str, score_total, score_cmd_bonus, score_support_cards).
    Les commandants sont filtrés par couleur et par stratégie, puis triés par score de pertinence.
    """
    potential_commanders = []
    
    preferred_colors = set(preferences.get('colors', [])) if preferences else set()
    chosen_strategy = preferences.get('strategy', None) if preferences else None

    inventory_identifiers = []
    for cache_key, card_info in inventory.items():
        inventory_identifiers.append({
            "name": card_info['name'],
            "set": card_info['set'],
            "collector_number": card_info['collector_number']
        })

    # Le spinner pour get_card_details_batch_scryfall est déjà inclus via le décorateur st.cache_data
    # et le texte du spinner est géré à un niveau supérieur si nécessaire (dans main.py).
    inventory_card_details_map, missing_cards_from_scryfall = get_card_details_batch_scryfall(
        inventory_identifiers
    )

    if missing_cards_from_scryfall:
        st.warning(f"⚠️ Avertissement : {len(missing_cards_from_scryfall)} cartes de l'inventaire n'ont pas été trouvées sur Scryfall : {', '.join(missing_cards_from_scryfall[:5])}{'...' if len(missing_cards_from_scryfall) > 5 else ''}")
    
    inventory_processed_cache = {}
    
    total_items_to_process = len(inventory.items())
    # Utilisation d'un conteneur vide pour la barre de progression pour la vider plus facilement
    progress_bar_container = st.empty()
    progress_bar = progress_bar_container.progress(0, text="Analyse locale de l'inventaire et classification des cartes...")
    
    processed_count = 0

    for commander_cache_key, commander_processed_info in inventory.items():
        
        processed_info = inventory_processed_cache.get(commander_cache_key)
        if not processed_info:
            details = inventory_card_details_map.get(commander_cache_key)
            if details:
                processed_info = {
                    'details': details,
                    'categories': classify_card(details, chosen_strategy),
                    'colors': get_color_identity(details),
                    'inventory_info': inventory.get(commander_cache_key)
                }
                inventory_processed_cache[commander_cache_key] = processed_info
            else:
                processed_count += 1
                progress_bar.progress(processed_count / total_items_to_process, text="Analyse et évaluation des commandants...")
                continue

        commander_details = processed_info['details']
        commander_categories = processed_info['categories']
        commander_colors = processed_info['colors']
        commander_name_from_scryfall = commander_details.get('name')

        is_commander_type = ('legendary' in commander_details.get('type_line', '').lower() and 
                             ('creature' in commander_details.get('type_line', '').lower() or 
                              'planeswalker' in commander_details.get('type_line', '').lower()))

        if not is_commander_type:
            processed_count += 1
            progress_bar.progress(processed_count / total_items_to_process, text="Analyse et évaluation des commandants...")
            continue

        if preferred_colors:
            if not commander_colors.issubset(preferred_colors):
                processed_count += 1
                progress_bar.progress(processed_count / total_items_to_process, text="Analyse et évaluation des commandants...")
                continue

        score_total = 0
        score_cmd_bonus = 0
        score_support_cards = 0
        relevance_str = "" 

        if chosen_strategy:
            commander_oracle_text_lower = commander_details.get('oracle_text', '').lower()
            strategy_keywords = CATEGORY_KEYWORDS.get(chosen_strategy, [])
            
            keyword_occurrences_in_cmd = sum(commander_oracle_text_lower.count(k) for k in strategy_keywords)
            
            if keyword_occurrences_in_cmd > 0:
                score_cmd_bonus = keyword_occurrences_in_cmd * 10
                score_total += score_cmd_bonus
                relevance_str = f" (pertinent pour {chosen_strategy.capitalize()})"
            else:
                processed_count += 1
                progress_bar.progress(processed_count / total_items_to_process, text="Analyse et évaluation des commandants...")
                continue 
            
            for inv_cache_key, inv_processed_info in inventory_processed_cache.items():
                if inv_cache_key == commander_cache_key:
                    continue

                inv_categories = inv_processed_info['categories']
                inv_colors = inv_processed_info['colors']

                if inv_colors.issubset(commander_colors):
                    if chosen_strategy in inv_categories:
                        score_support_cards += 1 
                        score_total += 1 
        
        if not chosen_strategy:
            for inv_cache_key, inv_processed_info in inventory_processed_cache.items():
                if inv_cache_key == commander_cache_key:
                    continue
                inv_colors = inv_processed_info['colors']
                if inv_colors.issubset(commander_colors):
                    score_support_cards += 1
            score_total = score_support_cards


        potential_commanders.append((commander_name_from_scryfall, commander_details, relevance_str, score_total, score_cmd_bonus, score_support_cards))
        processed_count += 1
        progress_bar.progress(processed_count / total_items_to_process, text="Analyse et évaluation des commandants...")
    
    progress_bar.empty()

    potential_commanders.sort(key=lambda x: (-x[3], x[0]))

    return potential_commanders
