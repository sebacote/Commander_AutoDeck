# config.py

# --- Fichiers et chemins ---
# INVENTORY_FILE = 'mon_inventaire.txt' # <-- RETIRÉ: Le fichier sera téléversé par l'utilisateur
SCRYFALL_CACHE_FILE = 'scryfall_cache.json'
MANA_SYMBOLS_PATH = 'mana_symbols'

# --- API Scryfall ---
SCRYFALL_RATE_LIMIT_DELAY = 0.1 # Délai entre les requêtes Scryfall (100ms pour respecter 10 req/sec)
SCRYFALL_BATCH_SIZE = 75 # Max 75 identificateurs par requête collection

# --- Règles du Commander ---
TARGET_DECK_SIZE = 100
TARGET_LAND_COUNT = 37 # Nombre de terrains visé pour un deck Commander standard
MIN_NON_LAND_CARDS = 60 # Minimum de sorts hors terrains (après le commandant)

# --- Couleurs ---
COLOR_MAP = {'W': 'White', 'U': 'Blue', 'B': 'Black', 'R': 'Red', 'G': 'Green'}

# Ordre canonique des couleurs de Magic: The Gathering
MTG_COLOR_ORDER = ['W', 'U', 'B', 'R', 'G']

# --- Catégories de cartes pour l'auto-building (ratios indicatifs) ---
CARD_CATEGORIES_RATIOS = {
    'ramp': 8,
    'draw': 8,
    'spot_removal': 5,
    'board_wipe': 3,
    'threat': 20,
    'utility': 15,
    'flex_slots': 4
}

# --- Mots-clés pour la classification et les stratégies ---
CATEGORY_KEYWORDS = {
    'ramp': ['add', 'mana', 'search your library for a basic land', 'untap', 'produces', 'mana value', 'tutor for a land'],
    'draw': ['draw a card', 'scry', 'look at the top', 'reveal cards until', 'card advantage', 'cantrip', 'wheel'],
    'spot_removal': ['destroy target', 'exile target', 'return target', 'counter target spell', 'deal damage to target creature', 'damage to target planeswalker', 'fight', 'sacrifices a permanent'],
    'board_wipe': ['destroy all', 'exile all', 'return all', 'sacrifice all creatures', 'nonland permanents', 'all permanents', 'deal damage to all creatures'],
    'token': ['create', 'token creature', 'populate', 'tokens you control', 'token in play', 'creature token'],
    'voltron': ['attach', 'equip', 'aura', 'power and toughness', 'first strike', 'lifelink', 'trample', 'flying', 'indestructible', 'double strike', 'hexproof', 'shroud', 'vigilance', 'unblockable', 'commander damage'],
    'stax': ["can't", "skip your", "each opponent sacrifices", "nontoken creatures don't untap", "enchant player", "curse", "extra cost", "pay life", "tax", "players can't", "only one", "more to cast", "prevent untap"],
    'mill': ['mill', 'put the top cards', 'target player exiles', 'graveyard from library', 'library into their graveyard', 'each opponent mills'],
    'discard': ['discard a card', 'hand', 'opponent chooses', 'target player discards', 'discards a card', 'each opponent discards'],
    'aristocrats': ['sacrifice a creature', 'whenever you sacrifice', 'death trigger', 'dies', 'creature leaves the battlefield', 'drain life', 'lose life for each creature'],
    'reanimator': ['return target creature card from your graveyard to the battlefield', 'from graveyard to battlefield', 'reanimate', 'graveyard to play', 'unearth', 'embrace death'],
    'spellslinger': ['whenever you cast an instant or sorcery spell', 'copy target instant or sorcery spell', 'storm', 'magecraft', 'spells you control', 'whenever you cast a noncreature spell', 'noncreature spell', 'cast from graveyard', 'extra turns'],
    'enchantments_matter': ['enchantment enters the battlefield', 'enchantments you control', 'aura', 'when you cast an enchantment spell', 'enchantress'],
    'artifacts_matter': ['artifact enters the battlefield', 'artifacts you control', 'metalcraft', 'affinity', 'when you cast an artifact spell', 'historic spell'],
    'counters_matter': ['+1/+1 counter', 'put a counter', 'proliferate', 'haste if it has a counter', 'counter on it', 'remove a counter', 'double counters'],
    'superfriends': ['planeswalker enters the battlefield', 'planeswalkers you control', 'loyalty abilities', 'emblem', 'loyalty counter'],
    'tribal': ['elf', 'goblin', 'zombie', 'dragon', 'angel', 'human', 'wizard', 'vampire', 'cleric', 'warrior', 'merfolk', 'slivers', 'cat', 'dog', 'elemental'],
    'group_hug': ['each player draws', 'target player draws', 'each player gains', 'everyone draws', 'gain life', 'each player creates a token', 'all players'],
    'group_slug': ['each opponent loses life', 'whenever a player casts a spell', 'damage to each opponent', 'each opponent sacrifices a permanent', 'you lose life', 'punish', 'pay life', 'opponent takes damage'],
    'pillow_fort': ['can\'t attack you', 'cost to attack', 'prevent all combat damage', 'shroud', 'hexproof', 'protection from', 'untargetable'],
    'theft': ['gain control of target', 'take control of', 'steal', 'opponent controls', 'exile target permanent an opponent controls', 'copy target spell an opponent controls']
}


# --- Préférences de courbes de mana (nombre de sorts ciblés par CMC) ---
CMC_TARGET_DISTRIBUTION = {
    0: 1,
    1: 8,
    2: 15,
    3: 15,
    4: 10,
    5: 5,
    6: 3,
    7: 2,
    8: 1,
    9: 0,
    10: 0
}
