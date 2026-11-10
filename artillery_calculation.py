from __future__ import annotations
import asyncio
import json
import math
import os
import random
import re
import sys
import time
from pathlib import Path
from datetime import datetime
from functools import lru_cache
from dataclasses import dataclass
from urllib.parse import quote, unquote

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("PYGAME_FORCE_SCALE", "photo")

import pygame
if sys.platform == "emscripten":
    gfxdraw = None
else:
    try:
        from pygame import gfxdraw
    except ImportError:
        gfxdraw = None

# ---------------------------------------------------------------------------
# Configuración de pantalla
# ---------------------------------------------------------------------------

WIDTH, HEIGHT = 1280, 720
FPS = 30 if sys.platform == "emscripten" else 60
TITLE = "Artillery Calculation"

SAVE_DIR = Path(__file__).resolve().parent / "save_prof"
SAVE_FILE = SAVE_DIR / "scores.json"
NAME_MAX = 14

GRAVITY = 9.81
TARGET_DISTANCE = 500.0
DIST_MIN, DIST_MAX = 100, 1000
MUZZLE_MOUNT = 12.0
TARGET_MOUNT = 24.0
BULLSEYE_RADIUS = 5.0
BOARD_RADIUS = 14.25
MAX_ANGLE = 180.0
MAX_TABLE_ROWS = 3
DIANA_TOL = 0.005

ROUNDS_PER_MATCH = 10
POINTS = {"diana": 100, "acierto": 60, "cerca": 0, "lejos": 0}
MAX_HINTS = 7
HINT_COOLDOWN = 15.0
HINT_PENALTY = 0.10
ATTEMPT_PENALTY = 0.10
MIN_MULTIPLIER = 0.20
BULLET_R = 2.0
NEAR_MISS_R = 45.0
TIP_MIN_FAILS = 2
TIP_PROB = 0.35
TIP_PROB_EXHAUSTED = 0.10
TOAST_SECONDS, TOAST_TIP_SECONDS = 3.0, 4.5
AUTO_NEXT_SECONDS = 7.0
TIME_MAX = 600.0
TIME_PENALTY_BASE, TIME_PENALTY_STEP, TIME_PENALTY_MAX = 10.0, 5.0, 60.0
BALLOON_MIN_FAILS, BALLOON_LIFE = 3, 30.0
BALLOON_TIME_BONUS, FREEZE_SECONDS = 45.0, 20.0
BALLOON_R = 26
PENALIZE_NEAR_MISS = True
TIME_FLASH_SECONDS = 2.4
SHOT_CLICK_SPEED = 4.0
FIRE_COOLDOWN_SECONDS = 3.0

FIELD = pygame.Rect(16, 76, 836, 628)
FW, FH = FIELD.size
ZOOM_REF, ZOOM_MIN, ZOOM_MAX = 1.42, 0.22, 1.6
GROUND_Y_REF = 470
GUN_MARGIN, TARGET_MARGIN, TOP_MARGIN = 120, 70, 150
TIME_SCALE = 3.0
BARREL_PX = 46

PROBLEM_RECT = pygame.Rect(868, 76, 396, 168)
ANSWER_RECT = pygame.Rect(868, 254, 396, 158)
DRAWER_RECT = pygame.Rect(FIELD.x + 16, FIELD.y + 12, 560, 112)
DRAWER_CLOSE = pygame.Rect(DRAWER_RECT.right - 38, DRAWER_RECT.y + 8, 30, 30)
METHOD_RECT = pygame.Rect(868, 422, 396, 282)
MENU_TUTORIAL = pygame.Rect(656, 36, 584, 388)
MENU_RANK = pygame.Rect(656, 436, 584, 248)
RES_LEFT = pygame.Rect(64, 100, 520, 500)
RES_SAVE = pygame.Rect(620, 100, 596, 128)
RES_RANK = pygame.Rect(620, 240, 596, 360)

def screen_canvas():
    """Tamaño lógico del lienzo: misma proporción que el monitor de la máquina (mínimo 1280x720)."""
    try:
        dw, dh = pygame.display.get_desktop_sizes()[0]
    except (AttributeError, IndexError, pygame.error):
        dw, dh = WIDTH, HEIGHT
    aspect = clamp(dw / max(dh, 1), 1.0, 3.2)
    return max(WIDTH, int(round(HEIGHT * aspect))), max(HEIGHT, int(round(WIDTH / aspect)))

MENU, PLAY, RESULT = "menu", "play", "result"
AIM, FLIGHT, SETTLE, SOLVED = "aim", "flight", "settle", "solved"

C_BG = (7, 10, 24)
C_PANEL = (13, 18, 42, 228)
C_PANEL_BORDER = (110, 130, 255, 64)
C_TEXT = (233, 238, 255)
C_MUTED = (142, 154, 194)
C_ACCENT = (56, 224, 255)
C_AMBER = (255, 176, 66)
C_GOOD = (52, 224, 150)
C_WARN = (255, 196, 61)
C_BAD = (255, 92, 108)
C_VIOLET = (160, 130, 255)
C_DARK = (6, 14, 32)
C_GOLD = (255, 214, 102)
C_CORAL = (255, 138, 76)

CAT_COLOR = {"diana": C_GOLD, "acierto": C_GOOD, "cerca": C_CORAL, "lejos": C_BAD}
CAT_TITLE = {"diana": "¡DIANA PERFECTA!", "acierto": "¡BLANCO TOCADO!", "cerca": "¡CASI!", "lejos": "FALLASTE"}
PHRASES = {
    "diana": [
        "¡Buen tiro, seguro no fue chiripazo?",
        "¡EERRRDDDAAAA Papi, ud si es de buenas creálas",
        "¡Ave maría, qué elegancia! Hasta el mismo Newton se quita el sombrero ante semejante belleza",
        "Uy papi, se lució",
    ],

    "acierto": [
        "¡Blanco tocado! Afine un poquito la puntería, que no siempre suena la flauta por casualidad",
        "Le atinó? pero muy suave, un poco más al centro y era diana, no sea tan tibio",
        "A lo bien? Se la puso?",
    ],

    "cerca": [
        "¡Casiiii, pero no JA!",
        "¡Casi lo peina mijita!",
        "¡Rozó como le gusta! Una iteración más y no pasa penas",
    ],

    "lejos": [
        "¡Vaya y duerma mejor!",
        "¡Le tiró a las nubes, jmmm... cerquita del fracaso total!",
        "Falló por completo, póngale brújula socio, seriedad",
        "Fué bala pérdida, ¡Ojo se la encuentra!",
        "A lo bien perrito? Otra vez no la dió, muy buñuelo"
    ],
}

def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v

def lerp(a, b, t):
    return a + (b - a) * t

def seg_point_dist(a, b, p):
    """Distancia mínima del punto p al segmento a-b (para detectar que la bala atravesó un globo)."""
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    length = dx * dx + dy * dy
    t = 0.0 if length <= 1e-12 else clamp(((p[0] - ax) * dx + (p[1] - ay) * dy) / length, 0.0, 1.0)
    return math.hypot(ax + t * dx - p[0], ay + t * dy - p[1])

def smoothstep(t):
    t = clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)

def ease_out_cubic(t):
    return 1.0 - (1.0 - clamp(t, 0.0, 1.0)) ** 3

def ease_out_back(t):
    t = clamp(t, 0.0, 1.0)
    return 1.0 + 2.70158 * (t - 1.0) ** 3 + 1.70158 * (t - 1.0) ** 2

def mix(a, b, t):
    t = clamp(t, 0.0, 1.0)
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))

