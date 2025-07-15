# deck_builder.py

import streamlit as st
from collections import Counter
import random

from scryfall_api import get_card_details_batch_scryfall, get_card_details_scryfall, get_color_identity, is_basic_land, get_mana_value, get_card_rarity, get_card_set_code, get_card_collector_number, is_foil, _get_cache_key
from card_classifier import classify_card
from config import TARGET_DECK_SIZE, TARGET_LAND_COUNT, MIN_NON_LAND_CARDS, COLOR_MAP, CARD_CATEGORIES_RATIOS, CMC_TARGET_DISTRIBUTION, CATEGORY_KEYWORDS

def build_commander_deck(commandant_name, inventory_cards, preferences={}, progress_bar_global_deck_build=None):
    """
    Construit un deck Commander en se basant sur un commandant, l'inventaire
    de l'utilisateur et ses préférences.
    Affiche la progression via `progress_bar_global_deck_build`.
    """
    deck_list_names = []
    deck_full_details_for_export = []
    
    # Initialisation des compteurs pour le rapport détaillé
    deck_category_counts = Counter()
    mana_curve_spells_cmc = []
    synergy_cards_info = [] # Pour stocker des infos sur les cartes clés pour la synergie

    # Mise à jour de la barre de progression (si fournie)
    def update_global_progress(value, text=""):
        if progress_bar_global_deck_build:
            progress_bar_global_deck_build.progress(value, text=text)

    update_global_progress(5, f"Début de construction pour {commandant_name} : Récupération des détails...")
    commandant_details = get_card_details_scryfall(commandant_name)
    if not commandant_details:
        st.error(f"❌ Erreur : Impossible de trouver les détails pour le commandant '{commandant_name}'.")
        return None, None, None, None

    is_legendary_creature = "Legendary Creature" in commandant_details.get('type_line', '')
    is_pw_commander = ("Planeswalker" in commandant_details.get('type_line', '') and
                        "can be your commander" in commandant_details.get('oracle_text', '').lower())
    
    if not (is_legendary_creature or is_pw_commander):
        st.error(f"❌ Erreur : '{commandant_name}' n'est pas un commandant valide.")
        return None, None, None, None

    commander_color_identity = get_color_identity(commandant_details)
    
    if 'colors' in preferences and preferences['colors']:
        chosen_colors_set = set(preferences['colors'])
        if not chosen_colors_set.issubset(commander_color_identity):
            st.warning(f"⚠️ Avertissement : Couleurs préférées non compatibles avec le commandant. Le deck utilisera les couleurs valides.")
            preferences['colors'] = list(chosen_colors_set.intersection(commander_color_identity))

    deck_list_names.append(commandant_name)
    deck_full_details_for_export.append({
        'name': commandant_name,
        'set': get_card_set_code(commandant_details),
        'collector_number': get_card_collector_number(commandant_details),
        'foil': is_foil(commandant_details),
        'details': commandant_details # Ajout des détails complets pour analyse post-construction
    })
    # Le commandant compte comme une "menace" ou "utilité" selon sa nature, mais pour les stats de deck, on le gère à part.
    # On ajoute son type de carte principal
    cmd_types = commandant_details.get('type_line', '').split(' — ')[0].split(' ')
    for t in cmd_types:
        if t not in ["Legendary", "Creature", "Planeswalker"]: # Éviter les types génériques qui ne sont pas des catégories de deck
            deck_category_counts[t] += 1
    if "Creature" in cmd_types:
        deck_category_counts["Creature"] += 1
    if "Planeswalker" in cmd_types:
        deck_category_counts["Planeswalker"] += 1

    st.info(f"Identité couleur du commandant '{commandant_name}' : {', '.join(commander_color_identity) if commander_color_identity else 'Incolore'}")

    available_cards_processed = {}
    
    all_inventory_identifiers = []
    cmd_full_ident = _get_cache_key({"name": commandant_name, 
                                    "set": get_card_set_code(commandant_details), 
                                    "collector_number": get_card_collector_number(commandant_details)})
    
    for cache_key, card_info in inventory_cards.items():
        if cache_key == cmd_full_ident:
            continue
        all_inventory_identifiers.append({
            "name": card_info['name'],
            "set": card_info['set'],
            "collector_number": card_info['collector_number']
        })

    update_global_progress(15, "Récupération des détails des cartes de l'inventaire...")
    with st.spinner("🔍 Récupération des détails des cartes de l'inventaire..."):
        card_details_map, missing_cards_from_scryfall = get_card_details_batch_scryfall(
            all_inventory_identifiers
        )

    if missing_cards_from_scryfall:
        st.warning(f"⚠️ Avertissement : {len(missing_cards_from_scryfall)} cartes de l'inventaire n'ont pas été trouvées sur Scryfall ou ont un format incorrect : {', '.join(missing_cards_from_scryfall[:5])}{'...' if len(missing_cards_from_scryfall) > 5 else ''}")

    update_global_progress(25, "Filtrage et catégorisation des cartes disponibles...")
    for inv_cache_key, card_details_scryfall in card_details_map.items():
        original_inventory_info = inventory_cards.get(inv_cache_key)
        
        if original_inventory_info:
            card_color_identity = get_color_identity(card_details_scryfall)
            
            if card_color_identity.issubset(commander_color_identity):
                if 'colors' in preferences and preferences['colors']:
                    if not card_color_identity.issubset(set(preferences['colors'])):
                        continue
                
                categories = classify_card(card_details_scryfall, preferences.get('strategy'))
                
                available_cards_processed[inv_cache_key] = {
                    'name': original_inventory_info['name'],
                    'details': card_details_scryfall,
                    'set_from_scryfall': get_card_set_code(card_details_scryfall),
                    'cn_from_scryfall': get_card_collector_number(card_details_scryfall),
                    'available_qty': original_inventory_info['quantity_owned'],
                    'cmc': get_mana_value(card_details_scryfall),
                    'categories': categories,
                    'rarity': get_card_rarity(card_details_scryfall),
                    'foil_in_txt': original_inventory_info['foil_in_txt']
                }

    st.info(f"Cartes valides de l'inventaire (prêtes à être sélectionnées) : **{len(available_cards_processed)}**")
    
    potential_lands_from_inventory = {k: data for k, data in available_cards_processed.items() if "Land" in data['details'].get('type_line', '')}
    potential_spells_from_inventory = {k: data for k, data in available_cards_processed.items() if "Land" not in data['details'].get('type_line', '')}

    # --- LOGIQUE DE CONSTRUCTION DU DECK ---

    # Phase 1: Ajouter les sorts (non-terrains)
    temp_deck_spells_data = []
    added_to_deck_keys = set([cmd_full_ident])

    shuffled_spells = list(potential_spells_from_inventory.items())
    random.shuffle(shuffled_spells)

    categorized_spells_for_filling = {cat: [] for cat in CARD_CATEGORIES_RATIOS.keys()}
    for strategy_key in CATEGORY_KEYWORDS.keys():
        if strategy_key not in categorized_spells_for_filling:
            categorized_spells_for_filling[strategy_key] = []

    for cache_key, data in shuffled_spells:
        for cat in data['categories']:
            if cat in categorized_spells_for_filling:
                categorized_spells_for_filling[cat].append((cache_key, data))
    
    fill_order = []
    chosen_strategy = preferences.get('strategy')
    if chosen_strategy and chosen_strategy in CATEGORY_KEYWORDS:
        fill_order.append(chosen_strategy)

    general_categories_ordered = ['ramp', 'draw', 'spot_removal', 'board_wipe', 'threat', 'utility', 'flex_slots']
    for cat in general_categories_ordered:
        if cat not in fill_order:
             fill_order.append(cat)
    
    progress_text_spells = "Sélection des sorts..."
    spell_progress_bar = st.progress(0, text=progress_text_spells)
    
    spells_added_count = 0
    total_spells_target = MIN_NON_LAND_CARDS

    for category in fill_order:
        if len(temp_deck_spells_data) >= total_spells_target:
            break
        
        target_count = CARD_CATEGORIES_RATIOS.get(category, 0)
        current_count_in_category = len([c_key for c_key, c_data in temp_deck_spells_data if category in c_data['categories']])
        
        needed = target_count - current_count_in_category
        if needed <= 0:
            continue

        category_cards = categorized_spells_for_filling.get(category, [])
        random.shuffle(category_cards)
        
        for cache_key, data in category_cards:
            if len(temp_deck_spells_data) >= total_spells_target:
                break
            if cache_key not in added_to_deck_keys and data['available_qty'] > 0:
                temp_deck_spells_data.append((cache_key, data))
                added_to_deck_keys.add(cache_key)
                spells_added_count += 1
                update_global_progress(25 + int((spells_added_count / total_spells_target) * 35), f"Sélection des sorts: {category}...")
                spell_progress_bar.progress(spells_added_count / total_spells_target, text=progress_text_spells)

    remaining_slots_for_spells = total_spells_target - len(temp_deck_spells_data)
    if remaining_slots_for_spells > 0:
        all_other_spells = [(key, data) for key, data in shuffled_spells if key not in added_to_deck_keys and data['available_qty'] > 0]
        random.shuffle(all_other_spells)

        for cache_key, data in all_other_spells:
            if len(temp_deck_spells_data) >= total_spells_target:
                break
            if cache_key not in added_to_deck_keys:
                temp_deck_spells_data.append((cache_key, data))
                added_to_deck_keys.add(cache_key)
                spells_added_count += 1
                update_global_progress(25 + int((spells_added_count / total_spells_target) * 35), "Sélection des sorts: Remplissage final...")
                spell_progress_bar.progress(spells_added_count / total_spells_target, text=progress_text_spells)
    spell_progress_bar.empty()

    # Remplir les statistiques et informations de synergie pour les sorts ajoutés
    for cache_key, data in temp_deck_spells_data:
        deck_list_names.append(data['name'])
        deck_full_details_for_export.append({
            'name': data['name'],
            'set': data['set_from_scryfall'],
            'collector_number': data['cn_from_scryfall'],
            'foil': data['foil_in_txt'],
            'details': data['details'] # Ajout des détails complets
        })
        mana_curve_spells_cmc.append(data['cmc'])
        for cat in data['categories']:
            deck_category_counts[cat] += 1
        
        # Logique simplifiée pour la synergie
        if chosen_strategy and chosen_strategy in data['categories']:
            synergy_cards_info.append({'name': data['name'], 'category': chosen_strategy})
        elif any(c in data['categories'] for c in ['ramp', 'draw', 'board_wipe', 'spot_removal']):
             synergy_cards_info.append({'name': data['name'], 'category': data['categories'][0]}) # Prendre la première catégorie significative

    update_global_progress(60, "Ajout des terrains non-base...")
    non_basic_lands_available = [key for key, data in potential_lands_from_inventory.items() if key not in added_to_deck_keys]
    random.shuffle(non_basic_lands_available)

    for cache_key in non_basic_lands_available:
        if len(deck_list_names) >= TARGET_DECK_SIZE:
            break
        
        land_data = potential_lands_from_inventory[cache_key]
        deck_list_names.append(land_data['name'])
        deck_full_details_for_export.append({
            'name': land_data['name'],
            'set': land_data['set_from_scryfall'],
            'collector_number': land_data['cn_from_scryfall'],
            'foil': land_data['foil_in_txt'],
            'details': land_data['details'] # Ajout des détails complets
        })
        added_to_deck_keys.add(cache_key)
        deck_category_counts["Land"] += 1 # Compter les terrains non-base

    current_deck_size = len(deck_list_names)
    basic_lands_to_add_count = TARGET_DECK_SIZE - current_deck_size
    
    color_needs = Counter()
    for card_data_added in deck_full_details_for_export:
        details = card_data_added['details'] # Utiliser les détails déjà chargés
        
        if details and 'mana_cost' in details:
            mana_cost_str = details['mana_cost']
            for color_symbol in ['W', 'U', 'B', 'R', 'G']:
                color_needs[color_symbol] += mana_cost_str.count(color_symbol)

    if not color_needs and commander_color_identity:
        for c in commander_color_identity:
            color_needs[c] = 1
    elif not color_needs and not commander_color_identity:
        color_needs['C'] = 1

    total_color_symbols = sum(color_needs.values())
    
    if basic_lands_to_add_count > 0:
        added_basic_lands_info = []
        progress_text_lands = "Complétion avec terrains de base..."
        land_progress_bar = st.progress(0, text=progress_text_lands)

        for i in range(basic_lands_to_add_count):
            chosen_color_symbol = 'C'
            if total_color_symbols > 0:
                chosen_color_symbol = random.choices(
                    list(color_needs.keys()), 
                    weights=list(color_needs.values()), 
                    k=1
                )[0]
            elif commander_color_identity:
                chosen_color_symbol = random.choice(list(commander_color_identity))

            basic_land_name = f"{COLOR_MAP.get(chosen_color_symbol, 'Colorless')} Basic Land"
            
            basic_land_sets_cn = {
                'White': {'set': 'STA', 'cn': '63'},
                'Blue': {'set': 'STA', 'cn': '64'},
                'Black': {'set': 'STA', 'cn': '65'},
                'Red': {'set': 'STA', 'cn': '66'},
                'Green': {'set': 'STA', 'cn': '67'},
                'Colorless': {'set': 'OGW', 'cn': '183'}
            }
            bl_info = basic_land_sets_cn.get(COLOR_MAP.get(chosen_color_symbol, 'Colorless'), {'set': 'STX', 'cn': '265'})

            added_basic_lands_info.append({
                'name': basic_land_name,
                'set': bl_info['set'],
                'collector_number': bl_info['cn'],
                'foil': False,
                'details': {'name': basic_land_name, 'type_line': 'Basic Land'} # Détails min pour les terrains de base
            })
            update_global_progress(60 + int(((i + 1) / basic_lands_to_add_count) * 20), progress_text_lands)
            land_progress_bar.progress((i + 1) / basic_lands_to_add_count, text=progress_text_lands)
        land_progress_bar.empty()
        
        for bl_data in added_basic_lands_info:
            deck_list_names.append(bl_data['name'])
            deck_full_details_for_export.append(bl_data)
            deck_category_counts["Basic Land"] += 1 # Compter les terrains de base

    update_global_progress(90, "Vérification finale du deck...")
    
    # Assurez-vous que le deck a exactement TARGET_DECK_SIZE cartes
    if len(deck_full_details_for_export) > TARGET_DECK_SIZE:
        deck_full_details_for_export = deck_full_details_for_export[:TARGET_DECK_SIZE]
        deck_list_names = [card['name'] for card in deck_full_details_for_export]
    
    if len(deck_list_names) < TARGET_DECK_SIZE:
        st.warning(f"\n⚠️ Avertissement : Le deck n'a que {len(deck_list_names)} cartes. Il en manque {TARGET_DECK_SIZE - len(deck_list_names)} pour atteindre 100.")
        st.warning("Cela peut être dû à un inventaire insuffisant ou à des préférences trop restrictives.")
    else:
        st.success(f"\n✅ Deck complet de {len(deck_list_names)} cartes généré avec succès ! 🎉")

    update_global_progress(100, "Deck prêt!")

    # Retourner les informations supplémentaires pour le rapport
    return deck_full_details_for_export, mana_curve_spells_cmc, deck_category_counts, synergy_cards_info
