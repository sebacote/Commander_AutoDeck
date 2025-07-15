# main.py

import os
import pyperclip
import streamlit as st
import matplotlib.pyplot as plt
from collections import Counter
import re
import base64

from inventory_manager import get_inventory
from card_classifier import identify_commanders_in_inventory
from deck_builder import build_commander_deck
from scryfall_api import get_card_details_scryfall, get_color_identity, _get_cache_key
from config import COLOR_MAP, CATEGORY_KEYWORDS, TARGET_DECK_SIZE, MTG_COLOR_ORDER, SCRYFALL_CACHE_FILE, MANA_SYMBOLS_PATH

COLOR_EMOJI_MAP = {
    'W': '⚪', 'U': '🔵', 'B': '⚫', 'R': '🔴', 'G': '🟢', 'C': '🟣'
}

# Dictionnaire des descriptions de stratégies - DÉFINI GLOBALEMENT AU DÉBUT
STRATEGY_DESCRIPTIONS = {
    'aggro': "Vise à mettre de la pression rapidement sur les adversaires avec de nombreuses petites créatures ou des créatures efficaces en début de partie.",
    'control': "Ralentit la partie, gère les menaces des adversaires, et cherche à dominer le jeu avant de gagner avec une ou deux grosses menaces ou une combo tardive.",
    'combo': "Cherche des combinaisons de cartes pour gagner la partie d'un coup, souvent en générant du mana infini, des dégâts infinis ou en vidant la bibliothèque de l'adversaire.",
    'ramp': "Vise à générer plus de mana que la normale pour lancer des sorts coûteux plus tôt dans la partie, accélérant votre plan de jeu.",
    'voltron': "Consiste à rendre votre commandant très puissant (souvent avec des équipements et des auras) pour gagner la partie par des dégâts de commandant.",
    'token': "Crée de grandes quantités de jetons de créatures (souvent petites) pour submerger l'adversaire, déclencher des effets en masse ou générer du mana.",
    'stax': "Vise à restreindre les ressources des adversaires (mana, cartes en main, permanents) pour les empêcher de jouer efficacement, vous laissant seul maître du jeu.",
    'mill': "Gagne la partie en vidant la bibliothèque des adversaires, les forçant à piocher dans une bibliothèque vide et à perdre.",
    'discard': "Vise à vider la main des adversaires pour limiter leurs options de jeu et contrôler leur capacité à répondre à vos menaces.",
    'aristocrats': "Se concentre sur le sacrifice de vos propres créatures (souvent des jetons) pour déclencher des effets puissants comme le drain de vie ou la pioche de cartes.",
    'reanimator': "Spécialisé dans la mise de grosses créatures dans votre cimetière, puis les ramener sur le champ de bataille pour un coût de mana réduit ou gratuitement.",
    'spellslinger': "Construit autour du lancement de nombreux sorts non-créature (instantanés et rituels) pour déclencher des capacités de vos permanents ou de votre commandant.",
    'enchantments_matter': "Se concentre sur le jeu d'un grand nombre d'enchantements, souvent avec des cartes qui vous font piocher ou génèrent des avantages à chaque enchantement joué.",
    'artifacts_matter': "Similaire à Enchantments Matter, mais avec des artefacts. Cherche à abuser des synergies avec les artefacts pour divers avantages et conditions de victoire.",
    'counters_matter': "Axé sur l'accumulation de marqueurs +1/+1 ou d'autres types de marqueurs sur vos permanents pour les rendre très grands, ou pour déclencher des effets liés aux marqueurs.",
    'superfriends': "Une stratégie centrée sur les planeswalkers, cherchant à en jouer plusieurs, à les protéger et à activer leurs capacités ultimes (emblems) pour gagner la partie.",
    'tribal': "Construire un deck autour d'un type de créature spécifique (par exemple, Zombies, Elfes, Dragons) et utiliser les synergies entre ces créatures pour un plan de jeu cohérent.",
    'group_hug': "Vise à aider tous les joueurs (vous y compris) en leur donnant des ressources (cartes, mana, jetons) pour créer une partie amusante et souvent chaotique. Peut être combiné avec une condition de victoire secrète.",
    'group_slug': "L'opposé du Group Hug. Cette stratégie vise à punir tous les joueurs (y compris vous-même, parfois) pour des actions de jeu courantes comme piocher des cartes ou lancer des sorts, drainant leur vie progressivement.",
    'pillow_fort': "Vise à se rendre difficilement attaquable ou ciblable pour vos adversaires, en utilisant des enchantements, des artefacts ou des créatures qui taxent, empêchent les attaques, ou offrent de la protection.",
    'theft': "Se concentre sur le vol des permanents ou des cartes de vos adversaires pour les utiliser contre eux, affaiblissant leur position tout en renforçant la vôtre."
}

