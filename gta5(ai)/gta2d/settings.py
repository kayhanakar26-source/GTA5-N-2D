"""SOKAKLAR 2D - genel ayarlar ve oyun verileri."""

TITLE = "SOKAKLAR 2D"
SCREEN_W = 1280
SCREEN_H = 720
FPS = 60

# ---------------------------------------------------------------------------
# Sehir izgarasi
# ---------------------------------------------------------------------------
TILE = 48
ROAD_W = 3          # yol genisligi (tile)
BLOCK_W = 10        # blok ici genisligi (tile)
BLOCK_H = 8         # blok ici yuksekligi (tile)
COLS = 6            # yatay blok sayisi
ROWS = 5            # dikey blok sayisi

MAP_W = COLS * BLOCK_W + (COLS + 1) * ROAD_W   # 81 tile
MAP_H = ROWS * BLOCK_H + (ROWS + 1) * ROAD_W   # 58 tile
WORLD_W = MAP_W * TILE                          # 3888 px
WORLD_H = MAP_H * TILE                          # 2784 px

# Tile turleri
ROAD = 0
WALK = 1
BUILDING = 2
GRASS = 3
LOT = 4

# ---------------------------------------------------------------------------
# Renkler
# ---------------------------------------------------------------------------
ASPHALT = (53, 56, 64)
ASPHALT_DARK = (44, 47, 54)
ASPHALT_LIGHT = (63, 66, 75)
SIDEWALK = (132, 136, 146)
SIDEWALK_LIGHT = (151, 155, 164)
SIDEWALK_DARK = (108, 112, 122)
CURB = (180, 181, 175)
GRASS = (77, 125, 76)
GRASS_DARK = (63, 105, 63)
GRASS_LIGHT = (94, 144, 85)
LOT_GROUND = (61, 63, 70)
LINE_WHITE = (224, 221, 205)
LINE_YELLOW = (218, 180, 65)
SHADOW = (28, 29, 34)

PLAYER_BODY = (42, 122, 128)
PLAYER_BODY_DARK = (31, 89, 94)
PLAYER_PANTS = (55, 61, 75)
SKIN = (206, 161, 122)
SKIN_DARK = (166, 120, 88)
HAIR = (48, 39, 34)

COP_BLUE = (47, 72, 133)
COP_BLUE_DARK = (32, 49, 93)
COP_SKIN = (196, 152, 111)
COP_HAT = (28, 38, 68)

BLOOD = (116, 20, 26)
BLOOD_DARK = (77, 13, 18)
MUZZLE = (255, 219, 112)
BULLET = (255, 240, 174)
SMOKE = (126, 128, 134)
FIRE = (240, 112, 42)

UI_BG = (14, 16, 22, 205)
UI_BG_LIGHT = (25, 28, 37, 225)
UI_BORDER = (64, 70, 84)
UI_TEXT = (231, 234, 240)
UI_DIM = (148, 154, 166)
UI_ACCENT = (247, 199, 64)
UI_RED = (226, 75, 66)
UI_GREEN = (89, 199, 119)
UI_BLUE = (83, 149, 230)

CAR_COLORS = [
    (183, 59, 52), (50, 103, 176), (211, 178, 63), (63, 143, 101),
    (203, 205, 212), (58, 62, 73), (191, 111, 49), (116, 74, 148),
    (90, 160, 168), (153, 153, 145),
]

# ---------------------------------------------------------------------------
# Silahlar
# ---------------------------------------------------------------------------
WEAPONS = {
    "pistol": {
        "name": "TABANCA", "damage": 28, "delay": 0.24, "spread": 0.028,
        "speed": 1560, "pellets": 1, "mag": 12, "reload": 1.05,
        "range": 1050, "shake": 3.2, "recoil": 0.0, "sound": "shot",
        "sound_radius": 780, "tracer": (255, 233, 150), "icon": "pistol",
    },
    "smg": {
        "name": "MAKİNELİ TABANCA", "damage": 16, "delay": 0.082, "spread": 0.085,
        "speed": 1650, "pellets": 1, "mag": 32, "reload": 1.45,
        "range": 1150, "shake": 2.4, "recoil": 1.0, "sound": "smg",
        "sound_radius": 900, "tracer": (255, 218, 120), "icon": "smg",
    },
    "shotgun": {
        "name": "POMPALI TÜFEK", "damage": 13, "delay": 0.82, "spread": 0.16,
        "speed": 1380, "pellets": 6, "mag": 6, "reload": 1.9,
        "range": 620, "shake": 7.5, "recoil": 5.0, "sound": "shotgun",
        "sound_radius": 1050, "tracer": (255, 204, 120), "icon": "shotgun",
    },
}
WEAPON_ORDER = ["pistol", "smg", "shotgun"]
START_AMMO = {
    "pistol": [12, 96],
    "smg": [32, 160],
    "shotgun": [6, 24],
}

# ---------------------------------------------------------------------------
# Araclar
# ---------------------------------------------------------------------------
CARS = {
    "sedan": {
        "label": "Sedan", "size": (78, 38), "max_speed": 550, "accel": 470,
        "brake": 900, "turn": 2.65, "health": 120, "grip": 6.4, "mass": 1.0,
    },
    "sport": {
        "label": "Spor", "size": (84, 36), "max_speed": 760, "accel": 660,
        "brake": 1000, "turn": 3.15, "health": 95, "grip": 5.4, "mass": 0.9,
    },
    "van": {
        "label": "Minibüs", "size": (90, 46), "max_speed": 420, "accel": 360,
        "brake": 720, "turn": 2.05, "health": 210, "grip": 7.4, "mass": 1.6,
    },
    "taxi": {
        "label": "Taksi", "size": (78, 38), "max_speed": 520, "accel": 445,
        "brake": 860, "turn": 2.6, "health": 110, "grip": 6.4, "mass": 1.0,
    },
}

# Ses / efekt esikleri
COP_SPEED = 205
PED_SPEED_MIN = 42
PED_SPEED_MAX = 78
MAX_BULLETS = 220
MAX_PARTICLES = 700
MAX_CORPSES = 30