def fade_color(color, k):
    return tuple(int(c * clamp(k, 0.0, 1.0)) // 16 * 16 for c in color)

def fmt_time(seconds):
    s = int(math.ceil(max(0.0, seconds)))
    return f"{s // 60}:{s % 60:02d}"

def parse_angle(text):
    try:
        return float(text.replace(",", "."))
    except ValueError:
        return None

# ---------------------------------------------------------------------------
# Física y aplicación del método de Newton-Raphson (cálculos y ecuaciones)
# ---------------------------------------------------------------------------

def coefficient(speed, dist):
    """c = g·D² / (2·v0²), constante de la parábola evaluada en x = D."""
    return GRAVITY * dist ** 2 / (2.0 * speed ** 2)

def f_angle(X, c, height, dist, side=1):
    """f(X): error de altura de la bala al llegar al blanco; el ángulo (X) es la incógnita.
    side = +1 blanco a la derecha, -1 a la izquierda; (X) se mide siempre desde la derecha."""
    t = side * math.tan(X)
    return dist * t - c * (1.0 + t * t) - height

def df_angle(X, c, dist, side=1):
    t = side * math.tan(X)
    return side * (1.0 + t * t) * (dist - 2.0 * c * t)

@dataclass(frozen=True)
class Step:
    n: int
    X: float
    fx: float
    dfx: float
    nxt: float

def newton_raphson(X0, c, height, dist, side=1, tol=1e-10, max_iter=25):
    """Resuelve f(X) = 0 con Newton-Raphson desde la semilla X0 (ángulo inicial (X)).
    Devuelve (raíz, iteraciones). Todo el cálculo se hace en radianes."""
    steps, X = [], X0
    for n in range(max_iter):
        fx, dfx = f_angle(X, c, height, dist, side), df_angle(X, c, dist, side)
        if abs(dfx) < 1e-12:
            break
        nxt = X - fx / dfx
        steps.append(Step(n, X, fx, dfx, nxt))
        converged = abs(nxt - X) < tol
        X = nxt
        if converged:
            break
    return X, steps

def terrain_height(x, plateau, dist, side=1):
    """Altura del terreno (m, relativa al cañón) bajo la coordenada x (positiva a la derecha)."""
    u = side * x
    base = -MUZZLE_MOUNT
    span = min(70.0 + 0.7 * max(0.0, plateau - base), max(30.0, dist - 65.0))
    rise = smoothstep((u - (dist - 60.0 - span)) / span)
    fall = smoothstep((u - (dist + 60.0)) / 70.0)
    return base + (plateau - base) * (rise - fall)

def path_is_clear(X, c, plateau, dist, side=1):
    t = side * math.tan(X)
    for u in range(20, int(dist - BOARD_RADIUS), 5):
        y = u * t - c * (u / dist) ** 2 * (1.0 + t * t)
        if y < terrain_height(side * u, plateau, dist, side) + 6.0:
            return False
    return True

SCENARIOS = {
    "plano": [
        ("DRON ENEMIGO", "Un dron aterrizó en el llano, {lado}. Derríbalo con un solo disparo.", "DRON"),
        ("ANTENA DE RADIO", "Hay que tumbar una antena de radio en terreno plano, {lado}.", "ANTENA"),
        ("PRÁCTICA DE TIRO", "Hoy toca práctica en el campo plano. El blanco está {lado}.", "DIANA"),
        ("CAMIÓN ABANDONADO", "Un camión enemigo quedó varado en la llanura, {lado}.", "CAMIÓN"),
    ],
    "colina": [
        ("RADAR EN LA COLINA", "Un radar vigila desde lo alto de la colina, {lado}. ¡Apágalo!", "RADAR"),
        ("GLOBO VIGÍA", "Un globo espía flota sobre el cerro, {lado}. Derríbalo.", "GLOBO"),
        ("TORRE DE VIGÍA", "Una torre de vigilancia sobresale en la loma, {lado}.", "TORRE"),
        ("FARO ENEMIGO", "Un faro enemigo ilumina la zona desde la colina, {lado}.", "FARO"),
    ],
    "valle": [
        ("BODEGA ESCONDIDA", "Una bodega de suministros se esconde en el valle, {lado}.", "BODEGA"),
        ("PUENTE ENEMIGO", "El puente del valle, {lado}, es el paso del enemigo. Destrúyelo.", "PUENTE"),
        ("CAMPAMENTO", "Un campamento enemigo acampó en la hondonada, {lado}.", "CAMPAMENTO"),
        ("TANQUE ATASCADO", "Un tanque quedó atascado en el fondo del valle, {lado}.", "TANQUE"),
    ],
}

SCENARIOS["cumbre"] = [
    ("ANTENA EN LA CUMBRE", "Una antena enemiga corona la cumbre de la montaña, {lado}.", "ANTENA"),
    ("NIDO DE ÁGUILAS", "El nido de águilas del enemigo está en lo más alto, {lado}.", "NIDO"),
    ("TORRE DE CONTROL", "La torre de control domina el risco, {lado}. ¡Hay que derribarla!", "TORRE"),
    ("OBSERVATORIO", "Un observatorio enemigo vigila desde el pico, {lado}.", "OBSERV."),
]

@dataclass(frozen=True)
class Problem:
    kind: str
    speed: float
    height: float
    c: float
    plateau: float
    seed_deg: float
    root_deg: float
    steps: tuple
    dist: float = TARGET_DISTANCE
    side: int = 1
    arc: str = "bajo"
    title: str = ""
    story: str = ""
    tname: str = "BLANCO"
    ans_row: int = 2 

def height_cap(phi_deg):
    """Altura máxima del blanco (m): cuanto mayor es el ángulo de tiro, más alto puede estar."""
    return 40.0 + 5.5 * max(0.0, phi_deg - 20.0)

def make_problem(round_index, rng=random, avoid=None):

    """Genera un problema válido: distancia 100-1000 m, altura variable, lado y contexto.
    El ángulo (X) se mide desde la derecha (0°) hasta la izquierda (180°). Se parte de un
    ángulo deseado y de la altura que ese ángulo permite (a 75° el blanco puede
    estar mucho más alto que a 20°); de ahí se deduce la velocidad v0 y se recalcula la raíz
    exacta. Solo se acepta si la trayectoria llega sin chocar con el terreno."""

    while True:
        if round_index == 0:
            kind, side, group = "plano", 1, "bajo"
        else:
            side = rng.choices((1, -1), (7, 3))[0]
            group = rng.choices(("bajo", "alto"), (8, 3))[0]
            weights = (1, 1, 4, 5) if group == "alto" else (2, 2, 4, 1) 
            kind = rng.choices(("plano", "valle", "colina", "cumbre"), weights)[0]
        target = 2 if round_index == 0 else rng.randrange(MAX_TABLE_ROWS)
        for _ in range(900):
            dist = float(rng.randrange(200, 501, 10) if round_index == 0
                         else rng.randrange(DIST_MIN, DIST_MAX + 1, 10))
            if round_index == 0:
                phi0 = rng.uniform(10.0, 30.0)
            else:
                phi0 = rng.uniform(8.0, 42.0) if group == "bajo" else rng.uniform(50.0, 80.0)
            cap = height_cap(phi0)
            if kind == "plano":
                height = 0.0
            elif kind == "valle":
                height = -float(rng.randrange(10, 65, 5))
            elif kind == "colina":
                if cap < 25:
                    continue
                top = int(min(150.0, cap))
                height = float(rng.randrange(max(10, int(top * 0.45)), top, 5))
            else:
                if cap <= 160:
                    continue
                height = float(rng.randrange(max(150, int(cap * 0.6)), int(cap), 5))
            t0 = math.tan(math.radians(phi0))
            gap = dist * t0 - height
            if gap <= 0:
                continue
            speed = float(round(dist * math.sqrt(GRAVITY * (1.0 + t0 * t0) / (2.0 * gap))))
            if not 25.0 <= speed <= 260.0:
                continue
            c = coefficient(speed, dist)
            disc = dist ** 2 - 4.0 * c * (c + height)
            if disc <= 0:
                continue
            sq = math.sqrt(disc)
            lows, highs = (dist - sq) / (2.0 * c), (dist + sq) / (2.0 * c)
            T = lows if abs(math.atan(lows) - math.radians(phi0)) <= abs(math.atan(highs) - math.radians(phi0)) else highs
            phi_deg = math.degrees(math.atan(T))
            if abs(phi_deg - phi0) > 6.0 or not 6.0 <= phi_deg <= 85.0:
                continue
            arc = "alto" if T > dist / (2.0 * c) else "bajo"
            root_deg = phi_deg if side == 1 else 180.0 - phi_deg
            root = math.radians(root_deg)
            lo, hi = (3.0, 88.0) if side == 1 else (92.0, 177.0)
            if target == 0:
                offset, digits = rng.uniform(-0.003, 0.003), 3
            elif target == 1: 
                offset, digits = rng.choice((-1, 1)) * (rng.uniform(0.2, 1.2) if arc == "bajo" else rng.uniform(0.1, 0.6)), 2
            else:
                offset, digits = rng.choice((-1, 1)) * (rng.uniform(4.0, 9.0) if arc == "bajo" else rng.uniform(1.5, 5.0)), 0
            seed_deg = float(round(clamp(root_deg + offset, lo, hi), digits))
            _, steps = newton_raphson(math.radians(seed_deg), c, height, dist, side, tol=0.0, max_iter=MAX_TABLE_ROWS)
            if len(steps) < MAX_TABLE_ROWS:
                continue
            ans_row = next((i for i, st in enumerate(steps) if abs(st.X - root) <= math.radians(DIANA_TOL)), None)
            if ans_row != target:
                continue
            shown = tuple(steps)
            plateau = height - TARGET_MOUNT
            if not path_is_clear(root, c, plateau, dist, side):
                continue
            pool = [s for s in SCENARIOS[kind] if s[0] != avoid] or SCENARIOS[kind]
            title, story, tname = rng.choice(pool)
            story = story.format(lado="a tu izquierda" if side < 0 else "a tu derecha")
            return Problem(kind, speed, height, c, plateau, seed_deg, root_deg, shown,
                           dist, side, arc, title, story, tname, ans_row)

def _span(root, width, rng):
    """Intervalo de `width` grados que contiene a la raíz en una posición al azar."""
    start = math.floor(root - rng.uniform(0.15, 0.85) * width)
    return start, start + width

def fmt_deg(value):
    return f"{value:.3f}".rstrip("0").rstrip(".")

def build_hints(p, rng=random):
    """Siete pistas progresivas (título, texto, rango|None). Cada ecuación elige variantes
    distintas al azar; solo la séptima revela el ángulo (X)."""
    root, seed = p.root_deg, p.seed_deg
    lo1 = math.floor(root)
    if p.side < 0 and p.arc == "alto":
        extra = " Tiro alto a la izquierda: el ángulo está entre 90° y 140°."
    elif p.side < 0:
        extra = " A tu izquierda: el ángulo será mayor que 90°."
    elif p.arc == "alto":
        extra = " Tiro alto: el ángulo será mayor que 45°."
    else:
        extra = ""
    a0, a1 = _span(root, 5, rng)
    b0, b1 = _span(root, 8, rng)
    s1 = rng.choice((
        ("Entiende f(X)", "f(X) mide cuánto falla la bala en altura al llegar al blanco. "
                          f"Si f(X) = 0, pasa por el centro: busca ese X.{extra}"),
        ("Piensa en el error", "Imagina f(X) como el «error de altura» en el blanco. "
                               f"Newton-Raphson mueve X poco a poco hasta que ese error sea 0.{extra}"),
        ("Ubica el blanco", "Antes de calcular, mira dónde está el blanco: ¿derecha o izquierda, arriba o abajo? "
                            f"Eso decide qué tan grande será el ángulo.{extra}"),
    ))
    s2 = rng.choice((
        ("Acota el ángulo", f"El ángulo está entre {a0}° y {a1}°. Fuera de ese rango no hay solución.", (a0, a1)),
        ("Un rango de prueba", f"Mira este rango: de {b0}° a {b1}°. Tu ángulo está ahí dentro.", (b0, b1)),
        ("Dispara de prueba", f"Prueba cerca de {round(root / 10.0) * 10:.0f}° y mira si la bala queda corta o larga. "
                              "Luego corrige.", None),
    ))
    if p.ans_row == 2:  
        th1 = math.degrees(p.steps[0].nxt)
        s3 = rng.choice((
            ("Usa la semilla", f"Empieza con la semilla X_{{0}} = {fmt_deg(seed)}°. La tabla muestra 3 iteraciones "
                               "seguidas: una de sus filas guarda la respuesta.", None),
            ("Primer ángulo de prueba", f"Usa X_{{0}} = {fmt_deg(seed)}° como primer intento. La tabla muestra cuánto "
                                        "falla (f) y qué tan inclinada es la curva (f').", None),
        ))
        s4 = rng.choice((
            ("Primera corrección", f"X_{{1}} = X_{{0}} - f(X_{{0}}) / f'(X_{{0}}) = {th1:.3f}°. Ya estás más cerca.", None),
            ("Aplica la fórmula", f"Si usas la fórmula una vez obtienes X_{{1}} = {th1:.3f}°. "
                                  "Pruébalo o sigue corrigiendo.", None),
        ))
    else: 
        s3 = rng.choice((
            ("Lee la tabla", "La tabla muestra 3 iteraciones seguidas. Cuando X casi no cambia de una fila a otra, "
                             "ahí está la respuesta.", None),
            ("Busca la fila clave", "Una de las 3 filas guarda el ángulo exacto: es donde f(X) vale casi 0.", None),
        ))
        s4 = rng.choice((
            ("Aplica la fórmula", "Cada vez que usas la fórmula, X cambia menos. La fila donde casi no cambia "
                                  "tiene la respuesta.", None),
            ("Compara filas", "Mira cómo cambia X entre una fila y la siguiente: el cambio se hace cada vez más pequeño.", None),
        ))
    s5 = rng.choice((
        ("Sigue iterando", "Repite la fórmula con el X nuevo. Cada vez el error f(X) se acerca más a 0: "
                           "míralo en la tabla.", None),
        ("Truco del error", "Cuando f(X) ya es casi 0, el ángulo es casi perfecto. "
                            "Fíjate en la columna f(X) de la tabla.", None),
    ))
    s6 = rng.choice((
        ("Casi converge", f"El ángulo ya está entre {lo1}° y {lo1 + 1}°. Afina los decimales: "
                          f"la diana exige ±{DIANA_TOL}°.", (lo1, lo1 + 1)),
        ("Empieza por aquí", f"Dispara con {root:.1f}° y ajusta con milésimas. Ya estás muy cerca.", (lo1, lo1 + 1)),
    ))
    s7 = rng.choice((
        ("Respuesta", f"X = {root:.3f}°. Escríbelo y dispara. La tabla ya muestra todas las iteraciones.", None),
        ("Aquí la tienes", f"El ángulo exacto es {root:.3f}°. ¡Escríbelo y dispara!", None),
    ))
    return [(*s1, None), s2, s3, s4, s5, s6, s7]

def reveal_order(ans_row, total=MAX_TABLE_ROWS):
    """Orden en que las pistas destapan la tabla: primero f(X) y f'(X) de cada fila y luego X.
    La X de la fila de la respuesta (y las siguientes) solo aparece con la última pista."""
    order = [3 * r + c for r in range(total) for c in (1, 2)]
    return order + [3 * r for r in range(ans_row)]

def cells_revealed(hints, ans_row, total=MAX_TABLE_ROWS):
 
    if hints <= 0:
        return frozenset()
    if hints >= MAX_HINTS:
        return frozenset(range(3 * total))
    order = reveal_order(ans_row, total)
    return frozenset(order[: math.ceil(len(order) * hints / (MAX_HINTS - 1))])

class Shot:

    def __init__(self, angle_deg, problem):
        self.X = math.radians(angle_deg)  
        self.problem = problem
        self.t = 0.0
        self.pos = (0.0, 0.0)
        self.path = [self.pos]
        self.path_t = 0.0
        self.kind = None
        self.impact = None
        self.dist = math.hypot(problem.dist, problem.height)  
        self.best = self.dist  
        self.best_pos = self.pos
        self.inside = False

    @property
    def done(self):
        return self.kind is not None

    def advance(self, dt):
        p = self.problem
        factor = TIME_SCALE * (2.4 if abs(self.pos[0]) > p.dist + 150.0 else 1.0)
        tx = p.side * p.dist 
        goal = self.t + dt * factor
        touch = BOARD_RADIUS + BULLET_R
        while self.t < goal and not self.done:
            step = 0.002 if self.dist < 80.0 else 0.02
            self.t = min(goal, self.t + step)
            x = p.speed * math.cos(self.X) * self.t
            y = p.speed * math.sin(self.X) * self.t - 0.5 * GRAVITY * self.t ** 2
            self.pos = (x, y)
            if self.t - self.path_t >= 0.02 - 1e-9:
                self.path.append(self.pos)
                self.path_t = self.t
            prev, self.dist = self.dist, math.hypot(x - tx, y - p.height)
            if self.dist < self.best:
                self.best, self.best_pos = self.dist, self.pos
            if self.dist <= touch:
                self.inside = True
            if self.inside and self.dist > prev:
 
                self.kind, self.impact = "target", self.best_pos
                self.pos = self.best_pos
                self.path.append(self.best_pos)
                break
            ground = terrain_height(x, p.plateau, p.dist, p.side)
            if y <= ground:
                self.kind, self.impact = "ground", (x, ground)
            elif self.t > 120.0:
                self.kind, self.impact = "lost", self.pos

def judge(shot, error_deg):
    """Categoría del disparo. Tocar el blanco es acierto; la diana exige el ángulo (X) exacto:
    a lo sumo DIANA_TOL grados (5 milésimas) de diferencia con la respuesta."""
    if shot.kind == "target":
        return "diana" if error_deg <= DIANA_TOL else "acierto"
    return "cerca" if shot.best <= NEAR_MISS_R else "lejos"

TIPS_GENERAL = (
    "Haz cambios grandes al inicio (de 5° en 5°) y afina después con décimas.",
    "Mira dónde cayó la bala y corrige solo la mitad de lo que te equivocaste.",
    "Cambia el ángulo poco a poco: medio grado ya mueve la bala varios metros.",
    "Anota cada intento: así ves si te estás acercando o alejando del blanco.",
    "Usa la semilla X_{0} de la tabla como primer intento: suele estar cerca.",
    "Lee el mensaje «SUBE X» o «BAJA X» después de fallar: te dice hacia dónde corregir.",
    "Para la diana hace falta el ángulo con milésimas: la tolerancia es de solo ±0.005°.",
    "Si tocas el blanco pero no es diana, afina los decimales del ángulo.",
    "Si te trabas, pulsa «Nueva ecuación»: no pierdes nada y pruebas otro reto.",
)
TIPS_HINT = (
    "Usa la bombilla: una pista cuesta 10 % de puntos, pero ahorra varios intentos.",
    "Pide una pista mientras piensas tu siguiente ángulo: se recarga cada 15 segundos.",
)
TIPS_LEFT = (
    "El blanco está a tu izquierda: prueba ángulos mayores que 90° (por ejemplo 150°).",
    "El ángulo siempre se mide desde la derecha: 180° apunta justo hacia la izquierda.",
)
TIPS_HIGH = (
    "En un tiro alto el ángulo es grande: la bala sube mucho y cae casi vertical.",
)
TIPS_KIND = {
    "plano": ("En terreno plano el ángulo suele ser el más sencillo de encontrar.",),
    "colina": ("La colina sube el blanco: tendrás que apuntar un poco más alto que en terreno plano.",),
    "valle": ("El valle baja el blanco: con apuntar un poco más bajo ya llega.",),
    "cumbre": ("La cumbre está muy alta: tendrás que apuntar mucho más alto que en terreno plano.",),
}

BALLOON_KINDS = (("doble", C_GOLD), ("congelar", C_ACCENT), ("tiempo", C_GOOD), ("pista", C_AMBER))

@dataclass
class Match:
    points: int = 0
    bulls: int = 0   
    touches: int = 0  
    near: int = 0   
    far: int = 0   
    hints: int = 0
    shots: int = 0  

    @property
    def hits(self):
        return self.bulls + self.touches

    @property
    def errors(self):
        return self.near + self.far

def clean_name(raw):
    return " ".join(raw.split())[:NAME_MAX]

class ScoreStore:
    """Estadísticas por jugador en cookies (web) o save_prof/scores.json (escritorio)."""

    def __init__(self, path=None):
        self.path = Path(path) if path else SAVE_FILE

    def _read(self):
        if sys.platform == "emscripten":
            import platform

            data = {}
            for cookie in str(platform.window.document.cookie).split(";"):
                key, separator, value = cookie.strip().partition("=")
                if not separator or not key.startswith("artillery_score_"):
                    continue
                try:
                    name = unquote(key[len("artillery_score_"):])
                    entry = json.loads(unquote(value))
                except (TypeError, ValueError):
                    continue
                if isinstance(entry, dict):
                    data[name] = entry
            return data
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _num(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def ranking(self, limit=8):
        rows = []
        for name, entry in self._read().items():
            if not isinstance(entry, dict):
                continue
            games = self._num(entry.get("partidas"))
            if games <= 0:
                continue
            hits = self._num(entry.get("aciertos_totales"))
            attempts = max(self._num(entry.get("intentos_totales")), hits)
            errors = attempts - hits
            rows.append({
                "name": str(name),
                "games": games,
                "hits": hits,
                "errors": errors,
                "ratio": hits / max(errors, 1),
                "average": self._num(entry.get("puntos_totales")) / games,
                "effectiveness": hits / attempts if attempts else 0.0,
            })
        rows.sort(key=lambda r: (r["average"], r["effectiveness"], r["games"]), reverse=True)
        return rows[:limit]

    def save_match(self, name, points, hits, attempts):
        """Guarda UN registro por jugador. Devuelve "ok", "exists" (nombre ya registrado),
        "invalid" (sin nombre) o "error" (no se pudo escribir)."""
        name = clean_name(name)
        if not name:
            return "invalid"
        data = self._read()
        if any(k.casefold() == name.casefold() for k in data):
            return "exists"
        data[name] = {
            "puntos_totales": points,
            "aciertos_totales": hits,
            "intentos_totales": attempts,
            "partidas": 1,
            "mejor_puntuacion": points,
            "ultima_fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        if sys.platform == "emscripten":
            import platform

            cookie_name = quote(f"artillery_score_{name}", safe="")
            cookie_value = quote(json.dumps(data[name], ensure_ascii=False, separators=(",", ":")), safe="")
            platform.window.document.cookie = (
                f"{cookie_name}={cookie_value}; path=/; max-age=31536000; samesite=lax"
            )
            return "ok" if name in self._read() else "error"
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self.path)
        except OSError:
            return "error"
        return "ok"

def aa_circle(dst, color, center, radius):
    x, y, r = int(center[0]), int(center[1]), int(radius)
    if r < 1 or not -300 < x < dst.get_width() + 300 or not -300 < y < dst.get_height() + 300:
        return
    if gfxdraw is None:
        pygame.draw.circle(dst, color, (x, y), r)
    else:
        gfxdraw.filled_circle(dst, x, y, r, color)
        gfxdraw.aacircle(dst, x, y, r, color)

@lru_cache(maxsize=128)
def glow_surface(radius, color):
    surf = pygame.Surface((radius * 2, radius * 2))
    for r in range(radius, 0, -1):
        k = (1.0 - r / radius) ** 2
        pygame.draw.circle(surf, (int(color[0] * k), int(color[1] * k), int(color[2] * k)), (radius, radius), r)
    return surf

def add_glow(dst, pos, radius, color):
    radius = max(2, int(radius))
    dst.blit(glow_surface(radius, tuple(color)), (pos[0] - radius, pos[1] - radius),
             special_flags=pygame.BLEND_RGB_ADD)

def vertical_gradient(size, stops):
    w, h = size
    surf = pygame.Surface(size)
    for y in range(h):
        t = y / max(1, h - 1)
        color = stops[-1][1]
        for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
            if t <= p1:
                color = mix(c0, c1, (t - p0) / max(1e-6, p1 - p0))
                break
        pygame.draw.line(surf, color, (0, y), (w, y))
    return surf

def draw_logo(dst, center, r, color=C_ACCENT):
    cx, cy = center
    pygame.draw.circle(dst, color, center, r, 2)
    pygame.draw.circle(dst, color, center, int(r * 0.52), 2)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        pygame.draw.line(dst, color, (cx + dx * (r - 3), cy + dy * (r - 3)), (cx + dx * (r + 5), cy + dy * (r + 5)), 2)
    pygame.draw.circle(dst, C_AMBER, center, max(2, r // 6))

def make_icon():
    icon = pygame.Surface((64, 64), pygame.SRCALPHA)
    pygame.draw.circle(icon, (12, 18, 44), (32, 32), 31)
    draw_logo(icon, (32, 32), 20)
    return icon

class UI:
    """Fuentes, caché de texto con subíndices y superficies redondeadas."""

    SANS = "segoeui,helveticaneue,sfprodisplay,inter,arial,dejavusans,freesans"
    MONO = "consolas,menlo,dejavusansmono,couriernew,freemono"
    MARKUP = re.compile(r"(_\{[^}]*\}|\^\{[^}]*\})")

    def __init__(self):
        self.styles = {}
        self.text_cache, self.shape_cache, self.wrap_cache = {}, {}, {}
        spec = {
            "label": (self.SANS, 12, True), "tiny": (self.SANS, 12, False),
            "small": (self.SANS, 13, False), "small_b": (self.SANS, 13, True),
            "body": (self.SANS, 15, False), "body_b": (self.SANS, 15, True),
            "lead": (self.SANS, 18, False),
            "h2": (self.SANS, 17, True), "h1": (self.SANS, 22, True),
            "title": (self.SANS, 27, True), "btn": (self.SANS, 17, True), "btn_s": (self.SANS, 14, True),
            "input": (self.SANS, 22, True), "stat": (self.SANS, 30, True),
            "big": (self.SANS, 40, True), "score": (self.SANS, 84, True),
            "mono": (self.MONO, 14, False), "mono_s": (self.MONO, 13, False),
            "mono_b": (self.MONO, 14, True),
        }
        for name, (family, size, bold) in spec.items():
            self.add(name, family, size, bold)

    def add(self, name, family, size, bold):
        font = pygame.font.SysFont(family, size, bold=bold)
        sub = pygame.font.SysFont(family, max(8, int(size * 0.72)), bold=bold)
        self.styles[name] = (font, sub)

    def fit_style(self, text, family, max_w, start, bold=True):
        for size in range(start, 20, -2):
            self.add(f"fit_{size}", family, size, bold)
            if self.styles[f"fit_{size}"][0].size(text)[0] <= max_w:
                return f"fit_{size}"
        return f"fit_{size}"

    def _pieces(self, markup):
        for part in self.MARKUP.split(markup):
            if not part:
                continue
            if part.startswith("_{"):
                yield part[2:-1], "sub"
            elif part.startswith("^{"):
                yield part[2:-1], "sup"
            else:
                yield part, "main"

    def measure(self, markup, style):
        font, sub = self.styles[style]
        return sum((font if kind == "main" else sub).size(text)[0] for text, kind in self._pieces(markup))

    def _render(self, markup, style, color):
        font, sub = self.styles[style]
        if "_{" not in markup and "^{" not in markup:
            return font.render(markup, True, color)
        parts = []
        for text, kind in self._pieces(markup):
            if kind == "main":
                parts.append((font.render(text, True, color), 0))
            else:
                parts.append((sub.render(text, True, color), int(font.get_height() * 0.30) if kind == "sub" else 0))
        surf = pygame.Surface((sum(s.get_width() for s, _ in parts), font.get_height() + 2), pygame.SRCALPHA)
        x = 0
        for s, dy in parts:
            surf.blit(s, (x, dy))
            x += s.get_width()
        return surf

    def surf(self, markup, style, color):
        key = (markup, style, tuple(color))
        cached = self.text_cache.get(key)
        if cached is None:
            if len(self.text_cache) > 900:
                self.text_cache.clear()
            cached = self.text_cache[key] = self._render(markup, style, color)
        return cached

    def text(self, dst, markup, style, color, pos, anchor="topleft"):
        s = self.surf(markup, style, color)
        rect = s.get_rect(**{anchor: (int(pos[0]), int(pos[1]))})
        dst.blit(s, rect)
        return rect

    def wrap(self, markup, style, max_w):
        key = (markup, style, max_w)
        if key in self.wrap_cache:
            return self.wrap_cache[key]
        lines, line = [], ""
        for word in markup.split(" "):
            trial = f"{line} {word}".strip()
            if line and self.measure(trial, style) > max_w:
                lines.append(line)
                line = word
            else:
                line = trial
        if line:
            lines.append(line)
        self.wrap_cache[key] = lines
        return lines

    def paragraph(self, dst, markup, style, color, pos, max_w, gap=3):
        x, y = pos
        line_h = self.styles[style][0].get_linesize()
        for line in self.wrap(markup, style, max_w):
            dst.blit(self.surf(line, style, color), (x, y))
            y += line_h + gap
        return y

    def rounded(self, size, radius, color, border=None, border_w=1):
        key = (size, radius, color, border, border_w)
        cached = self.shape_cache.get(key)
        if cached is None:
            ss = 3
            big = pygame.Surface((size[0] * ss, size[1] * ss), pygame.SRCALPHA)
            big.fill((*color[:3], 0))
            rect = big.get_rect()
            pygame.draw.rect(big, color, rect, border_radius=radius * ss)
            if border:
                pygame.draw.rect(big, border, rect, border_w * ss, border_radius=radius * ss)
            cached = self.shape_cache[key] = pygame.transform.smoothscale(big, size)
        return cached

    def card(self, dst, rect, accent=None, fill=C_PANEL, border=C_PANEL_BORDER, radius=18):
        dst.blit(self.rounded(rect.size, radius, fill, border), rect.topleft)
        if accent:
            pygame.draw.rect(dst, accent, (rect.x + 18, rect.y, 44, 3), border_radius=2)

    def pill(self, dst, text, color, right, y, style="label"):
        w = self.measure(text, style) + 22
        rect = pygame.Rect(right - w, y, w, 22)
        dst.blit(self.rounded(rect.size, 11, (*color, 46), (*color, 150)), rect.topleft)
        self.text(dst, text, style, color, rect.center, "center")

class TextInput:
    def __init__(self, rect, placeholder, max_len, numeric, sticky=False, suffix=""):
        self.rect = pygame.Rect(rect)
        self.placeholder, self.max_len, self.numeric = placeholder, max_len, numeric
        self.sticky, self.suffix = sticky, suffix
        self.text, self.cursor, self.focused, self.blink = "", 0, sticky, 0.0

    def set_text(self, text):
        self.text = text[: self.max_len]
        self.cursor = len(self.text)

    def update(self, dt):
        self.blink = (self.blink + dt) % 1.0

    def _allowed(self, ch):
        if self.numeric:
            return ch.isdigit() and ch.isascii() or (ch in ".," and not any(c in ".," for c in self.text))
        return ch.isalnum() or ch in " _-."

    def handle(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            hit = self.rect.collidepoint(e.pos)
            self.focused = hit or self.sticky
            self.blink = 0.0
            return
        if not self.focused:
            return
        if e.type == pygame.TEXTINPUT:
            for ch in e.text:
                if len(self.text) < self.max_len and self._allowed(ch):
                    self.text = self.text[: self.cursor] + ch + self.text[self.cursor:]
                    self.cursor += 1
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_BACKSPACE and self.cursor > 0:
                self.text = self.text[: self.cursor - 1] + self.text[self.cursor:]
                self.cursor -= 1
            elif e.key == pygame.K_DELETE:
                self.text = self.text[: self.cursor] + self.text[self.cursor + 1:]
            elif e.key == pygame.K_LEFT:
                self.cursor = max(0, self.cursor - 1)
            elif e.key == pygame.K_RIGHT:
                self.cursor = min(len(self.text), self.cursor + 1)
            elif e.key == pygame.K_HOME:
                self.cursor = 0
            elif e.key == pygame.K_END:
                self.cursor = len(self.text)
        self.blink = 0.0

    def draw(self, ui, dst, error=False, enabled=True):
        border = C_BAD if error else C_ACCENT if self.focused and enabled else (74, 90, 160)
        dst.blit(ui.rounded(self.rect.size, 12, (14, 20, 48, 255), border, 2), self.rect.topleft)
        x, cy = self.rect.x + 16, self.rect.centery
        if self.text:
            ui.text(dst, self.text, "input", C_TEXT if enabled else C_MUTED, (x, cy), "midleft")
        else:
            ui.text(dst, self.placeholder, "input", (82, 94, 140), (x, cy), "midleft")
        if self.suffix:
            ui.text(dst, self.suffix, "input", C_MUTED, (self.rect.right - 16, cy), "midright")
        if self.focused and enabled and self.blink < 0.55:
            cx = x + ui.measure(self.text[: self.cursor], "input")
            pygame.draw.rect(dst, C_ACCENT, (cx + 1, cy - 14, 2, 28))

class Button:
    KINDS = {
        "primary": ((56, 224, 255), C_DARK),
        "fire": ((255, 176, 66), (36, 16, 4)),
        "good": ((52, 224, 150), (4, 28, 18)),
        "ghost": ((34, 46, 100), (222, 230, 255)),
    }

    def __init__(self, rect, label, kind="primary", icon=None, style="btn"):
        self.rect, self.label, self.kind, self.icon = pygame.Rect(rect), label, kind, icon
        self.style = style
        self.enabled, self.hover, self.pressed = True, 0.0, False

    def update(self, dt, mouse):
        goal = 1.0 if self.enabled and self.rect.collidepoint(mouse) else 0.0
        self.hover += (goal - self.hover) * min(1.0, dt * 14.0)

    def handle(self, e):
        if not self.enabled:
            self.pressed = False
            return False
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rect.collidepoint(e.pos):
            self.pressed = True
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            was, self.pressed = self.pressed, False
            return was and self.rect.collidepoint(e.pos)
        return False

    def draw(self, ui, dst):
        base, fg = self.KINDS[self.kind]
        if self.enabled:
            fill = mix(base, (255, 255, 255), round(self.hover * 5) / 5 * 0.24)
        else:
            fill, fg = (40, 48, 86), (112, 124, 166)
        rect = self.rect.move(0, 2 if self.pressed else 0)
        if self.enabled:
            dst.blit(ui.rounded(rect.size, 13, (0, 0, 0, 90)), (rect.x, rect.y + 4))
        border = (104, 122, 214) if self.kind == "ghost" and self.enabled else None
        dst.blit(ui.rounded(rect.size, 13, (*fill, 255), border, 1), rect.topleft)
        label = ui.surf(self.label, self.style, fg)
        shift = 0
        if self.icon == "play":
            shift = 14
            x = rect.centerx - label.get_width() // 2 - 12
            pygame.draw.polygon(dst, fg, [(x, rect.centery - 9), (x, rect.centery + 9), (x + 15, rect.centery)])
        dst.blit(label, label.get_rect(center=(rect.centerx + shift, rect.centery)))

def draw_arc(dst, color, center, radius, frac, width):
 
    frac = clamp(frac, 0.0, 1.0)
    if frac <= 0.0:
        return
    n = max(2, int(72 * frac))
    pts = [(center[0] + radius * math.cos(-math.pi / 2 + math.tau * frac * i / n),
            center[1] + radius * math.sin(-math.pi / 2 + math.tau * frac * i / n)) for i in range(n + 1)]
    pygame.draw.lines(dst, color, False, pts, width)

def draw_bulb(dst, center, glow, t, idle):
 
    cx, cy = int(center[0]), int(center[1])
    gy = cy - 5    
    bg = (18, 26, 60)
    if glow > 0.02:
        rad = 6 * max(2, round((9 + 24 * glow) / 6))
        add_glow(dst, (cx, gy), rad, fade_color((255, 196, 70), glow * 0.85))
        pulse = 0.75 + 0.25 * math.sin(t * 9.0)
        for i in range(8): 
            a = t * 0.9 + i * math.pi / 4
            r0, r1 = 14, 14 + 5 * glow * (pulse if i % 2 else 1.0)
            pygame.draw.line(dst, mix(bg, (255, 226, 130), glow * 0.9),
                             (cx + math.cos(a) * r0, gy + math.sin(a) * r0),
                             (cx + math.cos(a) * r1, gy + math.sin(a) * r1), 2)
    glass_edge = mix((120, 136, 206), (255, 240, 170), glow)
    glass_fill = mix((24, 32, 72), (255, 212, 88), glow)
    base_col = mix((92, 104, 164), (196, 176, 112), glow)
    neck = [(cx - 7, gy + 7), (cx + 7, gy + 7), (cx + 5, gy + 14), (cx - 5, gy + 14)]
    pygame.draw.polygon(dst, glass_fill, neck)
    pygame.draw.lines(dst, glass_edge, False, [neck[0], neck[3], neck[2], neck[1]], 2)
    aa_circle(dst, glass_edge, (cx, gy), 11)
    aa_circle(dst, glass_fill, (cx, gy), 9)
    for k, w in enumerate((10, 10, 6)): 
        pygame.draw.rect(dst, base_col, (cx - w // 2, gy + 14 + k * 3, w, 2), border_radius=1)
   
    heat = glow if glow > 0.02 else (0.22 * (0.5 + 0.5 * math.sin(t * 3.0)) if idle else 0.0)
    flick = 1.0 if glow < 0.3 else 0.92 + 0.08 * math.sin(t * 23.0)
    fil = mix((112, 124, 170), (255, 252, 226), clamp(heat * flick, 0.0, 1.0))
    wire = [(cx - 3, gy + 8), (cx - 3, gy + 1), (cx - 1.5, gy - 3), (cx, gy + 1), (cx + 1.5, gy - 3),
            (cx + 3, gy + 1), (cx + 3, gy + 8)]
    pygame.draw.lines(dst, fil, False, wire, 2)
    if glow > 0.35: 
        for k in range(3):
            a = t * 5.0 + k * math.tau / 3
            aa_circle(dst, (255, 250, 228), (cx + math.cos(a) * 5.5, gy - 1 + math.sin(a) * 5.5), 1.5)

class BulbButton:
    """Botón de pistas"""

    SIZE = 52

    def __init__(self, pos):
        self.rect = pygame.Rect(pos[0], pos[1], self.SIZE, self.SIZE)
        self.enabled = True
        self.hover = 0.0
        self.pressed = False
        self.glow = 0.0 
        self.lit_for = 0.0 
        self.ready = True
        self.exhausted = False
        self.frac = 1.0  

    def ignite(self):
        self.lit_for = 3.4

    def reset(self):
        self.glow = self.lit_for = 0.0

    def update(self, dt, mouse, clickable, ready, left, exhausted):
        self.enabled, self.ready, self.exhausted = clickable, ready, exhausted
        self.frac = 1.0 - clamp(left / HINT_COOLDOWN, 0.0, 1.0)
        goal = 1.0 if clickable and self.rect.collidepoint(mouse) else 0.0
        self.hover += (goal - self.hover) * min(1.0, dt * 14.0)
        self.lit_for = max(0.0, self.lit_for - dt)
        target = 1.0 if self.lit_for > 0.0 else 0.0
        self.glow += (target - self.glow) * min(1.0, dt * (9.0 if target > self.glow else 2.2))

    def handle(self, e):
        if not self.enabled:
            self.pressed = False
            return False
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rect.collidepoint(e.pos):
            self.pressed = True
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            was, self.pressed = self.pressed, False
            return was and self.rect.collidepoint(e.pos)
        return False

    def draw(self, ui, dst, t):
        cx, cy = self.rect.centerx, self.rect.centery + (2 if self.pressed else 0)
        r = self.rect.w // 2
        lit = self.glow
        fill = mix((20, 28, 64), (74, 54, 14), lit)
        fill = mix(fill, (34, 46, 100), self.hover * 0.6 * (1.0 - lit))
        aa_circle(dst, (0, 0, 0), (cx, cy + 3), r) 
        aa_circle(dst, (62, 78, 150) if not lit else (255, 196, 70), (cx, cy), r)
        aa_circle(dst, fill, (cx, cy), r - 2)
        track = r - 4
        pygame.draw.circle(dst, (44, 56, 112), (cx, cy), track, 2)
        if self.exhausted:
            pygame.draw.circle(dst, (118, 56, 70), (cx, cy), track, 2)
        elif self.ready:
            pulse = 0.5 + 0.5 * math.sin(t * 4.0)
            pygame.draw.circle(dst, mix((150, 110, 40), C_AMBER, pulse), (cx, cy), track, 2)
        else:
            draw_arc(dst, (112, 132, 226), (cx, cy), track, self.frac, 3)
        draw_bulb(dst, (cx, cy), lit, t, idle=self.ready and not self.exhausted)

class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "age", "size", "color", "gravity", "glow")

    def __init__(self, x, y, vx, vy, life, size, color, gravity, glow):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life, self.age, self.size = life, 0.0, size
        self.color, self.gravity, self.glow = color, gravity, glow

def camera_goal(p, bullet=None):
 
    tx = p.side * p.dist
    top = p.height + BOARD_RADIUS + 16.0
    low = p.plateau - 10.0
    ml, mr = (GUN_MARGIN, TARGET_MARGIN) if p.side > 0 else (TARGET_MARGIN, GUN_MARGIN)

    def zoom_for(xs, hi):
        zx = (FW - ml - mr) / max(max(xs) - min(xs), 1.0)
        zy = (GROUND_Y_REF - TOP_MARGIN) / max(hi, 1.0)
        zl = (FH - GROUND_Y_REF - 10.0) / -low if low < 0 else ZOOM_MAX
        return clamp(min(zx, zy, zl, ZOOM_MAX), ZOOM_MIN, ZOOM_MAX)

    def place(xs, z):
        spare = max(0.0, FW - ml - mr - (max(xs) - min(xs)) * z) / 2.0
        return z, min(xs) - (ml + spare) / z

    base_xs = (0.0, tx)
    zb = zoom_for(base_xs, top)
    if bullet is not None:
        xs = (0.0, tx, bullet[0])
        zf = zoom_for(xs, max(top, bullet[1] + 12.0))
        if zf >= 0.5 * zb:
            return place(xs, zf)
        return place(base_xs, 0.5 * zb) 
    return place(base_xs, zb)

class Camera:
 
    def __init__(self):
        self.zoom, self.x0 = ZOOM_REF, 0.0

    def snap(self, goal):
        self.zoom, self.x0 = goal

    def approach(self, goal, dt, rate=5.0):
        k = min(1.0, dt * rate)
        self.zoom *= (goal[0] / self.zoom) ** k
        self.x0 += (goal[1] - self.x0) * k

class Backdrop:
 
    LAYERS = (
        (0.05, 90, 190, (44, 36, 104), (158, 92, 140), True, 11),
        (0.11, 55, 125, (30, 26, 80), (104, 64, 126), True, 23),
        (0.22, 24, 72, (19, 19, 56), (66, 52, 108), False, 37),
    )
    EXTRA = 140

    def __init__(self, size, horizon, seed):
        self.size, self.horizon = size, horizon
        self.tile_w = size[0] + 240
        self.rng = random.Random(seed * 7 + 3)
        self.moon = (int(size[0] * 0.16), int(horizon * 0.20))
        self.sky = self._make_sky(size, horizon)
        self.layers = [self._make_layer(*spec) for spec in self.LAYERS]
        self.stars = self._make_stars(size, horizon, seed)
        self.clouds = self._make_clouds(size, horizon, seed)
        self.twinkle = None 
        self.next_twinkle = None
        self.meteor = None  
        self.next_meteor = None

    def _make_sky(self, size, horizon):
        w, h = size
        sky = vertical_gradient(size, [
            (0.0, (5, 8, 24)), (horizon * 0.50 / h, (20, 18, 62)),
            (horizon * 0.82 / h, (84, 40, 108)), (horizon / h, (240, 120, 98)), (1.0, (240, 120, 98)),
        ])
        mx, my = self.moon
        sky.blit(glow_surface(90, (70, 70, 120)), (mx - 90, my - 90), special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.circle(sky, (232, 236, 255), (mx, my), 30)
        for dx, dy, r in ((-9, -6, 7), (10, 8, 5), (-4, 13, 4)):
            pygame.draw.circle(sky, (208, 214, 240), (mx + dx, my + dy), r)
        return sky.convert()

    def _make_stars(self, size, horizon, seed):
        rng = random.Random(seed)
        w, h = size
        mx, my = self.moon
        stars = []
        for _ in range(int(w * h / 4200)):
            x, y = rng.uniform(0, w), rng.randrange(int(horizon * 0.78))
            if math.hypot(x - mx, y - my) < 48:
                continue 
            b = int(rng.randint(110, 255) * (1 - y / horizon) ** 0.6)
            stars.append((x, y, b, rng.random() < 0.12, rng.uniform(1.5, 4.5)))
        return stars

    def _make_clouds(self, size, horizon, seed):
        rng = random.Random(seed + 77)
        w = size[0]
        clouds = []
        for _ in range(5):
            cw, ch = rng.randint(220, 340), rng.randint(48, 72)
            tint = rng.choice(((150, 92, 170), (120, 90, 190), (196, 112, 150)))
            small = pygame.Surface((cw // 4, ch // 4), pygame.SRCALPHA)
            sw, sh = small.get_size()
            for _ in range(7): 
                ew, eh = rng.randint(sw // 3, int(sw * 0.6)), rng.randint(max(3, sh // 3), max(4, int(sh * 0.7)))
                pygame.draw.ellipse(small, (*tint, rng.randint(26, 46)),
                                    (rng.randint(0, sw - ew), rng.randint(0, sh - eh), ew, eh))
            surf = pygame.transform.smoothscale(small, (cw, ch)).convert_alpha()
            clouds.append((surf, rng.uniform(0, w + cw), rng.uniform(0.18, 0.62) * horizon,
                           rng.uniform(5.0, 11.0), cw))
        return clouds

    def _make_layer(self, factor, h_min, h_max, color, rim, sharp, seed):
        rng = random.Random(seed)
        waves = [(k, rng.uniform(0.4, 1.0) / k ** 0.7, rng.uniform(0, math.tau)) for k in range(2, 12)]
        total = sum(a for _, a, _ in waves)
        surf = pygame.Surface((self.tile_w, h_max + self.EXTRA), pygame.SRCALPHA)
        points = []
        for x in range(self.tile_w + 1):
            raw = sum(a * math.sin(math.tau * k * x / self.tile_w + ph) for k, a, ph in waves) / total
            p = 1.0 - abs(raw) if sharp else 0.5 + 0.5 * raw
            points.append((x, h_max - (h_min + (h_max - h_min) * p)))
        bottom = surf.get_height()
        pygame.draw.polygon(surf, color, points + [(self.tile_w, bottom), (0, bottom)])
        pygame.draw.lines(surf, rim, False, points, 2)
        return factor, surf.convert_alpha(), h_max

    def _schedule(self, t):
 
        if self.next_twinkle is None:
            self.next_twinkle = t + self.rng.uniform(2.5, 5.0)
            self.next_meteor = t + self.rng.uniform(8.0, 18.0)
        if self.twinkle is None and self.stars and t >= self.next_twinkle:
            self.twinkle = (self.rng.randrange(len(self.stars)), t, self.rng.uniform(0.9, 1.5))
        if self.twinkle and t - self.twinkle[1] > self.twinkle[2]:
            self.twinkle = None
            self.next_twinkle = t + self.rng.uniform(3.0, 7.0)
        if self.meteor is None and t >= self.next_meteor:
            w = self.size[0]
            self.meteor = (self.rng.uniform(0.1, 0.7) * w, self.rng.uniform(0.05, 0.35) * self.horizon,
                           self.rng.uniform(380, 520), self.rng.uniform(150, 230), t, 0.8)
        if self.meteor and t - self.meteor[4] > self.meteor[5]:
            self.meteor = None
            self.next_meteor = t + self.rng.uniform(14.0, 28.0)

    def _draw_stars(self, dst, t):
        w = self.size[0]
        for x0, y, b, big, speed in self.stars: 
            x = int((x0 - t * speed) % w)
            dst.set_at((x, y), (b, b, min(255, b + 24)))
            if big:
                pygame.draw.circle(dst, (b, b, 255), (x, y), 1)
        if self.twinkle: 
            i, t0, dur = self.twinkle
            x0, y, b, _big, speed = self.stars[i]
            x = (x0 - t * speed) % w
            k = math.sin(math.pi * clamp((t - t0) / dur, 0.0, 1.0)) ** 1.5
            add_glow(dst, (x, y), 8, fade_color((170, 184, 255), 0.7 * k))
            col = mix((b, b, min(255, b + 24)), (255, 255, 255), k)
            ln = 2 + 5 * k
            pygame.draw.line(dst, col, (x - ln, y), (x + ln, y), 1)
            pygame.draw.line(dst, col, (x, y - ln), (x, y + ln), 1)
            dst.set_at((int(x), int(y)), (255, 255, 255))

    def _draw_clouds(self, dst, t):
        w = self.size[0]
        for surf, x0, y, speed, cw in self.clouds:
            x = (x0 - t * speed) % (w + cw) - cw
            dst.blit(surf, (int(x), int(y)))

    def _draw_meteor(self, dst, t):
        if not self.meteor:
            return
        x0, y0, vx, vy, t0, life = self.meteor
        p = t - t0
        fade = math.sin(math.pi * clamp(p / life, 0.0, 1.0))
        hx, hy = x0 + vx * p, y0 + vy * p
        for k in range(8):
            a, b = k * 0.018, (k + 1) * 0.018
            col = mix((20, 24, 60), mix((255, 255, 255), (80, 90, 170), k / 8), fade)
            pygame.draw.line(dst, col, (hx - vx * a, hy - vy * a), (hx - vx * b, hy - vy * b), max(1, 3 - k // 3))

    def draw(self, dst, cam_x, cam_y, t=0.0):
        dst.blit(self.sky, (0, 0))
        self._schedule(t)
        self._draw_stars(dst, t)
        self._draw_clouds(dst, t)
        self._draw_meteor(dst, t)
        for factor, layer, h_max in self.layers:
            off = int(cam_x * factor) % self.tile_w
            y = int(self.horizon + 2 - h_max + cam_y * factor * 0.5)
            dst.blit(layer, (-off, y))
            dst.blit(layer, (self.tile_w - off, y))

def draw_step_icon(dst, kind, center, color, t):
    """Iconos vectoriales pequeños (≈ 30 px) para las tarjetas del tutorial."""
    cx, cy = int(center[0]), int(center[1])
    if kind == "target":
        for r, w in ((13, 2), (8, 2)):
            pygame.draw.circle(dst, color, (cx, cy), r, w)
        aa_circle(dst, color, (cx, cy), 3)
        for a in (0, 90, 180, 270):
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            pygame.draw.line(dst, color, (cx + ca * 13, cy + sa * 13), (cx + ca * 18, cy + sa * 18), 2)
    elif kind == "angle":
        ox, oy = cx - 12, cy + 10
        pygame.draw.line(dst, color, (ox, oy), (ox + 28, oy), 2)
        a = math.radians(38 + 5 * math.sin(t * 1.6))  
        pygame.draw.line(dst, color, (ox, oy), (ox + math.cos(a) * 26, oy - math.sin(a) * 26), 2)
        pts = [(ox + 13 * math.cos(a * i / 10), oy - 13 * math.sin(a * i / 10)) for i in range(11)]
        pygame.draw.lines(dst, C_AMBER, False, pts, 2)
    elif kind == "newton":
        pygame.draw.line(dst, mix(color, (20, 26, 60), 0.55), (cx - 15, cy + 10), (cx + 15, cy + 10), 1)
        pts = [(cx + x, cy + 10 - 20 * (1 - (x / 14.0) ** 2)) for x in range(-14, 15, 2)]
        pygame.draw.lines(dst, color, False, pts, 2)
        k = (t * 0.5) % 1.0  
        px = cx + 14 - 28 * ease_out_cubic(k)
        aa_circle(dst, C_AMBER, (px, cy + 10 - 20 * (1 - ((px - cx) / 14.0) ** 2)), 3)
    else:  
        draw_bulb(dst, (cx, cy + 3), 0.55 + 0.45 * math.sin(t * 2.2), t, True)

class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_icon(make_icon())
        pygame.display.set_caption(TITLE)
        self.fullscreen = True
        self._open_display()
        pygame.key.start_text_input()
        self.clock = pygame.time.Clock()
        self.running = True
        self.ui = UI()
        self.store = ScoreStore()
        self.rows = self.store.ranking(10)
        self.cursor = pygame.SYSTEM_CURSOR_ARROW
        self.last_phrase = {}
        self.state = MENU
        self.scroll = 0.0
        self.clock_t = 0.0
        self.camera = Camera()
        self.match = Match()
        self._build_assets()
        self._build_widgets()
        self._reset_round_state()

    def _open_display(self):
        if sys.platform == "emscripten":
            self.fullscreen = False
            surface = pygame.display.get_surface()
            if surface is None:
                surface = pygame.display.set_mode((WIDTH, HEIGHT))
            self.display = surface
            self.canvas = surface.get_size()
            self.ox, self.oy = (self.canvas[0] - WIDTH) // 2, (self.canvas[1] - HEIGHT) // 2
            self.screen = surface.subsurface(pygame.Rect(self.ox, self.oy, WIDTH, HEIGHT))
            return

        flags = pygame.SCALED | (pygame.FULLSCREEN if self.fullscreen else pygame.RESIZABLE)
        size = screen_canvas()
        surface = None
        for extra in ({"vsync": 1}, {}):
            try:
                surface = pygame.display.set_mode(size, flags, **extra)
                break
            except pygame.error:
                continue
        if surface is None:
            surface = pygame.display.set_mode(size)
        self.display = surface
        self.canvas = surface.get_size()
        self.ox, self.oy = (self.canvas[0] - WIDTH) // 2, (self.canvas[1] - HEIGHT) // 2
        self.screen = surface.subsurface(pygame.Rect(self.ox, self.oy, WIDTH, HEIGHT))

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self._open_display()
        pygame.key.start_text_input()
        self.cursor = None

    def mouse_pos(self):
        x, y = pygame.mouse.get_pos()
        return x - self.ox, y - self.oy

    def _build_assets(self):
        ui = self.ui
        self.field_surf = pygame.Surface(FIELD.size).convert()
        horizon = GROUND_Y_REF + int(MUZZLE_MOUNT * ZOOM_REF)
        self.field_bd = Backdrop(FIELD.size, horizon, 5)
        self.menu_bd = Backdrop(self.canvas, self.oy + 566, 9)

        cw, ch = self.canvas
        ground = pygame.Surface((cw, 150), pygame.SRCALPHA)
        pts = [(x, 46 + 22 * math.sin(x * 0.011) + 12 * math.sin(x * 0.027 + 1.3)) for x in range(0, cw + 1, 8)]
        pygame.draw.polygon(ground, (8, 11, 28), pts + [(cw, 150), (0, 150)])
        pygame.draw.lines(ground, (70, 56, 120), False, pts, 2)
        self.menu_ground = ground.convert_alpha()

        self.menu_fade = pygame.Surface((cw, ch), pygame.SRCALPHA)
        for x in range(0, self.ox + 900):
            alpha = 205 if x < self.ox else int(205 * (1 - (x - self.ox) / 900) ** 1.2)
            pygame.draw.line(self.menu_fade, (5, 8, 22, alpha), (x, 0), (x, ch))
        self.menu_fade = self.menu_fade.convert_alpha()
        self.dim = pygame.Surface((cw, ch), pygame.SRCALPHA)
        self.dim.fill((5, 8, 22, 150))

        self.reticle = pygame.Surface((480, 480), pygame.SRCALPHA)
        for r, a in ((230, 34), (170, 26), (110, 26)):
            pygame.draw.circle(self.reticle, (*C_ACCENT, a), (240, 240), r, 2)
        for ang in range(0, 360, 15):
            c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
            ln = 14 if ang % 45 == 0 else 7
            pygame.draw.line(self.reticle, (*C_ACCENT, 40), (240 + c * 230, 240 + s * 230), (240 + c * (230 - ln), 240 + s * (230 - ln)), 2)
        pygame.draw.line(self.reticle, (*C_ACCENT, 30), (0, 240), (480, 240), 1)
        pygame.draw.line(self.reticle, (*C_ACCENT, 30), (240, 0), (240, 480), 1)
        self.reticle = self.reticle.convert_alpha()

        style = ui.fit_style("CALCULATION", UI.SANS, 560, 84)
        grad = vertical_gradient((560, ui.styles[style][0].get_height()), [(0, C_ACCENT), (1, C_VIOLET)])
        self.title_a = ui.surf("ARTILLERY", style, C_TEXT)
        self.title_b = ui.surf("CALCULATION", style, (255, 255, 255)).copy()
        self.title_b.blit(grad, (0, 0), special_flags=pygame.BLEND_RGB_MULT)

        self.corners = []
        r, ss = 18, 4
        for cx, cy in ((r, r), (0, r), (r, 0), (0, 0)):
            patch = pygame.Surface((r * ss, r * ss), pygame.SRCALPHA)
            patch.fill((*C_BG, 255))
            pygame.draw.circle(patch, (*C_BG, 0), (cx * ss, cy * ss), r * ss)
            self.corners.append(pygame.transform.smoothscale(patch, (r, r)).convert_alpha())

        self.formula = self._build_formula("h1", "h2")

    def _build_formula(self, main, frac):
        ui = self.ui
        left = ui.surf("X_{n+1} = X_{n} -", main, C_TEXT)
        num = ui.surf("f(X_{n})", frac, C_ACCENT)
        den = ui.surf("f'(X_{n})", frac, C_ACCENT)
        fw = max(num.get_width(), den.get_width()) + 12
        h = max(num.get_height() + den.get_height() + 6, left.get_height())
        surf = pygame.Surface((left.get_width() + 12 + fw, h), pygame.SRCALPHA)
        mid, fx = h // 2, left.get_width() + 12
        surf.blit(left, (0, mid - left.get_height() // 2))
        surf.blit(num, (fx + (fw - num.get_width()) // 2, 0))
        pygame.draw.line(surf, C_ACCENT, (fx, mid), (fx + fw, mid), 2)
        surf.blit(den, (fx + (fw - den.get_width()) // 2, h - den.get_height()))
        return surf

    def _build_widgets(self):
        a = ANSWER_RECT
        self.menu_input = TextInput((64, 424, 340, 52), "Ingrese su nombre", NAME_MAX, False)
        self.menu_input.focused = True
        self.play_btn = Button((64, 516, 340, 60), "Jugar", "primary", icon="play")
        self.angle_input = TextInput((a.x + 16, a.y + 40, 226, 48), "0.00", 7, True, sticky=True, suffix="°")
        self.fire_btn = Button((a.x + 254, a.y + 40, 126, 48), "Disparar", "fire")
        self.bulb = BulbButton((a.x + 14, a.y + 98))
        self.new_btn = Button((a.x + 212, a.y + 106, 168, 38), "Nueva Ecuación", "ghost", style="btn_s")
        self.next_btn = Button((0, 0, 340, 56), "Nueva Ecuación", "primary")
        self.result_input = TextInput((RES_SAVE.x + 24, RES_SAVE.y + 48, 330, 50), "Su nombre", NAME_MAX, False)
        self.save_btn = Button((RES_SAVE.x + 372, RES_SAVE.y + 48, 200, 50), "Guardar", "good")
        self.again_btn = Button((64, 624, 250, 56), "Jugar de Nuevo", "primary")
        self.menu_btn = Button((330, 624, 250, 56), "Menú", "ghost")

    def _reset_round_state(self):
        self.problem = None
        self.shot = None
        self.pending = None
        self.phase = AIM
        self.hints = 0
        self.hint_list = []
        self.hint_ready_at = 0.0  
        self.cells_prev, self.flash_t0 = frozenset(), -9.0
        self.time_left, self.freeze_t = TIME_MAX, 0.0
        self.time_flash, self.time_out = None, False
        self.double_next, self.free_hints = False, 0
        self.balloons, self.pops, self.mini_toast, self.balloon_at = [], [], None, -9
        self.pop_fx, self.balloon_idx = [], 0
        self.chip_rects = {}
        self.last_story = None
        self.last_tip = None
        self.tip_fail = -1  
        self.fails = 0 
        self.solved = False
        self.drawer_open, self.drawer_t = False, 0.0
        self.message = None
        self.barrel_deg = self.aim_deg = 10.0
        self.recoil = self.flash = self.shake = self.hold = self.settle = self.auto_t = 0.0
        self.fire_cooldown = 0.0
        self.particles, self.rings, self.floaters, self.hit_marks = [], [], [], []
        self.toast = None  
        self.save_note = None
        self.saved_name = None
        self.round_index = 0
        self.camera = Camera()

    def start_match(self):
        self.match = Match()
        self.round_index = 0
        self.saved_name = self.save_note = None
        self.hint_ready_at = 0.0
        self.bulb.reset()
        self.time_left, self.freeze_t, self.time_flash, self.time_out = TIME_MAX, 0.0, None, False
        self.double_next = False
        self.fire_cooldown = 0.0
        self.state = PLAY
        self.new_round()
        self.camera.snap(camera_goal(self.problem))

    def new_round(self):
        """Genera una ecuación nueva (reinicia pistas e intentos fallidos)."""
        self.problem = make_problem(self.round_index, avoid=self.last_story)
        self.last_story = self.problem.title
        self.hint_list = build_hints(self.problem)
        self.hints = 0
        self.hint_ready_at = 0.0
        self.bulb.reset()
        self.cells_prev, self.flash_t0 = frozenset(), -9.0
        self.free_hints = 0
        self.balloons, self.pops, self.mini_toast, self.balloon_at = [], [], None, -9
        self.pop_fx, self.balloon_idx = [], 0
        self.fails = 0
        self.tip_fail, self.last_tip = -1, None
        self.solved = False
        self.drawer_open, self.drawer_t = False, 0.0
        self.barrel_deg = self.aim_deg = 10.0 if self.problem.side > 0 else 170.0
        self.angle_input.set_text("")
        self.particles, self.rings, self.floaters, self.hit_marks = [], [], [], []
        self.toast = None
        self.begin_attempt()

    def begin_attempt(self):
        """Prepara un nuevo disparo SIN tocar la ecuación, las pistas ni el ángulo escrito."""
        self.shot = self.pending = None
        self.phase = AIM
        self.message = None
        self.hold = self.settle = 0.0
        self.angle_input.focused = True

    def new_equation(self):
        """Cambia el reto: botón «Nueva Ecuación» o reinicio automático tras dar al blanco."""
        if self.phase not in (AIM, SOLVED):
            return
        if self.round_index + 1 >= ROUNDS_PER_MATCH:
            self.end_match()
        else:
            self.round_index += 1
            self.new_round()

    def end_match(self, time_out=False):
        """Lleva a la tabla de resultados (al terminar las ecuaciones o al agotarse el tiempo)."""
        self.state = RESULT
        self.time_out = time_out
        self.result_input.set_text(self.menu_input.text)
        self.result_input.focused = True
        self.saved_name = self.save_note = None
        self.balloons, self.toast = [], None

    def go_menu(self):
        self.rows = self.store.ranking(10)
        self.state = MENU
        self.menu_input.focused = True

    def say(self, text, color):
        self.message = (text, color)

    def hint_left(self):
        return max(0.0, self.hint_ready_at - time.monotonic())

    def hint_ready(self):
        return self.phase == AIM and self.hints < MAX_HINTS and self.hint_left() <= 0.0

    def use_hint(self):
        if self.phase != AIM:
            return
        if self.hint_ready():
            self.cells_prev = cells_revealed(self.hints, self.problem.ans_row)
            self.flash_t0 = self.clock_t
            self.hints += 1
            self.match.hints += 1
            self.hint_ready_at = time.monotonic() + HINT_COOLDOWN
            self.drawer_open = True
            self.message = None
            self.bulb.ignite()
        elif self.hints > 0:
            self.drawer_open = not self.drawer_open

    def multiplier(self):
        paid = max(0, self.hints - self.free_hints)
        return max(MIN_MULTIPLIER, 1.0 - HINT_PENALTY * paid - ATTEMPT_PENALTY * self.fails)

    def fire(self):
        if self.phase != AIM or self.fire_cooldown > 0.0:
            return
        value = parse_angle(self.angle_input.text)
        if value is None:
            self.say("Escribe un número", C_BAD)
            return
        if not 0.0 < value <= MAX_ANGLE:
            self.say(f"Usa un ángulo entre 1° y {MAX_ANGLE:.0f}°", C_BAD)
            return
        self.pending = {"angle": value}
        self.balloon_idx = 0
        self.balloons_popped_this_shot = False
        self.shot_speed_multiplier = 1.0
        self.shot = Shot(value, self.problem)
        self.fire_cooldown = FIRE_COOLDOWN_SECONDS
        self.phase = FLIGHT
        self.message = None
        self.aim_deg = self.barrel_deg = value
        self.recoil, self.flash, self.shake = 1.0, 0.14, 3.0
        a = math.radians(value)
        tip = (math.cos(a) * BARREL_PX / self.camera.zoom, math.sin(a) * BARREL_PX / self.camera.zoom)
        self.burst(*tip, 14, (3, 14), (0.5, 1.1), (3, 7), [(170, 180, 222), (132, 144, 196)], gravity=-8)

    def finish_shot(self):
        shot, res, p, m = self.shot, self.pending, self.problem, self.match
        cat = judge(shot, abs(res["angle"] - p.root_deg))
        hit = cat in ("diana", "acierto")
        mult = self.multiplier()
        points = round(POINTS[cat] * mult)
        if hit and self.double_next:
            points *= 2
            self.double_next = False
            res["doubled"] = True
        res.update(cat=cat, mult=mult, points=points, hints=self.hints,
                   dist=shot.best, attempt=self.fails + 1)
        x, y = shot.impact
        m.shots += 1
        m.points += points
        if cat == "diana":
            m.bulls += 1
        elif cat == "acierto":
            m.touches += 1
        elif cat == "cerca":
            m.near += 1
        else:
            m.far += 1
        self.solved = hit
        if not hit:
            self.fails += 1
            res["tip"] = self.maybe_tip(res)
            if (cat == "lejos" or PENALIZE_NEAR_MISS) and not self.balloons_popped_this_shot:
                self.time_penalty()
            self.maybe_spawn_balloons()
        color = CAT_COLOR[cat]
        if hit:
            self.hit_marks.append((x, y))
            palette = [color, (255, 255, 255), C_AMBER] if cat == "diana" else [color, (255, 240, 220)]
            self.burst(x, y, 46 if cat == "diana" else 30, (18, 72), (0.5, 1.2), (2, 4.5), palette, gravity=38, glow=True)
            self.rings.append([x, y, 0.0, 0.7, color, 56])
            self.shake = 9.0 if cat == "diana" else 6.0
        else:
            self.burst(x, y, 26, (8, 40), (0.5, 1.1), (2, 5), [(150, 140, 196), (112, 102, 160)], gravity=26, spread=(20, 160))
            self.rings.append([x, y, 0.0, 0.5, (150, 140, 196), 32])
            self.shake = 5.0
        label = (f"+{points}" if points else "0") + (" ×2" if res.get("doubled") else "")
        self.floaters.append({"x": x, "y": y + 6, "text": label, "color": color, "age": 0.0, "life": 1.3})
        self.toast = {"card": self.build_feedback(), "age": 0.0,
                      "life": TOAST_TIP_SECONDS if res.get("tip") else TOAST_SECONDS}
        self.phase = SETTLE
        self.settle = 0.8 if hit else 0.6
        self.hold = 1.3

    def time_penalty(self):
        """Cada desacierto resta tiempo: 10 s, y +5 s por cada fallo seguido (se reinicia con cada ecuación)."""
        if self.freeze_t > 0.0:
            return
        pen = min(TIME_PENALTY_MAX, TIME_PENALTY_BASE + TIME_PENALTY_STEP * (self.fails - 1))
        self.time_left -= pen
        self.time_flash = {"text": f"-{pen:.0f} s", "age": 0.0}

    def maybe_spawn_balloons(self):
        """Tras 3 o más fallos seguidos pueden aparecer globos con ayudas, TODOS del mismo tamaño y en
        posiciones aleatorias. Viven en coordenadas del mundo: la bala los revienta al atravesarlos."""
        if self.fails < BALLOON_MIN_FAILS or self.fails - self.balloon_at < 2 or self.balloons:
            return
        if random.random() >= min(0.8, 0.5 + 0.1 * (self.fails - BALLOON_MIN_FAILS)):
            return
        p = self.problem
        z, x0 = camera_goal(p)
        tsx, tsy = (p.side * p.dist - x0) * z, GROUND_Y_REF - p.height * z
        gsx = -x0 * z
        placed = []
        for kind, color in random.sample(BALLOON_KINDS, random.choice((1, 2, 2, 3))):
            for _ in range(120):
                sx, sy = random.uniform(80, FW - 80), random.uniform(140, 400)
                wx, wy = sx / z + x0, (GROUND_Y_REF - sy) / z
                ground_sy = GROUND_Y_REF - terrain_height(wx, p.plateau, p.dist, p.side) * z
                if sy > ground_sy - BALLOON_R - 40:
                    continue
                if math.hypot(sx - tsx, sy - tsy) < 80 or (abs(sx - tsx) < 45 and sy > tsy):
                    continue
                if math.hypot(sx - gsx, sy - GROUND_Y_REF) < 100:
                    continue
                if any(math.hypot(sx - qx, sy - qy) < 2 * BALLOON_R + 24 for qx, qy in placed):
                    continue
                placed.append((sx, sy))
                self.balloons.append({"kind": kind, "color": color, "wx": wx, "wy": wy,
                                      "ph": random.uniform(0, math.tau), "age": 0.0, "life": BALLOON_LIFE})
                break
        if self.balloons:
            self.balloon_at = self.fails
            self.mini_toast = {"age": 0.0, "life": 3.2}

    def check_balloon_hits(self):
        """Revienta todo globo que la bala atraviese. Se revisa el TRAMO recorrido desde el último
        cuadro (no solo la punta), así ninguno se escapa aunque la bala vaya rápida."""
        shot = self.shot
        if not shot:
            return
        path = shot.path
        pts = path[max(0, self.balloon_idx - 1):]
        if shot.pos != pts[-1]:
            pts = pts + [shot.pos]
        self.balloon_idx = len(path)
        if not self.balloons or len(pts) < 2:
            return
        reach = BALLOON_R / self.camera.zoom + BULLET_R
        for b in list(self.balloons):
            c = (b["wx"], b["wy"])
            if any(seg_point_dist(u, v, c) <= reach for u, v in zip(pts, pts[1:])):
                self.balloons.remove(b)
                self.balloons_popped_this_shot = True
                self.apply_balloon(b)

    def apply_balloon(self, b):
        kind, color = b["kind"], b["color"]
        if kind == "doble":
            self.double_next, text = True, "×2 PUNTOS"
        elif kind == "congelar":
            self.freeze_t, text = min(60.0, self.freeze_t + FREEZE_SECONDS), "TIEMPO CONGELADO"
        elif kind == "pista" and self.hints < MAX_HINTS:
            self.cells_prev = cells_revealed(self.hints, self.problem.ans_row)
            self.flash_t0 = self.clock_t
            self.hints += 1
            self.free_hints += 1
            self.drawer_open = True
            self.bulb.ignite()
            text = "¡PISTA GRATIS!"
        else:
            self.time_left, text = min(TIME_MAX, self.time_left + BALLOON_TIME_BONUS), f"+{BALLOON_TIME_BONUS:.0f} s"
        wx, wy, z = b["wx"], b["wy"], self.camera.zoom
        self.pops.append({"x": wx, "y": wy, "text": text, "color": color, "age": 0.0, "life": 1.5})
        self.pop_fx.append({"x": wx, "y": wy, "color": color, "age": 0.0, "life": 0.5})
        self.rings.append([wx, wy, 0.0, 0.55, color, 62])
        self.rings.append([wx, wy, 0.0, 0.32, (255, 255, 255), 36])
        self.burst(wx, wy, 30, (28 / z, 100 / z), (0.5, 1.1), (2.5, 5.5),
                   [color, mix(color, (255, 255, 255), 0.55), (255, 255, 255)], gravity=34.0 / z, glow=True)
        self.shake = max(self.shake, 3.0)

    def update_balloons(self, dt):
        for b in self.balloons:
            b["age"] += dt
        self.balloons = [b for b in self.balloons if b["age"] < b["life"]]
        for q in self.pops:
            q["age"] += dt
        self.pops = [q for q in self.pops if q["age"] < q["life"]]
        for fx in self.pop_fx:
            fx["age"] += dt
        self.pop_fx = [fx for fx in self.pop_fx if fx["age"] < fx["life"]]
        if self.mini_toast:
            self.mini_toast["age"] += dt
            if self.mini_toast["age"] >= self.mini_toast["life"]:
                self.mini_toast = None

    def maybe_tip(self, res):
        """Tras varios fallos, de vez en cuando muestra un consejo táctico (poco si ya no quedan pistas)."""
        if self.fails < TIP_MIN_FAILS or self.tip_fail == self.fails - 1:
            return None
        exhausted = self.hints >= MAX_HINTS
        more = min(self.fails - TIP_MIN_FAILS, 3)
        prob = TIP_PROB_EXHAUSTED + 0.01 * more if exhausted else TIP_PROB + 0.05 * more
        if random.random() >= prob:
            return None
        p = self.problem
        pool = list(TIPS_GENERAL)
        if not exhausted:
            pool += TIPS_HINT
        if p.side < 0:
            pool += TIPS_LEFT
        if p.arc == "alto":
            pool += TIPS_HIGH
        if p.arc == "bajo":
            pool += TIPS_KIND[p.kind]
        options = [t for t in pool if t != self.last_tip] or pool
        tip = self.last_tip = random.choice(options)
        self.tip_fail = self.fails
        return tip

    def finish_match_save(self):
        if self.saved_name:
            return
        name = clean_name(self.result_input.text)
        if not name:
            self.save_note = ("Escribe un nombre para guardar", C_BAD)
            return
        m = self.match
        status = self.store.save_match(name, m.points, m.hits, m.shots)
        if status == "ok":
            self.saved_name = name
            self.save_note = (f"Puntuación de «{name}» guardada en save_prof", C_GOOD)
            self.menu_input.set_text(name)
            self.rows = self.store.ranking(10)
        elif status == "exists":
            self.save_note = (f"«{name}» ya está registrado: escribe un nombre nuevo", C_BAD)
            self.result_input.set_text("")
            self.result_input.focused = True
        else:
            self.save_note = ("No se pudo escribir en la carpeta save_prof", C_BAD)

    def burst(self, x, y, n, speed, life, size, colors, gravity=30.0, glow=False, spread=(0, 360)):
        for _ in range(n):
            a = math.radians(random.uniform(*spread))
            v = random.uniform(*speed)
            self.particles.append(Particle(x, y, math.cos(a) * v, math.sin(a) * v,
                                           random.uniform(*life), random.uniform(*size),
                                           random.choice(colors), gravity, glow))

    def view(self, x, y):
        return (x - self.camera.x0) * self.camera.zoom, GROUND_Y_REF - y * self.camera.zoom

    def handle_event(self, e):
        if e.type == pygame.QUIT or e.type == getattr(pygame, "WINDOWCLOSE", -1):
            self.running = False
            return
        if hasattr(e, "pos"):
            e = pygame.event.Event(e.type, {**e.dict, "pos": (e.pos[0] - self.ox, e.pos[1] - self.oy)})
        if e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
            self.toggle_fullscreen()
            return
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            if self.state == MENU:
                self.running = False
            else:
                self.go_menu()
            return
        {MENU: self.event_menu, PLAY: self.event_play, RESULT: self.event_result}[self.state](e)

    @staticmethod
    def _is_enter(e):
        return e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_KP_ENTER)

    def event_menu(self, e):
        self.menu_input.handle(e)
        if self.play_btn.handle(e) or self._is_enter(e):
            self.start_match()

    def event_play(self, e):
        if (self.phase == FLIGHT and e.type == pygame.MOUSEBUTTONDOWN and e.button == 1):
            self.shot_speed_multiplier = SHOT_CLICK_SPEED
        elif self.phase == AIM:
            before = self.angle_input.text
            self.angle_input.handle(e)
            if self.angle_input.text != before:
                self.message = None
            if (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.drawer_t > 0.9
                    and DRAWER_CLOSE.collidepoint(e.pos)):
                self.drawer_open = False
            fire = self.fire_btn.handle(e)
            hint = self.bulb.handle(e)
            new = self.new_btn.handle(e)
            if fire or self._is_enter(e):
                self.fire()
            elif hint or (e.type == pygame.KEYDOWN and e.key == pygame.K_TAB):
                self.use_hint()
            elif new:
                self.new_equation()
        elif self.phase == SOLVED:
            nxt = self.next_btn.handle(e)
            new = self.new_btn.handle(e)
            if nxt or new or self._is_enter(e):
                self.new_equation()

    def event_result(self, e):
        if not self.saved_name:
            self.result_input.handle(e)
            if self.save_btn.handle(e) or self._is_enter(e):
                self.finish_match_save()
        if self.again_btn.handle(e):
            self.start_match()
        if self.menu_btn.handle(e):
            self.go_menu()

    def update(self, dt, real=None):
        self.clock_t += dt
        self.scroll += dt * 16
        mouse = self.mouse_pos()
        if self.state == MENU:
            self.menu_input.update(dt)
            self.play_btn.update(dt, mouse)
        elif self.state == PLAY:
            self.update_play(dt, mouse, dt if real is None else real)
        else:
            self.result_input.update(dt)
            self.save_btn.enabled = not self.saved_name
            self.save_btn.label = "Guardado" if self.saved_name else "Guardar"
            for b in (self.save_btn, self.again_btn, self.menu_btn):
                b.update(dt, mouse)
        self.update_cursor(mouse)

    def update_play(self, dt, mouse, real):
        self.fire_cooldown = max(0.0, self.fire_cooldown - real)
        if self.freeze_t > 0.0:
            self.freeze_t = max(0.0, self.freeze_t - real)
        else:
            self.time_left -= real
        if self.time_flash:
            self.time_flash["age"] += dt
            if self.time_flash["age"] > TIME_FLASH_SECONDS:
                self.time_flash = None
        self.update_balloons(dt)
        if self.time_left <= 0.0: 
            self.time_left = 0.0
            self.end_match(time_out=True)
            return
        self.angle_input.update(dt)
        aim = self.phase == AIM
        self.fire_btn.enabled = aim and self.fire_cooldown <= 0.0
        self.fire_btn.label = (f"Espera {math.ceil(self.fire_cooldown)}s"
                               if self.fire_cooldown > 0.0 else "Disparar")
        self.new_btn.enabled = aim or self.phase == SOLVED
        self.next_btn.enabled = self.phase == SOLVED
        for b in (self.fire_btn, self.new_btn, self.next_btn):
            b.update(dt, mouse)
        self.bulb.update(dt, mouse, aim and (self.hint_ready() or self.hints > 0), self.hint_ready(),
                         self.hint_left(), self.hints >= MAX_HINTS)
        goal = 1.0 if (self.drawer_open and aim and self.hints) else 0.0
        self.drawer_t += (goal - self.drawer_t) * min(1.0, dt * 10.0)

        if self.phase == AIM:
            value = parse_angle(self.angle_input.text)
            if value is not None and 0.0 < value <= MAX_ANGLE:
                self.aim_deg = value 
        self.barrel_deg += (self.aim_deg - self.barrel_deg) * min(1.0, dt * 12.0)
        self.recoil = max(0.0, self.recoil - dt * 3.0)
        self.flash = max(0.0, self.flash - dt)
        self.shake = max(0.0, self.shake - dt * 30.0)

        if self.phase == FLIGHT:
            self.shot.advance(dt * self.shot_speed_multiplier)
            self.check_balloon_hits()
            if self.shot.done:
                self.finish_shot()
        elif self.hold > 0:
            self.hold -= dt
        bullet = None
        if self.shot and (self.phase == FLIGHT or self.hold > 0):
            bullet = self.shot.pos if self.phase == FLIGHT else self.shot.impact
        self.camera.approach(camera_goal(self.problem, bullet), dt, 6.0 if bullet else 4.0)
        if self.phase != FLIGHT:
            if self.phase == SETTLE:
                self.settle -= dt
                if self.settle <= 0:
                    if self.solved: 
                        self.phase, self.auto_t = SOLVED, AUTO_NEXT_SECONDS
                    else:
                        self.begin_attempt()
            elif self.phase == SOLVED:
                self.auto_t -= dt
                if self.auto_t <= 0:
                    self.new_equation()
        if self.toast:
            self.toast["age"] += dt
            if self.toast["age"] >= self.toast["life"]:
                self.toast = None

        self.update_effects(dt)

    def update_effects(self, dt):
        alive = []
        for p in self.particles:
            p.age += dt
            if p.age < p.life:
                p.vy -= p.gravity * dt
                p.x += p.vx * dt
                p.y += p.vy * dt
                alive.append(p)
        self.particles = alive
        for r in self.rings:
            r[2] += dt
        self.rings = [r for r in self.rings if r[2] < r[3]]
        for f in self.floaters:
            f["age"] += dt
        self.floaters = [f for f in self.floaters if f["age"] < f["life"]]

    def active_buttons(self):
        if self.state == MENU:
            return [self.play_btn]
        if self.state == RESULT:
            return [self.save_btn, self.again_btn, self.menu_btn]
        if self.phase == SOLVED:
            return [self.next_btn, self.new_btn]
        return [self.fire_btn, self.bulb, self.new_btn]

    def active_input(self):
        return {MENU: self.menu_input, PLAY: self.angle_input, RESULT: self.result_input}[self.state]

    def update_cursor(self, mouse):
        cursor = pygame.SYSTEM_CURSOR_ARROW
        if any(b.enabled and b.rect.collidepoint(mouse) for b in self.active_buttons()):
            cursor = pygame.SYSTEM_CURSOR_HAND
        elif self.active_input().rect.collidepoint(mouse):
            cursor = pygame.SYSTEM_CURSOR_IBEAM
        if cursor != self.cursor:
            try:
                pygame.mouse.set_cursor(cursor)
            except pygame.error:
                pass
            self.cursor = cursor

    def draw_play(self):
        s = self.screen
        self.display.fill(C_BG)
        self.draw_top_bar(s)
        self.draw_field()
        s.set_clip(FIELD)
        off = (random.uniform(-1, 1) * self.shake, random.uniform(-1, 1) * self.shake) if self.shake > 0.2 else (0, 0)
        s.blit(self.field_surf, (FIELD.x + off[0], FIELD.y + off[1]))
        s.set_clip(None)
        for patch, (x, y) in zip(self.corners, ((FIELD.left, FIELD.top), (FIELD.right - 18, FIELD.top),
                                                (FIELD.left, FIELD.bottom - 18), (FIELD.right - 18, FIELD.bottom - 18))):
            s.blit(patch, (x, y))
        pygame.draw.rect(s, (58, 72, 140), FIELD, 2, border_radius=18)
        s.set_clip(FIELD)
        self.draw_hint_drawer(s)
        s.set_clip(None)
        self.draw_problem_card(s)
        self.draw_answer_card(s)
        self.draw_method_card(s)
        self.draw_status(s)
        self.draw_toast(s)
        self.draw_next_button(s)
        self.draw_time_flash(s)

    def chip(self, dst, right, y, label, value, color):
        ui = self.ui
        w = max(ui.measure(label, "label"), ui.measure(value, "h2")) + 30
        rect = pygame.Rect(right - w, y, w, 46)
        self.chip_rects[label] = rect
        dst.blit(ui.rounded(rect.size, 12, (16, 22, 52, 255), (62, 76, 148), 1), rect.topleft)
        ui.text(dst, label, "label", C_MUTED, (rect.centerx, rect.y + 7), "midtop")
        ui.text(dst, value, "h2", color, (rect.centerx, rect.y + 22), "midtop")
        return rect.x - 8

    def draw_top_bar(self, s):
        ui = self.ui
        draw_logo(s, (42, 38), 17)
        r = ui.text(s, "ARTILLERY", "title", C_TEXT, (72, 20))
        ui.text(s, "CALCULATION", "title", C_ACCENT, (r.right + 10, 20))
        m = self.match
        items = [
            ("ARTILLERO", clean_name(self.menu_input.text) or "Invitado", C_TEXT),
            ("ECUACIÓN", f"{min(self.round_index + 1, ROUNDS_PER_MATCH)}/{ROUNDS_PER_MATCH}", C_ACCENT),
            ("TIEMPO", fmt_time(self.time_left), C_ACCENT if self.freeze_t > 0 else C_BAD if self.time_left < 30 else
             C_AMBER if self.time_left < 120 else C_TEXT),
            ("PUNTOS", str(m.points), C_AMBER),
            ("ACIERTOS · ERRORES", f"{m.hits} · {m.errors}", C_GOOD),
        ]
        x = WIDTH - 16
        for label, value, color in reversed(items):
            x = self.chip(s, x, 14, label, value, color)

    def draw_time_flash(self, s):
        """Descuento de tiempo («-10 s»). Se dibuja AL FINAL para quedar ENCIMA de la tarjeta de la misión."""
        f = self.time_flash
        rect = self.chip_rects.get("TIEMPO")
        if not f or rect is None:
            return
        ui, age = self.ui, f["age"]
        k = min(clamp(age / 0.12, 0.0, 1.0), clamp((TIME_FLASH_SECONDS - age) / 0.5, 0.0, 1.0))
        head = ui.surf("DESCUENTO POR FALLO", "label", (255, 170, 180))
        amount = ui.surf(f["text"], "stat", C_BAD)
        w = max(head.get_width(), amount.get_width()) + 40
        h = head.get_height() + amount.get_height() + 22
        card = ui.rounded((w, h), 14, (46, 8, 18, 248), (*C_BAD, 235), 2).copy()
        card.blit(head, head.get_rect(midtop=(w // 2, 8)))
        card.blit(amount, amount.get_rect(midtop=(w // 2, 8 + head.get_height() + 2)))
        if age < 0.25:
            sc = 0.7 + 0.3 * ease_out_back(age / 0.25)
            card = pygame.transform.smoothscale(card, (max(1, int(w * sc)), max(1, int(h * sc))))
        card.set_alpha(int(255 * k))
        s.blit(card, card.get_rect(midtop=(rect.centerx, rect.bottom + 8 + 10 * ease_out_cubic(age / TIME_FLASH_SECONDS))))

    def draw_field(self):
        surf = self.field_surf
        cam = self.camera
        self.field_bd.draw(surf, cam.x0 * cam.zoom, 0, self.clock_t)
        self.draw_terrain(surf)
        self.draw_markers(surf)
        self.draw_target(surf)
        self.draw_shot(surf)
        self.draw_gun(surf)
        self.draw_effects(surf)
        self.draw_balloons(surf)

    def draw_terrain(self, surf):
        p = self.problem
        step = 8
        pts = []
        for px in range(-step, FW + 2 * step, step):
            wx = px / self.camera.zoom + self.camera.x0
            pts.append((px, self.view(0, terrain_height(wx, p.plateau, p.dist, p.side))[1]))
        bottom = [(FW + 2 * step, FH + 40), (-step, FH + 40)]
        pygame.draw.polygon(surf, (38, 46, 98), pts + bottom)
        pygame.draw.polygon(surf, (22, 26, 62), [(x, y + 26) for x, y in pts] + bottom)
        pygame.draw.polygon(surf, (14, 17, 44), [(x, y + 80) for x, y in pts] + bottom)
        pygame.draw.lines(surf, (128, 142, 220), False, pts, 3)

    def draw_markers(self, surf):
        p = self.problem
        gap = next(g for g in (100, 200, 250, 500, 1000) if g * self.camera.zoom >= 64)
        for m in range(gap, int(p.dist) - 40, gap):
            wx = p.side * m
            sx, sy = self.view(wx, terrain_height(wx, p.plateau, p.dist, p.side))
            if -30 < sx < FW + 30:
                pygame.draw.line(surf, (126, 142, 220), (sx, sy), (sx, sy - 16), 2)
                tip = sx + 10 * p.side
                pygame.draw.polygon(surf, C_ACCENT, [(sx, sy - 16), (tip, sy - 12), (sx, sy - 8)])
                self.ui.text(surf, f"{m} m", "tiny", C_MUTED, (sx, sy + 12), "midtop")
        sx, sy = self.view(p.side * p.dist, p.plateau)
        if -60 < sx < FW + 60:
            self.ui.text(surf, f"{p.tname} · {p.dist:.0f} m", "small_b", C_AMBER, (sx, sy + 14), "midtop")

    def draw_target(self, surf):
        p = self.problem
        cx, cy = self.view(p.side * p.dist, p.height)
        gx, gy = self.view(p.side * p.dist, p.plateau)
        if not -80 < cx < FW + 80:
            return
        pygame.draw.line(surf, (104, 118, 190), (cx, cy), (cx, gy), 4)
        pygame.draw.rect(surf, (84, 98, 170), (cx - 18, gy - 5, 36, 8), border_radius=3)
        add_glow(surf, (cx, cy), 50, (30, 90, 150))
        r = max(BOARD_RADIUS * self.camera.zoom, 9.0)
        for frac, color in ((1.0, (240, 244, 255)), (0.84, (30, 38, 84)), (0.66, C_AMBER),
                            (BULLSEYE_RADIUS / BOARD_RADIUS, C_BAD), (0.13, (255, 240, 240))):
            aa_circle(surf, color, (cx, cy), r * frac)
        if self.phase == AIM:
            k = (self.clock_t % 1.8) / 1.8
            pygame.draw.circle(surf, mix(C_ACCENT, (14, 18, 46), k), (cx, cy), int(r + 6 + k * 26), 2)
        for hx, hy in self.hit_marks:
            sx, sy = self.view(hx, hy)
            aa_circle(surf, (255, 246, 220), (sx, sy), 4)
            aa_circle(surf, (20, 22, 44), (sx, sy), 2.5)

    def draw_shot(self, surf):
        shot = self.shot
        if not shot:
            return
        path = shot.path
        for i in range(0, len(path), 4):
            sx, sy = self.view(*path[i])
            if -10 < sx < FW + 10 and -10 < sy < FH + 10:
                pygame.draw.circle(surf, (120, 138, 226), (int(sx), int(sy)), 2)
        pts = [self.view(*p) for p in path[-16:]]
        for i in range(1, len(pts)):
            k = i / len(pts)
            pygame.draw.line(surf, mix((60, 70, 140), (255, 226, 150), k), pts[i - 1], pts[i], 1 + int(3 * k))
        if not shot.done:
            head = self.view(*shot.pos)
            add_glow(surf, head, 16, (255, 190, 90))
            aa_circle(surf, (255, 246, 214), head, 3.5)

    def draw_gun(self, surf):
        px, py = self.view(0, 0)
        gy = self.view(0, -MUZZLE_MOUNT)[1]
        if not -120 < px < FW + 120:
            return
        body = [(px - 46, gy + 6), (px - 30, py + 8), (px + 26, py + 8), (px + 38, gy + 6)]
        pygame.draw.polygon(surf, (40, 50, 100), body)
        pygame.draw.lines(surf, (104, 122, 200), False, body[:3] + [body[3]], 2)
        pygame.draw.rect(surf, (28, 34, 76), (px - 22, gy - 8, 34, 14), border_radius=3)
        ang = math.radians(self.barrel_deg)
        dx, dy = math.cos(ang), -math.sin(ang)
        nx, ny = -dy, dx
        rec = self.recoil * 7

        def quad(back, front, half):
            b = (px + dx * back, py + dy * back)
            f = (px + dx * front, py + dy * front)
            return [(b[0] + nx * half, b[1] + ny * half), (f[0] + nx * half, f[1] + ny * half),
                    (f[0] - nx * half, f[1] - ny * half), (b[0] - nx * half, b[1] - ny * half)]

        pygame.draw.polygon(surf, (138, 154, 214), quad(-10 - rec, BARREL_PX - rec, 5))
        pygame.draw.polygon(surf, (96, 110, 176), quad(-10 - rec, BARREL_PX - rec, 5)[2:] + [(px, py)])
        pygame.draw.polygon(surf, (190, 204, 250), quad(BARREL_PX - 10 - rec, BARREL_PX - rec, 7))
        if self.phase == AIM:
            for k in range(9):
                d = BARREL_PX + 16 + k * 15
                pygame.draw.circle(surf, mix(C_ACCENT, (24, 28, 70), k / 9), (int(px + dx * d), int(py + dy * d)), 2)
        aa_circle(surf, (58, 70, 130), (px, py), 14)
        aa_circle(surf, (104, 122, 196), (px, py), 14)
        aa_circle(surf, (58, 70, 130), (px, py), 12)
        aa_circle(surf, C_AMBER, (px, py), 3)
        if self.phase in (AIM, FLIGHT) and self.barrel_deg > 0.4:
            radius = 78
            arc = [(px + radius * math.cos(math.radians(a)), py - radius * math.sin(math.radians(a)))
                   for a in [i * self.barrel_deg / 24 for i in range(25)]]
            pygame.draw.line(surf, (92, 108, 190), (px, py), (px + radius + 14, py), 1)
            pygame.draw.lines(surf, C_ACCENT, False, arc, 2)
            mid = math.radians(self.barrel_deg / 2)
            self.ui.text(surf, f"{self.barrel_deg:.1f}°", "small_b", C_ACCENT,
                         (px + (radius + 28) * math.cos(mid), py - (radius + 28) * math.sin(mid) - 4), "midleft")
        if self.flash > 0:
            tip = (px + dx * BARREL_PX, py + dy * BARREL_PX)
            k = self.flash / 0.14
            add_glow(surf, tip, 46, fade_color((255, 190, 90), k))
            star = []
            for i in range(12):
                rad = (30 if i % 2 == 0 else 9) * k
                a = ang + i * math.pi / 6
                star.append((tip[0] + math.cos(a) * rad, tip[1] - math.sin(a) * rad))
            pygame.draw.polygon(surf, (255, 236, 176), star)

    def draw_balloons(self, surf):
        """Globos de ayuda (la bala los revienta), su animación de explosión y los textos de premio."""
        ui, t = self.ui, self.clock_t
        for b in self.balloons:
            if b["life"] - b["age"] < 2.5 and int(b["age"] * 6) % 2 == 0:
                continue
            x, y = self.view(b["wx"], b["wy"])
            if not -60 < x < FW + 60 or not -60 < y < FH + 60:
                continue
            y += 3.0 * math.sin(t * 2.2 + b["ph"])
            r = BALLOON_R * ease_out_back(clamp(b["age"] / 0.4, 0.0, 1.0))
            color = b["color"]
            pygame.draw.lines(surf, (150, 160, 210), False,
                              [(x, y + r + 4), (x - 5, y + r + 14), (x + 4, y + r + 24), (x - 2, y + r + 34)], 1)
            pygame.draw.polygon(surf, mix(color, (0, 0, 0), 0.4), [(x - 4, y + r + 6), (x + 4, y + r + 6), (x, y + r - 2)])
            aa_circle(surf, mix(color, (0, 0, 0), 0.35), (x, y), r)
            aa_circle(surf, color, (x, y - 1), r - 2)
            aa_circle(surf, mix(color, (255, 255, 255), 0.6), (x - r * 0.35, y - r * 0.38), max(2, r * 0.2))
            if b["kind"] == "doble":
                ui.text(surf, "×2", "h2", C_DARK, (x, y), "center")
            elif b["kind"] == "congelar":
                pygame.draw.rect(surf, C_DARK, (x - 8, y - 9, 5, 18), border_radius=2)
                pygame.draw.rect(surf, C_DARK, (x + 3, y - 9, 5, 18), border_radius=2)
            elif b["kind"] == "tiempo":
                ui.text(surf, f"+{BALLOON_TIME_BONUS:.0f}", "small_b", C_DARK, (x, y), "center")
            else:
                ui.text(surf, "?", "h1", C_DARK, (x, y), "center")
        for fx in self.pop_fx:
            k = fx["age"] / fx["life"]
            e = ease_out_cubic(k)
            x, y = self.view(fx["x"], fx["y"])
            color, dark = fx["color"], (18, 20, 50)
            add_glow(surf, (x, y), 8 * max(3, int((26 + 40 * e) / 8)), fade_color(color, 0.8 * (1.0 - k)))
            if k < 0.28:
                aa_circle(surf, mix(color, (255, 255, 255), k / 0.28), (x, y), BALLOON_R * (1.0 + 0.55 * k / 0.28))
            pygame.draw.circle(surf, mix(color, dark, k), (int(x), int(y)),
                               int(BALLOON_R * (0.8 + 1.5 * e)), max(1, int(5 * (1.0 - k))))
            for i in range(10):
                a = i * math.tau / 10 + fx["x"] * 0.37
                d, sz = BALLOON_R * (0.4 + 2.0 * e), BALLOON_R * 0.40 * (1.0 - k)
                cx, cy = x + math.cos(a) * d, y + math.sin(a) * d
                tri = [(cx + math.cos(a + w) * sz * m, cy + math.sin(a + w) * sz * m)
                       for w, m in ((0.0, 1.5), (2.4, 1.0), (-2.4, 1.0))]
                pygame.draw.polygon(surf, mix(color, dark, k ** 1.5), tri)
        for q in self.pops:
            k = q["age"] / q["life"]
            sx, sy = self.view(q["x"], q["y"])
            txt = ui.surf(q["text"], "h2", q["color"]).copy()
            txt.set_alpha(int(255 * (1 - k ** 2)))
            surf.blit(txt, txt.get_rect(midbottom=(sx, sy - 30 - 40 * ease_out_cubic(k))))

    def draw_effects(self, surf):
        for p in self.particles:
            t = p.age / p.life
            sx, sy = self.view(p.x, p.y)
            size = max(1.0, p.size * (1.0 - t * 0.6))
            pygame.draw.circle(surf, mix(p.color, (18, 20, 50), t ** 1.4), (int(sx), int(sy)), int(size))
            if p.glow and t < 0.8:
                add_glow(surf, (sx, sy), size * 4, fade_color(p.color, 0.5 * (1 - t)))
        for x, y, age, life, color, rmax in self.rings:
            t = age / life
            sx, sy = self.view(x, y)
            pygame.draw.circle(surf, mix(color, (18, 20, 50), t), (int(sx), int(sy)),
                               int(rmax * ease_out_cubic(t)) + 2, max(1, int(5 * (1 - t))))
        for f in self.floaters:
            t = f["age"] / f["life"]
            sx, sy = self.view(f["x"], f["y"])
            txt = self.ui.surf(f["text"], "big", f["color"]).copy()
            txt.set_alpha(int(255 * (1 - t ** 2)))
            surf.blit(txt, txt.get_rect(midbottom=(sx, sy - 30 - 46 * ease_out_cubic(t))))

    def draw_problem_card(self, s):
        ui, p, r = self.ui, self.problem, PROBLEM_RECT
        ui.card(s, r, accent=C_ACCENT)
        ui.text(s, p.title, "label", C_MUTED, (r.x + 18, r.y + 16))
        badge = {"plano": ("PLANO", C_ACCENT),
                 "colina": (f"COLINA +{p.height:.0f} m", C_AMBER),
                 "valle": (f"VALLE {p.height:.0f} m", C_VIOLET),
                 "cumbre": (f"CUMBRE +{p.height:.0f} m", C_GOLD)}[p.kind]
        ui.pill(s, badge[0], badge[1], r.right - 16, r.y + 12)
        ui.paragraph(s, p.story, "body", C_TEXT, (r.x + 18, r.y + 44), r.w - 36)
        chips = [("v_{0}", f"{p.speed:.0f} m/s"), ("D", f"{p.dist:.0f} m"),
                 ("g", f"{GRAVITY} m/s²"), ("h", "0 m" if p.height == 0 else f"{p.height:+.0f} m")]
        for i, (label, value) in enumerate(chips):
            rect = pygame.Rect(r.x + 16 + (i % 2) * 186, r.y + 92 + (i // 2) * 38, 178, 32)
            s.blit(ui.rounded(rect.size, 10, (22, 30, 68, 255), (60, 74, 146), 1), rect.topleft)
            ui.text(s, label, "body_b", C_MUTED, (rect.x + 12, rect.centery), "midleft")
            ui.text(s, value, "mono_b", C_TEXT, (rect.right - 12, rect.centery), "midright")

    def draw_answer_card(self, s):
        ui, r = self.ui, ANSWER_RECT
        ui.card(s, r, accent=C_AMBER)
        ui.text(s, "TU RESPUESTA", "label", C_MUTED, (r.x + 18, r.y + 16))
        if self.message:
            ui.text(s, self.message[0], "small_b", self.message[1], (r.right - 18, r.y + 15), "topright")
        else:
            ui.text(s, "0° derecha · 90° arriba · 180° izquierda", "tiny", C_MUTED, (r.right - 18, r.y + 17), "topright")
        self.angle_input.draw(ui, s, error=bool(self.message and self.message[1] == C_BAD), enabled=self.phase == AIM)
        self.fire_btn.draw(ui, s)
        self.bulb.draw(ui, s, self.clock_t)
        left = self.hint_left()
        if self.hints >= MAX_HINTS:
            status, color = "Sin pistas", C_BAD
        elif left > 0:
            status, color = f"Lista en {fmt_time(left)}", C_MUTED
        else:
            status, color = "Pista lista", C_AMBER
        ui.text(s, f"Pistas {self.hints}/{MAX_HINTS} · ×{self.multiplier():.2f}", "small_b", C_TEXT,
                (r.x + 76, r.y + 108))
        ui.text(s, status, "small", color, (r.x + 76, r.y + 128))
        self.new_btn.draw(ui, s)

    def draw_hint_drawer(self, s):
        """Panel desplegable con la última pista: fondo crema y texto oscuro (alto contraste)."""
        k = ease_out_cubic(self.drawer_t)
        if k < 0.02 or not 0 < self.hints <= len(self.hint_list):
            return
        ui, r = self.ui, DRAWER_RECT
        title, text, _span_ = self.hint_list[self.hints - 1]
        y = r.y - int((1.0 - k) * (r.h + 16))
        dx, dy = r.x, y
        s.blit(ui.rounded(r.size, 14, (0, 0, 0, 80)), (dx + 2, dy + 5))
        s.blit(ui.rounded(r.size, 14, (255, 247, 224, 255), (255, 176, 66), 2), (dx, dy))
        pygame.draw.rect(s, (255, 176, 66), (dx + 16, dy, 54, 4), border_radius=2)
        ui.text(s, f"PISTA {self.hints}/{MAX_HINTS}", "label", (150, 78, 0), (dx + 18, dy + 14))
        ui.text(s, title, "h2", (24, 28, 52), (dx + 18 + 86, dy + 9))
        ui.paragraph(s, text, "body", (30, 24, 10), (dx + 18, dy + 36), r.w - 36, gap=2)
        for i in range(MAX_HINTS):
            used = i < self.hints
            pygame.draw.circle(s, (232, 140, 20) if used else (214, 198, 160),
                               (dx + r.w - 52 - (MAX_HINTS - 1 - i) * 12, dy + 22), 4)
        cx, cy = dx + r.w - 23, dy + 23
        pygame.draw.circle(s, (240, 224, 186), (cx, cy), 12)
        pygame.draw.line(s, (90, 60, 10), (cx - 5, cy - 5), (cx + 5, cy + 5), 2)
        pygame.draw.line(s, (90, 60, 10), (cx + 5, cy - 5), (cx - 5, cy + 5), 2)

    def draw_method_card(self, s):
        ui, p, r = self.ui, self.problem, METHOD_RECT
        ui.card(s, r, accent=C_GOOD)
        ui.text(s, "MÉTODO NEWTON-RAPHSON", "label", C_MUTED, (r.x + 18, r.y + 16))
        ui.pill(s, f"PISTAS {self.hints}/{MAX_HINTS}", C_GOOD, r.right - 16, r.y + 12)
        s.blit(self.formula, self.formula.get_rect(midtop=(r.centerx, r.y + 34)))
        c = p.c
        sg = "-" if p.side < 0 else ""
        tail = "" if p.height == 0 else f" {'-' if p.height > 0 else '+'} {abs(p.height):.0f}"
        ui.text(s, f"f(X) = {sg}{p.dist:.0f}·tan X - {c:.2f}·sec²X{tail}", "mono_s", C_TEXT, (r.x + 18, r.y + 90))
        ui.text(s, f"f'(X) = sec²X·({sg}{p.dist:.0f} - {2 * c:.2f}·tan X)", "mono_s", C_TEXT, (r.x + 18, r.y + 108))
        shown = cells_revealed(self.hints, p.ans_row)
        seed = f"{fmt_deg(p.seed_deg)}°" if p.ans_row == 2 or 0 in shown else "?"
        ui.text(s, f"Semilla X_{{0}} = {seed} · respuesta: X que ya no cambia", "tiny", C_MUTED,
                (r.x + 18, r.y + 127))

        top = r.y + 148
        box = pygame.Rect(r.x + 12, top - 4, r.w - 24, r.bottom - top - 2)
        s.blit(ui.rounded(box.size, 10, (10, 14, 34, 255), (70, 86, 160), 1), box.topleft)
        s.blit(ui.rounded((box.w - 8, 22), 6, (30, 44, 98, 255)), (box.x + 4, box.y + 3))
        cols = (r.x + 22, r.x + 58, r.x + 168, r.x + 286)
        widths = (96, 108, 86)
        for x, head in zip(cols, ("n", "X_{n} (°)", "f(X_{n})", "f'(X_{n})")):
            ui.text(s, head, "small_b", C_ACCENT, (x, top))
        flash = clamp(1.0 - (self.clock_t - self.flash_t0) / 1.8, 0.0, 1.0)
        for i, st in enumerate(p.steps):
            y = top + 26 + i * 19
            answer = i == p.ans_row
            if i % 2 == 0:
                s.blit(ui.rounded((box.w - 8, 19), 5, (24, 34, 76, 255)), (box.x + 4, y - 2))
            ui.text(s, str(st.n), "mono_s", C_MUTED, (cols[0], y))
            values = (f"{math.degrees(st.X):.5f}", f"{st.fx:+.4f}", f"{st.dfx:.3f}")
            for j, v in enumerate(values):
                idx, x = 3 * i + j, cols[j + 1]
                if idx in shown:
                    if flash > 0.0 and idx not in self.cells_prev:
                        glow = int(150 * flash) // 16 * 16
                        if glow:
                            s.blit(ui.rounded((widths[j], 18), 5, (*C_GOOD, glow)), (x - 4, y - 2))
                    ui.text(s, v, "mono_s", C_GOOD if answer and 3 * i in shown else C_TEXT, (x, y))
                else:
                    ui.text(s, "· · ·", "mono_s", (84, 98, 160), (x, y))
            if answer and 3 * i in shown:
                pygame.draw.lines(s, C_GOOD, False, [(r.right - 34, y + 8), (r.right - 29, y + 13), (r.right - 20, y + 3)], 2)
        span = None
        for _title, _text, rg in self.hint_list[: self.hints]:
            span = rg or span
        if self.hints == 0:
            caption, color = "Pulsa la bombilla para descubrir las celdas", (190, 202, 240)
        elif span:
            caption, color = f"Rango del ángulo: {span[0]}° a {span[1]}°", C_AMBER
        else:
            caption, color = "Cada pista descubre nuevas celdas", (190, 202, 240)
        ui.text(s, caption, "small_b", color, (box.centerx, box.bottom - 13), "center")

    def build_feedback(self):
        ui, res, p = self.ui, self.pending, self.problem
        cat, color = res["cat"], CAT_COLOR[res["cat"]]
        hit = cat in ("diana", "acierto")
        tip = res.get("tip")
        phrase = self.pick_phrase(cat)
        ex = max(0, len(ui.wrap(phrase, "h2", 400)) - 2) * (ui.styles["h2"][0].get_linesize() + 3)
        w, h = 520, 150 + ex + (80 if tip else 0)
        card = pygame.Surface((w, h), pygame.SRCALPHA)
        ui.card(card, pygame.Rect(0, 0, w, h), fill=(10, 14, 36, 244), border=(*color, 170), radius=20)
        pygame.draw.rect(card, color, (22, 0, 60, 4), border_radius=2)
        cx, cy = 52, 52
        aa_circle(card, (*color, 40), (cx, cy), 30)
        pygame.draw.circle(card, color, (cx, cy), 30, 3)
        if cat == "diana":
            for f in (0.6, 0.3):
                pygame.draw.circle(card, color, (cx, cy), int(30 * f), 3)
            aa_circle(card, color, (cx, cy), 4)
        elif cat == "acierto":
            pygame.draw.lines(card, color, False, [(cx - 12, cy + 1), (cx - 3, cy + 10), (cx + 13, cy - 11)], 5)
        elif cat == "cerca":
            pygame.draw.circle(card, color, (cx - 5, cy + 3), 11, 3)
            aa_circle(card, color, (cx + 12, cy - 12), 4)
        else:
            pygame.draw.line(card, color, (cx - 11, cy - 11), (cx + 11, cy + 11), 5)
            pygame.draw.line(card, color, (cx + 11, cy - 11), (cx - 11, cy + 11), 5)
        ui.text(card, CAT_TITLE[cat], "h1", color, (100, 12))
        ui.paragraph(card, phrase, "h2", C_TEXT, (100, 46), 400)
        pygame.draw.line(card, (60, 74, 140), (22, 102 + ex), (w - 22, 102 + ex), 1)
        third = (("X REAL (NR)", f"{p.root_deg:.3f}°") if hit
                 else ("AJUSTE", "SUBE X" if res["angle"] < p.root_deg else "BAJA X"))
        stats = (("TU ÁNGULO", f"{res['angle']:.3f}°"), ("AL CENTRO", f"{res['dist']:.1f} m"), third)
        for i, (label, value) in enumerate(stats):
            ui.text(card, label, "label", C_MUTED, (24 + i * 116, 110 + ex))
            ui.text(card, value, "mono_b", C_TEXT, (24 + i * 116, 126 + ex))
        pts = f"+{res['points']}" if res["points"] else "0"
        ui.text(card, pts, "stat", color, (w - 24, 106 + ex), "topright")
        if tip:
            box = pygame.Rect(22, 156 + ex, w - 44, 70)
            card.blit(ui.rounded(box.size, 12, (44, 32, 10, 255), (*C_AMBER, 200), 1), box.topleft)
            draw_bulb(card, (box.x + 30, box.centery + 3), 0.9, 0.0, False)
            ui.text(card, "CONSEJO", "label", C_AMBER, (box.x + 62, box.y + 8))
            ui.paragraph(card, tip, "small", (255, 236, 200), (box.x + 62, box.y + 26), box.w - 76, gap=1)
        return card

    def pick_phrase(self, cat):
        options = [x for x in PHRASES[cat] if x != self.last_phrase.get(cat)]
        phrase = self.last_phrase[cat] = random.choice(options)
        return phrase

    def draw_status(self, s):
        """Aviso breve de ayuda generada y etiquetas de los power-ups activos."""
        ui = self.ui
        mt = self.mini_toast
        if mt:
            k = min(clamp(mt["age"] / 0.2, 0.0, 1.0), clamp((mt["life"] - mt["age"]) / 0.4, 0.0, 1.0))
            rect = pygame.Rect(FIELD.right - 256, FIELD.y + 14, 240, 52)
            box = ui.rounded(rect.size, 12, (44, 32, 10, 255), (*C_AMBER, 220), 1).copy()
            ui.text(box, "¡SE GENERÓ UNA AYUDA!", "small_b", C_AMBER, (14, 8))
            ui.text(box, "Atraviésalos con tu disparo", "tiny", (255, 236, 200), (14, 29))
            box.set_alpha(int(255 * k))
            s.blit(box, rect.topleft)
        y = FIELD.y + 76
        if self.double_next:
            ui.pill(s, "×2 PUNTOS", C_GOLD, FIELD.right - 16, y)
            y += 30
        if self.freeze_t > 0.0:
            ui.pill(s, f"TIEMPO CONGELADO {math.ceil(self.freeze_t)} s", C_ACCENT, FIELD.right - 16, y)

    def draw_toast(self, s):
        """Frase de resultado: aparece con un pequeño salto y se desvanece sola en pocos segundos."""
        t = self.toast
        if not t:
            return
        card, age, life = t["card"], t["age"], t["life"]
        w, h = card.get_size()
        rect = card.get_rect(midbottom=(FIELD.centerx, FIELD.bottom - 14))
        alpha = int(255 * min(clamp(age / 0.18, 0.0, 1.0), clamp((life - age) / 0.6, 0.0, 1.0)))
        shown = card
        if age < 0.3:
            k = 0.85 + 0.15 * ease_out_back(age / 0.3)
            shown = pygame.transform.smoothscale(card, (max(1, int(w * k)), max(1, int(h * k))))
        shown.set_alpha(alpha)
        s.set_clip(FIELD)
        s.blit(shown, shown.get_rect(center=rect.center))
        s.set_clip(None)

    def draw_next_button(self, s):
        """Tras dar al blanco: botón «Nueva Ecuación» con cuenta atrás de 7 s (luego se inicia sola)."""
        if self.phase != SOLVED:
            return
        ui = self.ui
        last = self.round_index + 1 >= ROUNDS_PER_MATCH
        self.next_btn.label = "Ver Resultados" if last else "Nueva Ecuación"
        rect = pygame.Rect(FIELD.centerx - 160, FIELD.y + 18, 320, 56)
        self.next_btn.rect = rect
        self.next_btn.draw(ui, s)
        frac = clamp(self.auto_t / AUTO_NEXT_SECONDS, 0.0, 1.0)
        bar = pygame.Rect(rect.x + 10, rect.bottom + 8, rect.w - 20, 6)
        pygame.draw.rect(s, (30, 40, 90), bar, border_radius=3)
        if frac > 0.0:
            pygame.draw.rect(s, C_ACCENT, (bar.x, bar.y, max(6, int(bar.w * frac)), bar.h), border_radius=3)
        ui.text(s, f"Se inicia sola en {math.ceil(self.auto_t)} s", "tiny", C_TEXT, (rect.centerx, bar.bottom + 6), "midtop")

    def draw_ranking(self, dst, rect, title, highlight=None):
        ui = self.ui
        ui.card(dst, rect, accent=C_AMBER)
        ui.text(dst, title, "label", C_MUTED, (rect.x + 20, rect.y + 18))
        if not self.rows:
            ui.text(dst, "Aún no hay puntuaciones guardadas.", "body_b", C_TEXT, (rect.centerx, rect.centery - 6), "center")
            ui.text(dst, "Juega una partida y guarda tu nombre para aparecer aquí.", "small", C_MUTED,
                    (rect.centerx, rect.centery + 18), "center")
            return
        right = {"PART.": rect.right - 292, "ACIER.": rect.right - 224, "ERR.": rect.right - 160,
                 "A/E": rect.right - 98, "PROM.": rect.right - 24}
        ui.text(dst, "#", "label", C_ACCENT, (rect.x + 24, rect.y + 44))
        ui.text(dst, "ARTILLERO", "label", C_ACCENT, (rect.x + 58, rect.y + 44))
        for head, x in right.items():
            ui.text(dst, head, "label", C_ACCENT, (x, rect.y + 44), "topright")
        row_h = 24 if rect.h < 300 else 28
        medals = [(255, 201, 71), (196, 206, 230), (214, 134, 78)]
        for i, row in enumerate(self.rows[: (rect.h - 82) // row_h]):
            y = rect.y + 68 + i * row_h
            if highlight and row["name"].casefold() == highlight.casefold():
                dst.blit(ui.rounded((rect.w - 24, row_h - 2), 8, (*C_ACCENT, 46), (*C_ACCENT, 120)), (rect.x + 12, y - 2))
            elif i % 2 == 0:
                dst.blit(ui.rounded((rect.w - 24, row_h - 2), 8, (255, 255, 255, 12)), (rect.x + 12, y - 2))
            cy = y + row_h // 2 - 2
            if i < 3:
                aa_circle(dst, medals[i], (rect.x + 33, cy), 9)
                ui.text(dst, str(i + 1), "small_b", (30, 22, 6), (rect.x + 33, cy), "center")
            else:
                ui.text(dst, str(i + 1), "small_b", C_MUTED, (rect.x + 33, cy), "center")
            ui.text(dst, row["name"], "body_b", C_TEXT, (rect.x + 58, cy), "midleft")
            values = {"PART.": str(row["games"]), "ACIER.": str(row["hits"]), "ERR.": str(row["errors"]),
                      "A/E": f"{row['ratio']:.2f}", "PROM.": f"{row['average']:.1f}"}
            for head, x in right.items():
                color = C_AMBER if head == "PROM." else C_GOOD if head == "ACIER." else C_BAD if head == "ERR." else C_TEXT
                ui.text(dst, values[head], "mono_b", color, (x, cy), "midright")

    def draw_wide_backdrop(self):
        """Cielo y montañas a pantalla completa (también detrás de los bordes del lienzo)."""
        d = self.display
        self.menu_bd.draw(d, self.scroll, 0, self.clock_t)
        d.blit(self.menu_ground, (0, self.oy + HEIGHT - self.menu_ground.get_height()))
        if self.canvas[1] > self.oy + HEIGHT:
            d.fill((8, 11, 28), (0, self.oy + HEIGHT, self.canvas[0], self.canvas[1] - self.oy - HEIGHT))

    def draw_menu(self):
        s, ui = self.screen, self.ui
        self.draw_wide_backdrop()
        self.display.blit(self.menu_fade, (0, 0))
        s.blit(self.reticle, self.reticle.get_rect(center=(330, 400)))
        draw_logo(s, (84, 78), 20)
        ui.text(s, "SIMULADOR BALÍSTICO  ·  MÉTODOS NUMÉRICOS", "label", C_ACCENT, (120, 70))
        s.blit(self.title_a, (60, 108))
        s.blit(self.title_b, (60, 108 + self.title_a.get_height() - 6))
        y = 108 + self.title_a.get_height() * 2 + 12
        ui.paragraph(s, "Dispara con matemáticas: encuentra el ángulo exacto con Newton-Raphson y no falles al blanco.",
                     "lead", C_MUTED, (64, y), 500, gap=4)
        ui.text(s, "NOMBRE DEL ARTILLERO  ·  opcional", "label", C_MUTED, (64, 402))
        self.menu_input.draw(ui, s)
        self.play_btn.draw(ui, s)
        ui.text(s, "ENTER para jugar  ·  ESC para salir", "tiny", C_MUTED, (64, 592))
        self.draw_tutorial(s)
        self.draw_ranking(s, MENU_RANK, "CLASIFICACIÓN  ·  PROMEDIO POR PARTIDA")

    def draw_tutorial(self, s):
        """Panel «¿Cómo se juega?»: 4 tarjetas con icono animado, resumen de puntos y la fórmula."""
        ui, r = self.ui, MENU_TUTORIAL
        t = self.clock_t
        ui.card(s, r, accent=C_ACCENT)
        draw_logo(s, (r.x + 34, r.y + 29), 9)
        ui.text(s, "¿CÓMO SE JUEGA?", "h2", C_TEXT, (r.x + 56, r.y + 28), "midleft")
        ui.pill(s, "4 PASOS", C_ACCENT, r.right - 20, r.y + 18)
        pygame.draw.line(s, (60, 74, 140), (r.x + 20, r.y + 48), (r.right - 20, r.y + 48), 1)

        steps = (
            (C_ACCENT, "target", "MIRA EL BLANCO",
             "Puede estar cerca o lejos, arriba o abajo, a tu derecha o a tu izquierda."),
            (C_VIOLET, "angle", "BUSCA EL ÁNGULO",
             "Halla el ángulo del cañón (0° a 180°). Si fallas, la ecuación NO cambia: intenta de nuevo."),
            (C_GOOD, "newton", "USA NEWTON-RAPHSON",
             "La fórmula de abajo corrige un ángulo de prueba paso a paso. ¡La tabla guarda la respuesta!"),
            (C_AMBER, "bulb", "PIDE AYUDA",
             f"Bombilla: {MAX_HINTS} pistas (1 cada {HINT_COOLDOWN:.0f} s). Si fallas mucho salen globos con ayudas: ¡atraviésalos con la bala! Durante el vuelo, haz clic para acelerarla."),
        )
        gap = 8
        cw = (r.w - 40 - gap) // 2
        text_w = cw - 28
        line_h = ui.styles["small"][0].get_linesize() + 2
        lines = [len(ui.wrap(text, "small", text_w)) for _, _, _, text in steps]
        row_h = [max(lines[0], lines[1]) * line_h + 44, max(lines[2], lines[3]) * line_h + 44]
        y0 = r.y + 56
        for i, (color, icon, title, text) in enumerate(steps):
            col, row = i % 2, i // 2
            x = r.x + 20 + col * (cw + gap)
            y = y0 + (row_h[0] + gap if row else 0)
            h = row_h[row]
            s.blit(ui.rounded((cw, h), 12, (18, 26, 62, 235), (*color, 120), 1), (x, y))
            pygame.draw.rect(s, color, (x + 14, y, 40, 3), border_radius=2)
            aa_circle(s, color, (x + 26, y + 21), 11)
            ui.text(s, str(i + 1), "small_b", C_DARK, (x + 26, y + 21), "center")
            ui.text(s, title, "small_b", color, (x + 44, y + 21), "midleft")
            draw_step_icon(s, icon, (x + cw - 30, y + 21), color, t)
            ui.paragraph(s, text, "small", C_TEXT, (x + 14, y + 38), text_w, gap=2)
        sy = y0 + row_h[0] + row_h[1] + gap + 8
        pills = (("BLANCO +60", C_GOOD), ("DIANA +100 · ±0.005°", C_GOLD), ("10 MIN · FALLAR −10 s", C_VIOLET))
        x = r.x + 20
        for text, color in pills:
            w = ui.measure(text, "label") + 22
            ui.pill(s, text, color, x + w, sy)
            x += w + 8
        box = pygame.Rect(r.x + 20, r.bottom - 70, r.w - 40, 58)
        s.blit(ui.rounded(box.size, 12, (10, 14, 34, 255), (*C_ACCENT, 150), 1), box.topleft)
        pygame.draw.rect(s, C_ACCENT, (box.x + 14, box.y, 40, 3), border_radius=2)
        ui.text(s, "FÓRMULA DE ITERACIÓN", "label", C_MUTED, (box.x + 16, box.centery), "midleft")
        s.blit(self.formula, self.formula.get_rect(center=(box.centerx + 70, box.centery)))

    def draw_result(self):
        s, ui, m = self.screen, self.ui, self.match
        self.draw_wide_backdrop()
        self.display.blit(self.dim, (0, 0))
        ui.text(s, "TIEMPO AGOTADO" if self.time_out else "PARTIDA TERMINADA", "big", C_TEXT, (WIDTH // 2, 30), "midtop")

        r = RES_LEFT
        ui.card(s, r, accent=C_ACCENT)
        ui.text(s, "PUNTUACIÓN FINAL", "label", C_MUTED, (r.x + 28, r.y + 24))
        score = ui.text(s, str(m.points), "score", C_ACCENT, (r.x + 28, r.y + 40))
        ui.text(s, f"/ {ROUNDS_PER_MATCH * POINTS['diana']} puntos", "h1", C_MUTED, (score.right + 14, score.bottom - 40))
        pygame.draw.line(s, (60, 74, 140), (r.x + 28, r.y + 158), (r.right - 28, r.y + 158), 1)
        shots = max(m.shots, 1)
        tiles = (
            ("ACIERTOS", str(m.hits), C_GOOD), ("ERRORES", str(m.errors), C_BAD),
            ("A / E", f"{m.hits / max(m.errors, 1):.2f}", C_ACCENT), ("EFECTIVIDAD", f"{100 * m.hits / shots:.0f} %", C_AMBER),
            ("DIANAS", str(m.bulls), C_GOLD), ("PISTAS USADAS", str(m.hints), C_VIOLET),
        )
        for i, (label, value, color) in enumerate(tiles):
            rect = pygame.Rect(r.x + 28 + (i % 2) * 240, r.y + 180 + (i // 2) * 96, 228, 84)
            s.blit(ui.rounded(rect.size, 14, (20, 28, 64, 255), (60, 74, 146), 1), rect.topleft)
            ui.text(s, label, "label", C_MUTED, (rect.x + 16, rect.y + 14))
            ui.text(s, value, "stat", color, (rect.x + 16, rect.y + 34))

        ui.card(s, RES_SAVE, accent=C_GOOD)
        ui.text(s, "GUARDA TU PUNTUACIÓN", "label", C_MUTED, (RES_SAVE.x + 24, RES_SAVE.y + 20))
        self.result_input.draw(ui, s, enabled=not self.saved_name)
        self.save_btn.draw(ui, s)
        if self.save_note:
            ui.text(s, self.save_note[0], "small", self.save_note[1], (RES_SAVE.x + 24, RES_SAVE.y + 106))
        else:
            ui.text(s, "Se guarda una sola vez, con un nombre que no esté registrado.", "small", C_MUTED, (RES_SAVE.x + 24, RES_SAVE.y + 106))
        self.draw_ranking(s, RES_RANK, "CLASIFICACIÓN  ·  PROMEDIO POR PARTIDA", self.saved_name)
        self.again_btn.draw(ui, s)
        self.menu_btn.draw(ui, s)

    def draw(self):
        {MENU: self.draw_menu, PLAY: self.draw_play, RESULT: self.draw_result}[self.state]()
        pygame.display.flip()

    async def run(self):
        while self.running:
            raw = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(min(raw, 0.05), raw)
            self.draw()
            await asyncio.sleep(0)

async def main():
    game = Game()
    try:
        await game.run()
    finally:
        pygame.key.stop_text_input()
        pygame.quit()

if __name__ == "__main__":
    asyncio.run(main())