try:
    pyperclip.copy('')
    CLIPBOARD_AVAILABLE = True
except pyperclip.PyperclipException:
    CLIPBOARD_AVAILABLE = False

# Fonction pour charger et afficher les symboles de mana SVG
@st.cache_data
def get_mana_svg_html(symbol, size_px=20):
    filepath = os.path.join(MANA_SYMBOLS_PATH, f"{symbol.upper()}.svg")
    try:
        with open(filepath, "rb") as f:
            svg_content = f.read()
        encoded_svg = base64.b64encode(svg_content).decode('utf-8')
        return f'<img src="data:image/svg+xml;base64,{encoded_svg}" width="{size_px}" height="{size_px}" style="vertical-align: middle; margin: 0 1px;">'
    except FileNotFoundError:
        return f"({symbol})" # Fallback si le fichier n'est pas trouvé
    except Exception as e:
        return f"({symbol} ERR)"

# Dictionnaire de mappage des symboles de couleur MTG vers leurs HTML SVG
MANA_SYMBOL_HTML_MAP = {
    'W': get_mana_svg_html('W'),
    'U': get_mana_svg_html('U'),
    'B': get_mana_svg_html('B'),
    'R': get_mana_svg_html('R'),
    'G': get_mana_svg_html('G'),
    'C': get_mana_svg_html('C')
}


def clear_cache_main():
    if os.path.exists(SCRYFALL_CACHE_FILE):
        try:
            os.remove(SCRYFALL_CACHE_FILE)
            st.success(f"🗑️ Cache Scryfall '{SCRYFALL_CACHE_FILE}' vidé avec succès.")
        except OSError as e:
            st.error(f"❌ Erreur lors de la suppression du cache : {e}")
    else:
        st.info(f"Cache Scryfall '{SCRYFALL_CACHE_FILE}' non trouvé, rien à vider.")
    
    st.cache_data.clear()
    for key in st.session_state.keys():
        del st.session_state[key]
    st.rerun()

def display_cmc_chart(mana_curve_spells_cmc, commandant_name):
    if mana_curve_spells_cmc:
        cmc_counts = Counter(mana_curve_spells_cmc)
        max_cmc = int(max(cmc_counts.keys())) if cmc_counts else 0
        
        cmc_labels = list(range(max_cmc + 1))
        cmc_values = [cmc_counts.get(cmc, 0) for cmc in cmc_labels]

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(cmc_labels, cmc_values, color='skyblue')
        ax.set_xlabel('Coût Converti de Mana (CMC)')
        ax.set_ylabel('Nombre de cartes')
        ax.set_title(f'Courbe de Mana du Deck ({commandant_name})')
        ax.set_xticks(cmc_labels)
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        st.pyplot(fig)
        plt.close(fig)
    else:
        st.info("📊 Pas assez de sorts pour générer la courbe de mana.")

def app():
    st.set_page_config(page_title="AutoDeck Commander MTG", page_icon="✨", layout="wide")
    st.title("✨ AutoDeck Commander MTG ✨")
    st.markdown("---")

    if 'preferences' not in st.session_state:
        st.session_state.preferences = {}
    if 'commanders_data' not in st.session_state:
        st.session_state.commanders_data = None
    if 'sort_option_name' not in st.session_state:
        st.session_state.sort_option_name = "Par score de pertinence total (Commandant + Cartes de support)"
    if 'selected_commander_index' not in st.session_state:
        st.session_state.selected_commander_index = None
    if 'deck_generated' not in st.session_state:
        st.session_state.deck_generated = False
    if 'inventaire_loaded' not in st.session_state:
        st.session_state.inventaire_loaded = False
    if 'inventaire' not in st.session_state:
        st.session_state.inventaire = None
    if 'generated_deck_details' not in st.session_state:
        st.session_state.generated_deck_details = None
    if 'generated_mana_curve' not in st.session_state:
        st.session_state.generated_mana_curve = None
    if 'last_selected_commander_name' not in st.session_state:
        st.session_state.last_selected_commander_name = None
    if 'selected_colors_checkbox' not in st.session_state:
        st.session_state.selected_colors_checkbox = {c: False for c in MTG_COLOR_ORDER + ['C']}
    if 'generated_deck_category_counts' not in st.session_state:
        st.session_state.generated_deck_category_counts = Counter()
    if 'generated_synergy_cards_info' not in st.session_state:
        st.session_state.generated_synergy_cards_info = []


    main_choice = st.sidebar.radio("Que voulez-vous faire ?", ("Construire un deck", "Vider le cache Scryfall"), key="main_choice_radio")

    if main_choice == "Construire un deck":
        st.header("⚙️ Définissez vos préférences de deck")
        
        # --- Section de téléchargement de l'inventaire ---
        st.markdown("📤 **Téléchargez votre fichier d'inventaire (.txt)**")
        st.markdown(
            """
            Le fichier doit être un simple fichier texte (.txt) où chaque ligne représente une carte selon la syntaxe suivante :
            `quantité Nom de la carte (SET) no de carte *F*`
            
            * **quantité** : Nombre d'exemplaires de la carte (chiffre).
            * **Nom de la carte** : Nom complet de la carte (si carte recto-verso, seul le nom de la première face est suffisant, mais le nom complet `Face1 // Face2` est aussi accepté).
            * **(SET)** : Code de l'édition entre parenthèses (ex: `(ELD)`, `(C13)`, `(AFR)`).
            * **no de carte** : Numéro de collection de la carte dans l'édition.
            * ***F*** : (Optionnel) Indique si la carte est foil, avec des astérisques de chaque côté. Si elle n'est pas foil, ne rien écrire.
            
            **Exemples de lignes valides :**
            * `1 Sol Ring (C13) 1`
            * `2 Arcane Signet (CMR) 297`
            * `1 Lightning Bolt (A25) 141 *F*`
            * `1 Balamb Garden, SeeD Academy // Balamb Garden, Airborne (UNF) 250`
            """
        )

        uploaded_file = st.file_uploader("Choisissez un fichier .txt", type="txt", key="file_uploader")

        if uploaded_file is not None:
            st.session_state.inventaire = get_inventory(uploaded_file)
            st.session_state.inventaire_loaded = True
            st.info(f"Inventaire chargé : **{sum(data['quantity_owned'] for data in st.session_state.inventaire.values())}** cartes uniques.")
            st.markdown("*(Le builder considérera 1 exemplaire par carte unique (nom+set+num), sauf pour les terrains de base qui sont illimités.)*")
        else:
            st.warning("Veuillez téléverser votre fichier d'inventaire pour commencer.")
            st.session_state.inventaire_loaded = False
            st.session_state.inventaire = {}

        if st.session_state.inventaire_loaded:
            st.markdown("---")
            st.markdown("🎨 **Préférez-vous certaines couleurs ?** (Cochez pour sélectionner)")
            selected_colors_list = []
            
            all_color_symbols_to_display = MTG_COLOR_ORDER + ['C']
            
            cols_color = st.columns(len(all_color_symbols_to_display))
            for i, color_symbol in enumerate(all_color_symbols_to_display):
                with cols_color[i]:
                    checkbox_state = st.session_state.selected_colors_checkbox.get(color_symbol, False)
                    
                    st.markdown(MANA_SYMBOL_HTML_MAP.get(color_symbol, f"({color_symbol})"), unsafe_allow_html=True)
                    label = f"{COLOR_MAP.get(color_symbol, 'Incolore')}"
                    
                    if st.checkbox(label, value=checkbox_state, key=f"color_checkbox_{color_symbol}"):
                        selected_colors_list.append(color_symbol)
                        st.session_state.selected_colors_checkbox[color_symbol] = True
                    else:
                        st.session_state.selected_colors_checkbox[color_symbol] = False
            
            if 'C' in selected_colors_list:
                st.session_state.preferences['colors'] = ['C']
                st.info("🌈 Préférence définie sur **Incolore** uniquement (précise si d'autres couleurs étaient sélectionnées).")
            else:
                st.session_state.preferences['colors'] = selected_colors_list
                if selected_colors_list:
                    st.info(f"🌈 Couleurs préférées sélectionnées : **{', '.join([COLOR_MAP[c] for c in selected_colors_list])}**")
                else:
                    st.info("🎨 Aucune couleur préférée sélectionnée. Le deck utilisera toutes les couleurs disponibles du commandant.")


            st.subheader("🎯 Choisissez une stratégie pour votre deck")
            strategies_dict = {
                'Aggro': 'aggro', 'Contrôle': 'control', 'Combo': 'combo', 'Ramp': 'ramp', 
                'Voltron': 'voltron', 'Token': 'token', 'Stax': 'stax', 'Mill': 'mill', 'Discard': 'discard',
                'Aristocrats': 'aristocrats', 'Reanimator': 'reanimator', 'Spellslinger': 'spellslinger', 
                'Enchantments Matter': 'enchantments_matter', 'Artifacts Matter': 'artifacts_matter', '+1/+1 Counters': 'counters_matter',
                'Superfriends': 'superfriends', 'Tribal': 'tribal', 'Group Hug': 'group_hug', 'Group Slug': 'group_slug',
                'Pillow Fort': 'pillow_fort', 'Theft': 'theft'
            }
            strategy_display_names = ["Aucune préférence (Deck 'amusant mais valide')"] + list(strategies_dict.keys())
            
            strategy_selected_name = st.selectbox("Sélectionnez une stratégie :", strategy_display_names, 
                                                  index=strategy_display_names.index(st.session_state.preferences.get('strategy_display_name', strategy_display_names[0])),
                                                  key="strategy_selectbox_key")

            chosen_strategy_key = None
            if strategy_selected_name != "Aucune préférence (Deck 'amusant mais valide')":
                chosen_strategy_key = strategies_dict[strategy_selected_name]
                st.session_state.preferences['strategy'] = chosen_strategy_key
                st.session_state.preferences['strategy_display_name'] = strategy_selected_name
                
                st.info(f"✨ Stratégie préférée : **{chosen_strategy_key.capitalize()}**")
                if chosen_strategy_key in STRATEGY_DESCRIPTIONS:
                    st.markdown(f"*{STRATEGY_DESCRIPTIONS[chosen_strategy_key]}*")

            else:
                st.session_state.preferences['strategy'] = None
                st.session_state.preferences['strategy_display_name'] = strategy_selected_name
                st.info("🎲 Aucune stratégie spécifique choisie. Tentative de construction d'un deck 'amusant mais valide'.")
            
            def on_find_commanders_click():
                # L'inventaire est déjà chargé si inventaire_loaded est True
                # st.session_state.inventaire = get_inventory() # Pas besoin de re-l'appeler ici

                st.session_state.deck_generated = False
                st.session_state.selected_commander_name = None
                st.session_state.last_selected_commander_name = None
                st.session_state.commanders_data = None
                st.session_state.generated_deck_details = None
                st.session_state.generated_mana_curve = None
                st.session_state.generated_deck_category_counts = Counter()
                st.session_state.generated_synergy_cards_info = []

                # Utiliser la barre de progression globale
                progress_bar_global = st.progress(0, text="Initialisation de la recherche de commandants...")
                
                # Étape 1: Recherche et évaluation des commandants (cette fonction contient ses propres st.spinner/progress)
                commanders_data_raw = identify_commanders_in_inventory(st.session_state.inventaire, st.session_state.preferences)
                st.session_state.commanders_data = commanders_data_raw

                progress_bar_global.progress(100, text="Commandants trouvés et évalués!") 
                
                if not st.session_state.commanders_data:
                    st.error("❌ Aucun commandant valide trouvé dans votre inventaire correspondant à vos préférences.")
                    st.warning("Veuillez ajuster vos préférences de couleurs/stratégies ou ajouter d'autres commandants à votre inventaire.")
                    progress_bar_global.empty()
                else:
                    st.info("Commandants trouvés et évalués. Faites votre choix ci-dessous.")
                    progress_bar_global.empty()
            
                st.session_state.deck_generated = False
                st.session_state.selected_commander_name = None
                st.session_state.last_selected_commander_name = None


            if st.button("Trouver les commandants"):
                on_find_commanders_click()

            if st.session_state.commanders_data:
                st.subheader("👑 Commandants disponibles selon vos préférences")
                
                if st.session_state.preferences.get('strategy'):
                    st.markdown(f"*{MANA_SYMBOL_HTML_MAP['C']} Le score de pertinence indique à quel point un commandant est pertinent pour la stratégie '{st.session_state.preferences['strategy'].capitalize()}', basé sur :*", unsafe_allow_html=True)
                    st.markdown(f"  *- Un bonus basé sur la présence de mots-clés stratégiques dans le texte du commandant (par ex. +10 par mot-clé).*", unsafe_allow_html=True)
                    st.markdown(f"  *- Plus 1 point pour chaque carte de support pertinente dans votre inventaire (dans ses couleurs).*", unsafe_allow_html=True)
                else:
                    st.markdown(f"*{MANA_SYMBOL_HTML_MAP['C']} Le score de pertinence générale indique le nombre total de cartes compatibles dans votre inventaire pour ce commandant.*", unsafe_allow_html=True)

                sort_options = ["Par score de pertinence total (Commandant + Cartes de support)", "Par score de pertinence du commandant uniquement"]
                if not st.session_state.preferences.get('strategy'):
                    sort_options = ["Par score de pertinence total (Commandant + Cartes de support)"]
                    if st.session_state.sort_option_name not in sort_options:
                        st.session_state.sort_option_name = sort_options[0]

                st.session_state.sort_option_name = st.radio(
                    "📊 Comment souhaitez-vous trier les commandants ?",
                    sort_options,
                    index=sort_options.index(st.session_state.sort_option_name),
                    key="sort_option_radio_key"
                )
                
                commanders_data_to_display = list(st.session_state.commanders_data)
                if st.session_state.sort_option_name == "Par score de pertinence total (Commandant + Cartes de support)":
                    commanders_data_to_display.sort(key=lambda x: (-x[3], x[0]))
                    st.info("Commandants triés par score de pertinence total.")
                else:
                    commanders_data_to_display.sort(key=lambda x: (-x[4], x[0]))
                    st.info("Commandants triés par score de pertinence du commandant.")
                
                st.markdown("---")
                st.markdown("### Choisissez votre commandant :")
                st.markdown("---")

                col_widths = [0.05, 0.35, 0.20, 0.25, 0.15]
                
                cols_header = st.columns(col_widths)
                cols_header[0].markdown("**#**")
                cols_header[1].markdown("**Nom**")
                cols_header[2].markdown("**Couleurs**")
                cols_header[3].markdown("**Score**")
                cols_header[4].markdown(" ")

                st.markdown("---")

                commandant_clicked_name = None 
                for i, (cmd_name, cmd_details, relevance_str, score_total, score_cmd_bonus, score_support_cards) in enumerate(commanders_data_to_display):
                    cmd_ci_set = get_color_identity(cmd_details)
                    sorted_ci_symbols = [c for c in MTG_COLOR_ORDER if c in cmd_ci_set]
                    formatted_ci_html = ' '.join([MANA_SYMBOL_HTML_MAP.get(s, f"({s})") for s in sorted_ci_symbols])
                    if not formatted_ci_html: formatted_ci_html = MANA_SYMBOL_HTML_MAP['C']
                    
                    score_breakdown_str = ""
                    if st.session_state.preferences.get('strategy'):
                        score_breakdown_str = (
                            f"**T:** {score_total}<br>"
                            f"**C:** {score_cmd_bonus} | **S:** {score_support_cards}"
                        )
                    else:
                        score_breakdown_str = (
                            f"**T:** {score_total}<br>"
                            f"**S:** {score_support_cards}"
                        )

                    cols = st.columns(col_widths)
                    cols[0].markdown(f"**{i+1}.**")
                    cols[1].markdown(f"**{cmd_name}**")
                    cols[2].markdown(formatted_ci_html, unsafe_allow_html=True)
                    cols[3].markdown(score_breakdown_str, unsafe_allow_html=True)
                    
                    select_button_key = f"select_cmd_{cmd_name}_{i}"
                    if cols[4].button("Choisir", key=select_button_key):
                        commandant_clicked_name = cmd_name
                
                st.markdown("---")

                if commandant_clicked_name and commandant_clicked_name != st.session_state.last_selected_commander_name:
                    st.session_state.selected_commander_name = commandant_clicked_name
                    st.session_state.last_selected_commander_name = commandant_clicked_name
                    st.session_state.deck_generated = True

                    st.info(f"Construction du deck pour : **{st.session_state.selected_commander_name}**...")
                    
                    progress_bar_global_deck_build = st.progress(0, text="Initialisation de la construction du deck...")
                    
                    deck_full_details, mana_curve_spells_cmc, deck_category_counts, synergy_cards_info = build_commander_deck(
                        st.session_state.selected_commander_name, 
                        st.session_state.inventaire, 
                        st.session_state.preferences,
                        progress_bar_global_deck_build
                    )

                    if deck_full_details:
                        st.session_state.generated_deck_details = deck_full_details
                        st.session_state.generated_mana_curve = mana_curve_spells_cmc
                        st.session_state.generated_deck_category_counts = deck_category_counts
                        st.session_state.generated_synergy_cards_info = synergy_cards_info
                    else:
                        st.session_state.deck_generated = False
                elif st.session_state.selected_commander_name and not st.session_state.deck_generated:
                    st.info(f"Commandant sélectionné : **{st.session_state.selected_commander_name}**. Cliquez sur 'Trouver les commandants' si vous voulez le reconstruire ou ajuster les préférences.")

            if st.session_state.deck_generated and st.session_state.generated_deck_details:
                st.subheader("📋 Aperçu du Deck Généré")
                deck_display_list = []
                for card_info in sorted(st.session_state.generated_deck_details, key=lambda x: x['name']):
                    foil_str = " *F*" if card_info['foil'] else ""
                    deck_display_list.append(f"1 {card_info['name']} ({card_info['set']}) {card_info['collector_number']}{foil_str}")
                st.text_area("Votre Deck :", "\n".join(deck_display_list), height=300)
                
                if CLIPBOARD_AVAILABLE:
                    archidekt_output = "\n".join(deck_display_list)
                    if st.button("Copier le deck dans le presse-papiers pour Archidekt"):
                        pyperclip.copy(archidekt_output)
                        st.success("🎉 Deck copié dans le presse-papiers au format Archidekt ! Collez-le directement. 🎉")
                else:
                    st.warning("Pyperclip n'est pas disponible. Copiez le deck manuellement.")

                st.subheader("📊 Courbe de Mana (CMC) des Sorts")
                display_cmc_chart(st.session_state.generated_mana_curve, st.session_state.selected_commander_name)

                st.subheader("📊 Statistiques du Deck")
                actual_land_count_in_final_deck = 0
                type_counts_final_deck = Counter()

                for card_info in st.session_state.generated_deck_details:
                    is_land = False
                    if card_info['name'] in [f"{COLOR_MAP.get(c, 'Colorless')} Basic Land" for c in ['W','U','B','R','G']] or card_info['name'] == 'Wastes':
                        is_land = True
                        type_counts_final_deck['Basic Land'] += 1
                    else:
                        details_for_check = get_card_details_scryfall(card_info['name'])
                        if details_for_check and "Land" in details_for_check.get('type_line', ''):
                            is_land = True
                            types = details_for_check['type_line'].split(' — ')[0].split(' ')
                            for t in types:
                                type_counts_final_deck[t] += 1
                        
                        if details_for_check and 'type_line' in details_for_check:
                            types = details_for_check['type_line'].split(' — ')[0].split(' ')
                            for t in types:
                                if t != "Land":
                                    type_counts_final_deck[t] += 1

                    if is_land:
                        actual_land_count_in_final_deck += 1
                
                st.write(f"Nombre total de cartes : **{len(st.session_state.generated_deck_details)}**")
                st.write(f"Nombre de terrains : **{actual_land_count_in_final_deck}**")

                total_cmc_spells = sum(st.session_state.generated_mana_curve)
                if st.session_state.generated_mana_curve:
                    avg_cmc = total_cmc_spells / len(st.session_state.generated_mana_curve)
                    st.write(f"Coût Converti de Mana moyen des sorts (CMC) : **{avg_cmc:.2f}**")
                
                st.write("Répartition des types de cartes :")
                for card_type, count in type_counts_final_deck.most_common():
                    st.write(f"- {card_type}: **{count}**")

                # Répartition par catégorie de sort (rampe, pioche, etc.)
                st.markdown("##### Répartition par catégorie de sort :")
                if st.session_state.generated_deck_category_counts:
                    # Filtrer les catégories pertinentes pour l'affichage
                    # S'assurer que 'threat' et 'utility' sont inclus pour les decks généraux
                    relevant_categories_for_display = [
                        'ramp', 'draw', 'spot_removal', 'board_wipe', 'threat', 'utility', 'flex_slots',
                        # Ajouter les catégories de stratégie si elles sont non-génériques
                        'token', 'voltron', 'stax', 'mill', 'discard', 'aristocrats', 'reanimator',
                        'spellslinger', 'enchantments_matter', 'artifacts_matter', 'counters_matter',
                        'superfriends', 'tribal', 'group_hug', 'group_slug', 'pillow_fort', 'theft'
                    ]
                    
                    chosen_strategy = st.session_state.preferences.get('strategy')
                    
                    displayed_categories = []
                    for cat in relevant_categories_for_display:
                        if st.session_state.generated_deck_category_counts.get(cat, 0) > 0:
                            displayed_categories.append(f"- {cat.replace('_', ' ').title()}: **{st.session_state.generated_deck_category_counts[cat]}**")
                    
                    if displayed_categories:
                        for line in displayed_categories:
                            st.write(line)
                    else:
                        st.info("Aucune catégorie de sort spécifique identifiée ou affichée pour le moment.")
                else:
                    st.info("Les catégories de sorts n'ont pas encore été calculées.")

                # Analyse de Synergie (texte)
                st.markdown("##### Analyse de Synergie :")
                if st.session_state.preferences.get('strategy') and st.session_state.generated_synergy_cards_info:
                    strategy_name = st.session_state.preferences['strategy'].capitalize()
                    st.markdown(f"Votre deck est construit autour de la stratégie **{strategy_name}**.")
                    
                    synergy_cards_for_strategy = [c['name'] for c in st.session_state.generated_synergy_cards_info if c['category'] == st.session_state.preferences['strategy']]
                    
                    if synergy_cards_for_strategy:
                        st.markdown(f"Quelques cartes qui soutiennent bien cette stratégie : **{', '.join(synergy_cards_for_strategy[:5])}{'...' if len(synergy_cards_for_strategy) > 5 else ''}**.")
                        st.markdown(f"Ces cartes ont été sélectionnées pour leurs capacités qui s'alignent avec les objectifs de la stratégie '{strategy_name}'.")
                    else:
                        st.info(f"Peu de cartes de votre inventaire ont été fortement classées pour la stratégie '{strategy_name}'.")
                else:
                    st.info("Aucune stratégie spécifique n'a été choisie, ou aucune synergie clé n'a été identifiée pour le moment.")
                
                # Suggestions de Cartes "Manquantes"
                st.markdown("##### Suggestions de Cartes Manquantes :")
                current_deck_size = len(st.session_state.generated_deck_details)
                
                suggestions_made = []
                
                if current_deck_size < TARGET_DECK_SIZE:
                    suggestions_made.append(f"- **Il manque {TARGET_DECK_SIZE - current_deck_size} cartes pour atteindre la taille standard de 100 cartes pour un deck Commander.**")

                current_lands_count = st.session_state.generated_deck_category_counts.get("Basic Land", 0) + st.session_state.generated_deck_category_counts.get("Terrain non-base", 0)
                if current_lands_count < TARGET_LAND_COUNT:
                    suggestions_made.append(f"- **Terrains** (il est recommandé d'avoir environ {TARGET_LAND_COUNT} terrains).")

                if st.session_state.generated_deck_category_counts.get('ramp', 0) < CARD_CATEGORIES_RATIOS['ramp']:
                    suggestions_made.append(f"- **Rampe de mana** (objectif: {CARD_CATEGORIES_RATIOS['ramp']} cartes).")
                
                if st.session_state.generated_deck_category_counts.get('draw', 0) < CARD_CATEGORIES_RATIOS['draw']:
                    suggestions_made.append(f"- **Pioche de cartes** (objectif: {CARD_CATEGORIES_RATIOS['draw']} cartes).")

                total_removal = st.session_state.generated_deck_category_counts.get('spot_removal', 0) + st.session_state.generated_deck_category_counts.get('board_wipe', 0)
                if total_removal < (CARD_CATEGORIES_RATIOS['spot_removal'] + CARD_CATEGORIES_RATIOS['board_wipe']):
                    suggestions_made.append(f"- **Gestion des menaces** (objectif: {CARD_CATEGORIES_RATIOS['spot_removal']} ciblées, {CARD_CATEGORIES_RATIOS['board_wipe']} de masse).")
                
                if not suggestions_made and current_deck_size == TARGET_DECK_SIZE:
                    st.info("Votre deck semble avoir une bonne répartition des types de cartes clés.")
                elif suggestions_made:
                    st.markdown("Considérez l'ajout des types de cartes suivants :")
                    for suggestion in suggestions_made:
                        st.write(suggestion)
                    st.markdown("Pensez à rechercher ces types de cartes dans votre inventaire ou à les acquérir pour améliorer la cohérence de votre deck.")
                else:
                    st.info("Aucune suggestion spécifique n'est faite pour le moment, mais vous pouvez toujours affiner votre sélection.")


    elif main_choice == "Vider le cache Scryfall":
        st.header("Vider le cache Scryfall")
        st.warning("Cela supprimera toutes les données de cartes mises en cache et forcera l'application à les re-télécharger depuis Scryfall.")
        if st.button("Confirmer la suppression du cache"):
            clear_cache_main()
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("[Scryfall](https://scryfall.com/) (ouvrir dans une nouvelle fenêtre)")
    st.sidebar.markdown("[Archidekt](https://archidekt.com/) (ouvrir dans une nouvelle fenêtre)")

if __name__ == "__main__":
    app()
