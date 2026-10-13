import sys
import os
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"  # v2.1: Chromium dentro del paquete (para el .exe)
import asyncio

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from nicegui import ui, app, run
import urllib.request
import urllib.parse
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import pandas as pd
import email.utils
import datetime
import time
import re
import unicodedata
import json
import os
import io
import csv
import queue
import requests
import subprocess
import threading

# ====================================================================
# Hecho por Santiago Allende de Ketchum
# ====================================================================
# CONFIGURACIÓN Y VERSIÓN
# ====================================================================
APP_VERSION = "3.0"
URL_VERSION_GITHUB = "https://raw.githubusercontent.com/santiagoarielallende93-del/ClippingMulticlienteQuilljs/main/version.txt"
URL_MAIN_PYTHON_GITHUB = "https://raw.githubusercontent.com/santiagoarielallende93-del/ClippingMulticlienteQuilljs/main/main.py"
# v5.79: SECRETOS FUERA DEL CÓDIGO. Las keys y usuarios viven en archivos junto al .exe (config.env, usuarios.json, .secret)
import hashlib, hmac, secrets
BASE_DIR = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
_NOMBRES_CLIENTES_KEYS = ["MSD Salud Animal", "Mars", "BMS", "Arredo", "Amanco Wavin", "Booking", "Mail Boxes"]
def _nombre_env(c): return "GROQ_KEY_" + re.sub(r'[^A-Z0-9]+', '_', c.upper()).strip('_')

def _cargar_config_env():
    ruta = os.path.join(BASE_DIR, "config.env")
    if not os.path.exists(ruta):
        try:
            with open(ruta, 'w', encoding='utf-8') as f:
                f.write("# Completá las API Keys de Groq (sin comillas ni espacios). No compartas este archivo.\n")
                f.write("GROQ_KEY_COMPARTIDA_1=\nGROQ_KEY_COMPARTIDA_2=\n")
                for c in _NOMBRES_CLIENTES_KEYS: f.write(f"{_nombre_env(c)}=\n")
        except Exception: pass
    cfg = {}
    try:
        with open(ruta, encoding='utf-8-sig') as f:
            for l in f:
                l = l.strip()
                if l and not l.startswith('#') and '=' in l:
                    k, v = l.split('=', 1); cfg[k.strip()] = v.strip().strip('"').strip("'")
    except Exception: pass
    return cfg
_CFG = _cargar_config_env()
GROQ_API_KEY = os.environ.get("GROQ_KEY_COMPARTIDA_1") or _CFG.get("GROQ_KEY_COMPARTIDA_1", "")
GROQ_API_KEY_2 = os.environ.get("GROQ_KEY_COMPARTIDA_2") or _CFG.get("GROQ_KEY_COMPARTIDA_2", "")
GROQ_KEYS = [k for k in (GROQ_API_KEY, GROQ_API_KEY_2) if k]
# v5.88: pantalla de revisión: fecha y dominio de cada nota en gris
# v5.87: Mail Boxes: keywords y búsquedas RSS agrupadas (Competencia y Noticias de Interés)
# v5.86: velocidad: bloqueo de recursos pesados, lectura previa con requests y resolución de links de Google News sin navegador
# v5.85: el lector del Word acepta también un link de Google Docs/Drive
# v5.84: botón para cargar los links hipervinculados del Word compartido (por cliente y sección) en las notas manuales
# v5.83: editor: auto-scroll al arrastrar una nota cerca del borde de la pantalla
# v5.82: editor del reporte: mejoras visuales (animaciones, tarjetas, botones, scroll, modal, móvil)
# v5.81: sin tope por búsqueda en Mars, MSD, Mail Boxes y en Exclusivas/Competencia/Mención de BMS, Arredo, Booking y Amanco; URLs RSS corregidas
# v5.80: tope de notas por búsqueda automático = max(3, límite de la sección / nº de búsquedas)
# v5.79: Mars Competencia y Noticias de Interés: RSS agrupados de a 3 con OR (se corrigen URLs mal formadas); APP_VERSION 2.7
# v5.78: se elimina el registro de actividad (registro_uso.csv) y el visor de log del admin
# v5.77: indicador de búsqueda solo para RSS de Google (no para feeds del Excel)
# v5.76: nota excluida en una búsqueda se omite directo si reaparece en otra de la misma sección (solo por link)
# v5.75: nota excluida en una búsqueda se omite directo si reaparece en otra de la misma sección
# v5.74: Amanco Sustentabilidad: nuevos RSS agrupados y keywords
# v5.73: se quita '· N sumadas' del chip; se muestra a la derecha el RSS en curso
# v5.72: tiempo máximo por sección: 3 minutos (antes 2)
# v5.71: límites: semana suma +10 extra (3 días +5 extra)
# v5.70: máx 3 notas por búsqueda RSS (todos); límites +5 (+5 más si 3 días o semana)
# v5.69: pantalla (junto al estado) = aprobadas totales x/límite de la sección; log = aprobadas por búsqueda RSS
# v5.66: Amanco Industria: RSS agrupados con OR; orden por tier dentro de cada búsqueda (1 y 2 primero); Tier 3 excluidas en secciones de IDS_EXCLUIR_TIER3
# v5.65: Amanco Industria e Infraestructura: nuevos RSS y keywords
# v5.64: 'Copiar al portapapeles' copia solo el reporte (sin el bloque contenedor gris)
# v5.63: 'Copiar al portapapeles' vuelve al método de v5.60 (se mantiene el botón ☰ del menú lateral)
# v5.62: copiar al portapapeles sin demora (conserva el gesto del usuario) + respaldo con API del portapapeles
# v5.61: menú lateral con botón ☰ para reabrir; 'Copiar al portapapeles' copia como selección manual (iframe)
# v5.60: botón 'Copiar al portapapeles' en el editor (copia el reporte con formato)
# v5.59: puerto configurable con la variable PUERTO (por defecto 8080)
# v5.58: historial solo afecta feed/Google (no manuales); Arredo Competencia sin métricas; Booking Turismo: más notas tier 1/2 y tope 5 por sitio
# v5.57: una API Key propia por cliente (evita saturaciones). Las compartidas de arriba quedan como respaldo.
GROQ_KEY_POR_CLIENTE = {c: (os.environ.get(_nombre_env(c)) or _CFG.get(_nombre_env(c), "")) for c in _NOMBRES_CLIENTES_KEYS}
def keys_para_cliente(cliente):
    propia = GROQ_KEY_POR_CLIENTE.get(cliente)
    return ([propia] if propia else []) + [k for k in GROQ_KEYS if k != propia]  # puede quedar vacía si falta config.env
# ---------- FILTRO "SOLO ARGENTINA" (BMS, todas las secciones excepto Exclusivas) ----------
CLIENTES_FILTRO_AR = ["BMS"]
SECCIONES_SIN_FILTRO_AR = ["bms_tema_1"]  # Exclusivas
SECCIONES_FILTRO_AR_ESTRICTO_RSS = ["bms_tema_4"]  # Competencia: descarta extranjeros ANTES de leer la nota

# Sitios NO ".ar" que SÍ son argentinos (dominios sin "www."). AGREGAR ACÁ los nuevos.
SITIOS_COM_ARGENTINOS = [
    "infobae.com", "iprofesional.com", "elonce.com", "ambito.com", "cronista.com", "baenegocios.com",
    "clarin.com", "perfil.com", "eldia.com", "minutouno.com", "mdzol.com", "diarioregistrado.com",
    "elintransigente.com", "lapoliticaonline.com", "cadena3.com", "saludiario.com", "infocampo.com",
    "eldiarioar.com", "noticiasargentinas.com", "mejorinformado.com", "infonegocios.com", "0223.com", "pharmabiz.net", "pmfarma.com", "cienciatecno.com", "presenterse.com", "yahoo.com", "latamsalud.com", "parasusalud.tv", "la100.cienradios.com", "gov.ar", "eldestapeweb.com", "campoenaccion.com", "totalmedios.com", "nuevodiarioweb.com"
]

# Si el sitio no es .ar ni está en la lista, se acepta solo si el texto habla de Argentina (agregar/quitar a gusto)
KW_ARGENTINA = ["argentina", "argentino", "argentinos", "argentinas", "anmat", "buenos aires",
                "conicet", "milei", "ministerio de salud de la nacion", "superintendencia de servicios de salud",
                "obras sociales", "sistema de salud argentino"]

# Diarios argentinos con prioridad máxima (se matchea contra nombre del medio o dominio, sin espacios/acentos)
PRIORIDAD_DIARIOS_AR = ["baenegocios", "ambito", "cronista", "infobae", "clarin", "lanacion", "iprofesional",
                        "pagina12", "perfil", "telam", "elonce", "lavoz", "rionegro", "losandes", "lagaceta"]

def aplica_filtro_ar(cliente_nombre, sec_id):
    return cliente_nombre in CLIENTES_FILTRO_AR and sec_id not in SECCIONES_SIN_FILTRO_AR

def es_diario_ar_prioritario(medio, url=""):
    m = re.sub(r'[^a-z0-9]', '', remover_acentos(str(medio).lower()))
    h = urlparse(str(url)).netloc.lower().replace("www.", "")
    h = re.sub(r'[^a-z0-9]', '', h)
    return any(d in m or d in h for d in PRIORIDAD_DIARIOS_AR)

def es_sitio_permitido_ar(url, medio="", texto=""):
    """True si es .ar, está en SITIOS_COM_ARGENTINOS, es diario prioritario, o el texto habla de Argentina."""
    try: host = urlparse(str(url)).netloc.lower().split(':')[0]
    except Exception: host = ""
    if host.startswith('www.'): host = host[4:]
    if not host or host.endswith('google.com'): return True  # destino sin resolver: no se juzga todavía
    if host.endswith('.ar'): return True
    if any(host == d or host.endswith('.' + d) for d in SITIOS_COM_ARGENTINOS): return True
    if es_diario_ar_prioritario(medio, url): return True
    t = remover_acentos(f"{texto} {medio}".lower())
    return any(k in t for k in KW_ARGENTINA)

LIMITE_POOL_IA = 30  # Máx. de notas a analizar con IA por sección

_GROQ_LOCK = threading.Lock()
_GROQ_BLOQUEADA_HASTA = {}  # índice de key -> timestamp hasta el que se considera saturada

def llamar_groq(payload, timeout=25, logger=None, cliente=None):
    """POST a Groq con la key propia del cliente; si está saturada (429/503) o inválida (401/403), pasa a las de respaldo."""
    ultimo_error = None
    keys = keys_para_cliente(cliente)
    for idx, key in enumerate(keys):
        with _GROQ_LOCK:
            if _GROQ_BLOQUEADA_HASTA.get(key, 0) > time.time():
                continue
        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=payload, timeout=timeout)
            if resp.status_code in (401, 403, 429, 498, 503):
                try: espera = min(float(resp.headers.get("retry-after", 60)), 3600)
                except Exception: espera = 60
                if resp.status_code in (401, 403): espera = 3600
                with _GROQ_LOCK:
                    _GROQ_BLOQUEADA_HASTA[key] = time.time() + max(espera, 5)
                if logger: logger(f"    🔑 API Key {idx+1} ({cliente or 'compartida'}) no disponible (HTTP {resp.status_code}). Probando la siguiente...")
                ultimo_error = Exception(f"HTTP {resp.status_code} en key {idx+1}")
                continue
            resp.raise_for_status()
            return resp
        except requests.exceptions.HTTPError:
            raise
        except Exception as e:
            ultimo_error = e
            continue
    raise ultimo_error or Exception("No hay API Keys configuradas (revisá config.env) o están todas saturadas")

USAR_FILTRO_IA = True  # Desactivable globalmente si se requiere
LINK_EXCEL_DRIVE = "https://docs.google.com/spreadsheets/d/1ZntitgSKrfkaL5rpG45ajwbr0yPVvfAp/edit?usp=sharing&ouid=110785507732300006515&rtpof=true&sd=true"

# Cache global de gacetillas para renderizado en UI
GACETILLAS_CACHE = None

# Caché por Sesión para evaluación de IA (Acelera búsquedas y ahorra tokens)
CACHE_IA_SESION = {}

# Archivos de persistencia histórica antiduplicados
HISTORIAL_JSON = "historial_notas.json"
HISTORIAL_EXCEL = "historial_notas.xlsx"

def _hash_pw(pwd, salt=None):
    salt = salt or secrets.token_hex(16)
    return salt + "$" + hashlib.pbkdf2_hmac('sha256', pwd.encode('utf-8'), bytes.fromhex(salt), 200000).hex()

def _verificar_pw(pwd, guardado):
    try:
        salt, _ = guardado.split("$", 1)
        return hmac.compare_digest(_hash_pw(pwd, salt), guardado)
    except Exception:
        return False

RUTA_USUARIOS = os.path.join(BASE_DIR, "usuarios.json")
def _cargar_usuarios():
    if not os.path.exists(RUTA_USUARIOS):  # primera vez: crea usuarios iniciales (cambiá las claves con: programa.exe --usuario NOMBRE CLAVE rol)
        ini = {"admin": {"hash": _hash_pw("admin123"), "rol": "admin"}, "usuario": {"hash": _hash_pw("clipping2026"), "rol": "usuario"}}
        try: json.dump(ini, open(RUTA_USUARIOS, 'w', encoding='utf-8'), indent=2)
        except Exception: pass
        return ini
    try: return json.load(open(RUTA_USUARIOS, encoding='utf-8'))
    except Exception: return {}

def _storage_secret():
    ruta = os.path.join(BASE_DIR, ".secret")
    try:
        if os.path.exists(ruta): return open(ruta, encoding='utf-8').read().strip()
        v = secrets.token_hex(32); open(ruta, 'w', encoding='utf-8').write(v); return v
    except Exception:
        return secrets.token_hex(32)

if len(sys.argv) >= 4 and sys.argv[1] == "--usuario":  # uso: main.exe --usuario NOMBRE CLAVE [admin|usuario]
    _u = _cargar_usuarios(); _u[sys.argv[2]] = {"hash": _hash_pw(sys.argv[3]), "rol": sys.argv[4] if len(sys.argv) > 4 else "usuario"}
    json.dump(_u, open(RUTA_USUARIOS, 'w', encoding='utf-8'), indent=2); print(f"Usuario '{sys.argv[2]}' guardado."); sys.exit(0)

DOMINIOS_EXTRANJEROS = ['.mx', '.pe', '.co', '.cl', '.es', '.uy', '.py', '.ve', '.ec', '.bo', '.cr', '.gt', '.hn', '.ni', '.pa', '.sv', '.do',
                        '.br', '.pt', '.cu', '.pr', '.gq', '.eu', '.uk', '.fr', '.de', '.it', '.us', '.vn', '.io']

DOMINIOS_EXTRANJEROS_EXACTOS = [
    'marca.com', 'lavanguardia.com', 'elconfidencial.com', 'elperiodico.com', 'elespanol.com', 'okdiario.com',
    'libertaddigital.com', 'mundodeportivo.com', 'eltiempo.com', 'semana.com', 'eluniverso.com',
    'elnuevodia.com', 'prensalibre.com', 'laprensagrafica.com', 'elperiodicomediterraneo.com', 'hsbnoticias.com', 'murciaplaza.com', 'dw.com', 'fomoera.com', 'hellpress.com', 'revistaespejo.com', 'tribunavalladolid.com', 'vanidades.com', 'capitalmadrid.com', 'tikr.com', 'tusbuenasnoticias.com'
]

SUBDOMINIOS_EXTRANJEROS = ['mx', 'pe', 'co', 'cl', 'uy', 'py', 've', 'ec', 'bo', 'cr', 'gt', 'hn', 'ni', 'sv',
                           'mexico', 'espana', 'colombia', 'peru', 'chile', 'venezuela', 'ecuador', 'bolivia',
                           'uruguay', 'paraguay', 'guatemala', 'honduras', 'nicaragua', 'panama', 'elsalvador', 'costarica']
PORTALES_EXTRANJEROS_KEYWORDS = ['investing.com espana', 'es.investing.com', 'profeco', 'peru retail', 'peru-retail', 'luz noticias', 'luznoticias', 'milenio', 'el universal mexico', 'el comercio peru', 'larepublica.pe', 'infobae colombia', 'infobae mexico', 'infobae peru', 'infobae espana', 'tikr.com']

RUTAS_EXTRANJERAS_KEYWORDS = [
    '/colombia/', '/mexico/', '/peru/', '/espana/', '/venezuela/',
    '/ecuador/', '/chile/', '/bolivia/', '/uruguay/', '/paraguay/',
    '/guatemala/', '/honduras/', '/nicaragua/', '/panama/', '/elsalvador/',
    '/dominicana/', '/puertorico/', '/america/colombia/', '/america/mexico/',
    '/america/peru/', '/america/espana/', '/america/venezuela/',
    '/es-es/', '/es_es/', '/es-mx/', '/es_mx/', '/es-co/', '/es_co/', '/es-cl/', '/es_cl/', '/es-pe/', '/es_pe/',
    '/es-uy/', '/es_uy/', '/es-ve/', '/es_ve/', '/es-ec/', '/es_ec/', '/es-bo/', '/es_bo/', '/es-py/', '/es_py/'
]

SECCIONES_DIRECTAS_KEYWORDS = ['exclusiva', 'exclusivas', 'competencia', 'mencion', 'menciones', 'corporativo', 'snacking', 'pet nutrition']

CLIENTES_CONFIG = { 
    "MSD Salud Animal": {
        "color_primario": "#006E74",
        "hoja_excel": "MSD",
        "temas_excluir": [],  # Temas/palabras a excluir en TODAS las secciones de este cliente
        "banner_principal_local": "banners/principal.jpg",
        "banner_principal_url": "https://drive.google.com/file/d/1uT1al-u7cCEG-Q6oiay52GIdwnj2OKM5/view",
        "secciones": [
            {
                "id": "exclusivas", "nombre": "Exclusivas", "nombre_largo": "Exclusivas (MSD Salud Animal)",
                "img_local": "banners/exclusivas.jpg", "img_url": "https://drive.google.com/file/d/1cUyr83JrnQIo0XqMFltpoQkbuskaN41C/view", 
                "rss": ["https://news.google.com/rss/search?q=MSD%20Salud%20Animal%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
                "https://news.google.com/rss/search?q=Walter%20Comas%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
                "https://news.google.com/rss/search?q=Clara%20Fern%C3%A1ndez%20Boglione%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
                "https://news.google.com/rss/search?q=Pablo%20Nervi%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
                "https://news.google.com/rss/search?q=Eugenia%20Sanz%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], 
                "keywords": ["MSD Salud Animal", "MSD", "Walter Comas", "Clara Fernández Boglione", "Pablo Nervi", "Emiliano Segurado", "Eugenia Sanz"], "exclusiones": [], "limite": 20
            },
            {
                "id": "ceo", "nombre": "CEO", "nombre_largo": "CEO",
                "img_local": "banners/ceo.jpg", "img_url": "https://drive.google.com/file/d/1IH8MranbZnd_R--Nz5JZFbxbg3kDTfBB/view", 
                "rss": ["https://news.google.com/rss/search?q=CEO%20-futbol%20-deportes%20ARG%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], 
                "keywords": ["ceo", "CEO", "entrevista", "Entrevista", "ENTREVISTA", "Chief Ejecutive Officer", "Director Ejecutivo", "en dialogo"], "exclusiones": ["fútbol", "futbol", "partido", "dt ", "boca", "river", "racing", "independiente", "san lorenzo", "champions", "tenis", "nba", "rugby", "goles", "gol ", "estadio", "scaloni", "actor", "actriz", "película", "pelicula", "cine", "teatro", "recital", "cantante", "música", "musica", "farándula", "gran hermano", "reality", "asesinato", "crimen"], "limite": 10,
                "contexto_ia": "El interés es estrictamente sobre entrevistas, declaraciones o frases textuales de cualquier CEO, Presidente o Director de empresas operando en Argentina (no es obligatorio que sea de MSD). NO incluir notas que solo anuncien designaciones o cambios de puesto sin testimonios o dichos."
            },
            {
                "id": "salud", "nombre": "Salud Animal", "nombre_largo": "Salud Animal",
                "img_local": "banners/salud.jpg", "img_url": "https://drive.google.com/file/d/1Uc5WOsfk6kPBTncXsb6b7qOQlX3guYhz/view", 
                "rss": ["https://news.google.com/rss/search?q=zoonosis%20ARG%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
                "https://news.google.com/rss/search?q=hantavirus%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
                "https://news.google.com/rss/search?q=triquinosis%20ARG%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
                "https://news.google.com/rss/search?q=%22bienestar%20animal%22%20ARG%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
                "https://news.google.com/rss/search?q=%22salud%20animal%22%20ARG%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
                "https://news.google.com/rss/search?q=ARG%20gripe%20aviar%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], 
                "keywords": ["gripe aviar", "zoonosis", "hantavirus", "triquinosis", "veterinaria", "salud animal", "humano", "humanos", "Biogénesis Bagó"], "exclusiones": ["pediatría", "hospital municipal", "paro médico", "prepaga", "ioma", "pami", "estética humana"], "limite": 10,
                "contexto_ia": "El interés es sobre enfermedades transmitidas de animales a humanos (zoonosis) y novedades de la industria veterinaria en general. EXCLUIR notas cuyo foco principal sean las mascotas o animales de compañía."
            },
            {
                "id": "mascotas", "nombre": "Animales de Compañía", "nombre_largo": "Animales de Compañía / Mascotas",
                "img_local": "banners/mascotas.jpg", "img_url": "https://drive.google.com/file/d/1-zviGD1bM6e5493pKhUntxGXVQTquj5z/view", 
                "rss": ["https://news.google.com/rss/search?q=AR%20mascotas%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
                "https://news.google.com/rss/search?q=AR%20perros%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
                "https://news.google.com/rss/search?q=AR%20gatos%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=AR%20animales%20de%20compa%C3%B1%C3%ADa%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], 
                "keywords": ["Mascotas", "Perros", "Perro", "Gato", "Gatos", "Animales de compañía", "canino", "felino"], "exclusiones": ["ballena", "delfín", "tiburón", "fauna silvestre", "zoológico", "zoo ", "matt damon", "actor", "actriz", "película", "pelicula", "cine", "hollywood", "famosos", "farándula", "gran hermano", "reality", "hugo sigman", "insud", "diputado", "senador"], "limite": 15,
                "contexto_ia": "El interés es EXCLUSIVAMENTE sobre mascotas (perros y gatos domésticos)."
            },
            {
                "id": "aves", "nombre": "Aves", "nombre_largo": "Aves",
                "img_local": "banners/aves.jpg", "img_url": "https://drive.google.com/file/d/1xxWwhur4zqeiH5OyH11LtVa-nqH-Bvfp/view", 
                "rss": ["https://news.google.com/rss/search?q=avicultura%20ARG%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=%22granjas%20av%C3%ADcolas%22%20ARG%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=produccion%20avicola%20ARG%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=gallinas%20huevos%20produccion%20ARG%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], 
                "keywords": ["Aves", "Avicultura", "Avícola", "avícolas", "huevo", "huevos", "gallina", "gallinas", "granjas avícolas"], "exclusiones": ["dinosaurio", "fósil", "cóndor", "fauna silvestre", "avión", "aerolíneas", "vuelo"], "limite": 10,
                "contexto_ia": "El interés es sobre avicultura, granjas avícolas, gallinas, pollos, y la producción o consumo de huevos/carne aviar en Argentina."
            },
            {
                "id": "cerdos", "nombre": "Cerdos", "nombre_largo": "Cerdos",
                "img_local": "banners/cerdos.jpg", "img_url": "https://drive.google.com/file/d/1vvV1SK4Vf0Y6Zijn_9pOIfQbZV11Gw-v/view", 
                "rss": ["https://news.google.com/rss/search?q=cerdos%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=porcino%20ARG%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=porcina%20ARG%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], 
                "keywords": ["Cerdos", "Cerdas", "Porcino", "Porcina"], "exclusiones": ["actor", "actriz", "farándula", "película", "cine"], "limite": 10,
                "contexto_ia": "El interés es sobre porcicultura, producción y consumo de cerdos en Argentina, y enfermedades porcinas que NO se transmiten a humanos."
            },
            {
                "id": "ganaderia", "nombre": "Ganadería", "nombre_largo": "Ganadería",
                "img_local": "banners/ganaderia.jpg", "img_url": "https://drive.google.com/file/d/1JglW_UjMe-Lzqc7nxA1Ws776gVqXPI08/view", 
                "rss": ["https://news.google.com/rss/search?q=ganaderia%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=Tecnovax%20ARG%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=bovino%20ARG%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=feedlot%20ARG%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=vacas%20ganado%20ARG%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], 
                "keywords": ["Ganadería", "Ganadero", "Bovino", "Ganado", "vacas", "vaca", "feedlot", "feedlots", "tecnovax", "lechería", "leche", "brucelosis", "tuberculosis", "aftosa",], "exclusiones": ["actor", "actriz", "farándula", "película", "cine", "fútbol", "Vaca Muerta"], "limite": 20,
                "contexto_ia": "El interés es sobre ganadería bovina, lechería, tambos, producción y consumo de carne vacuna, y enfermedades bovinas que NO se transmiten a humanos."
            },
            {
                "id": "innovacion", "nombre": "Innovación en Salud Animal", "nombre_largo": "Innovación en Salud Animal",
                "img_local": "banners/innovacion.jpg", "img_url": "https://drive.google.com/file/d/1A6JsKrwszGa5UQaxtE-fOda1gleA9jP9/view", 
                "rss": ["https://news.google.com/rss/search?q=%22innovacion%20animal%22%20ARG%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=%22tecnologia%20veterinaria%22%20ARG%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=%22biotecnologia%20animal%22%20ARG%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], 
                "keywords": ["Innovación", "tecnología veterinaria", "biotecnología animal"], "exclusiones": ["actor", "farándula", "cine"], "limite": 5
            }
        ]
    },
    "Mars": {
        "color_primario": "#0000FF", "hoja_excel": "Mars", "temas_excluir": [], "banner_principal_local": "banners/mars_principal.jpg", "banner_principal_url": "https://drive.google.com/file/d/1pi3-8vZ-xr9p0AVR8tZmLaknj2kuhY7W/view",
        "secciones": [
            { "id": "mars_exclusivas", "nombre": "Exclusivas", "nombre_largo": "Banner Separador Exclusivas", "img_local": "banners/mars_exclusivas.jpg", "img_url": "https://drive.google.com/file/d/1tOcO3nn8Dsa55rldjciutv5cFr0h_VNP/view", "es_separador": True, "rss": [], "keywords": [], "exclusiones": [], "limite": 0 },
            { "id": "mars_tema_1", "nombre": "Corporativo", "nombre_largo": "Corporativo", "img_local": "banners/mars_corporativo.jpg", "img_url": "https://drive.google.com/file/d/1Vb7xaz32_V2lphPsAdJELhzPqeSERLJY/view", "rss": ["https://news.google.com/rss/search?q=AR%20Mars%20South%20Latam%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=Mars%20South%20Latam%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=Mars%20Petcare%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=AR%20Mars%20Petcare%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=Romina%20Ferreyra%20ARG%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=Mattia%20Iannone%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=Mar%C3%ADa%20No%C3%ABl%20Travetto%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419","https://news.google.com/rss/search?q=Guadalupe%20P%C3%A9rez%20Torelli%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], 
            "keywords": ["Mars", "South", "Latam", "Mars South Latam", "Romina Ferreyra", "Mattia Iannone", "María Noël Travetto", "Guadalupe Pérez Torelli"], "exclusiones": ["marte", "veronica mars", "bruno mars", "Jared Leto", "30 seconds to mars", "profeco", "mexico", "peru"], "limite": 20 },
            { "id": "mars_tema_2", "nombre": "Pet Nutrition", "nombre_largo": "Pet Nutrition", "img_local": "banners/mars_petnutrition.jpg", "img_url": "https://drive.google.com/file/d/1gayVCjqbhHsrPvm6XqO4jWFifqixT0gh/view", "rss": ["https://news.google.com/rss/search?q=AR%20Mars%20Petcare%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=Mars%20Petcare%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=Guadalupe%20P%C3%A9rez%20Torelli%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=Whiskas%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=Pedigree%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["Pedigree", "Whiskas", "Guadalupe Perez Torelli", "Mars Petcare"], "exclusiones": ["marte", "veronica mars", "bruno mars", "Jared Leto", "30 seconds to mars", "profeco", "mexico", "peru"], "limite": 20 },
            { "id": "mars_tema_3", "nombre": "Snacking", "nombre_largo": "Snacking", "img_local": "banners/mars_snacking.jpg", "img_url": "https://drive.google.com/file/d/1ji-Jx3hf4XKQbxl013c84Hhaezri3Wj-/view", "rss": ["https://news.google.com/rss/search?q=AR%20Mars%20Snacking%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["Mars", "Snacking", "Mars Snacking"], "exclusiones": ["marte", "veronica mars", "bruno mars", "Jared Leto", "30 seconds to mars", "profeco", "mexico", "peru"], "limite": 20 },
            { "id": "mars_competencia", "nombre": "Competencia", "nombre_largo": "Competencia", "img_local": "banners/mars_competencia.jpg", "img_url": "https://drive.google.com/file/d/1xTP21p0Xd8fbr9sSqZ8I1ON8FBy2Qovz/view", "rss": ["https://news.google.com/rss/search?q=Wouu%20OR%20%22Nestl%C3%A9%20purina%22%20OR%20Alican%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=%22Royal%20Canin%22%20OR%20Eukanuba%20OR%20Purina%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=Vitalcan%20OR%20Metrive%20OR%20Sieger%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=%22Agroindustrias%20Baires%22%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=AR%20%22Alimento%20mascota%22%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["Wouu", "Nestlé", "Alican", "Bacan", "Purina", "Mon Ami", "Metrive", "Eukanuba", "Royal Canin", "Vitalcan", "Sieger", "Agroindustrias Baires", "Dogrun", "Old Prince", "Fawna", "Kongo"], "exclusiones": ["cafe"], "limite": 20 },
            { "id": "mars_interes", "nombre": "Noticias de Interés", "nombre_largo": "Noticias de interés", "img_local": "banners/mars_interes.jpg", "img_url": "https://drive.google.com/file/d/1U6reL2Cj2o6XhbHB8nmssoLqYNyIJulK/view", "rss": ["https://news.google.com/rss/search?q=AR%20consumo%20OR%20inflaci%C3%B3n%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=AR%20perros%20OR%20gatos%20OR%20mascotas%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=Alimento%20de%20mascota%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["consumo", "consumo masivo", "industria alimenticia", "supermercados", "inflación", "pobreza", "alimentos", "mascotas", "perro", "perros", "gato", "gatos", "nutrición animal", "nutrición de animales", "WSAVA"], "exclusiones": ["PBI", "drogas", "cocaína", "marihuana", "alcohol", "carne", "vacuna", "vacuno", "porcino", "aviar", "profeco", "mexico", "peru", "huevo", "huevos"], "limite": 20 }
        ]
    },
    "BMS": {
        "color_primario": "#1A4FB5", "hoja_excel": "BMS", "temas_excluir": ["hormonas de crecimiento", "adermicina"], #Temas a excluir
        "banner_principal_local": "banners/bms_principal.jpg", "banner_principal_url": "https://drive.google.com/file/d/1ruuvwWkVLVgu-ZJJ6wwEPF8S6snh5mUX/view",
        "secciones": [
            { "id": "bms_tema_1", "nombre": "Exclusivas", "nombre_largo": "Exclusivas", "img_local": "banners/bms_exclusivas.jpg", "img_url": "https://drive.google.com/file/d/1ZYHx7jQfemxr2S4g5crIpaGdDgJtXQds/view", "rss": [
            "https://news.google.com/rss/search?q=Bristol%20Myers%20Squibb%20OR%20Bristol%20Myers%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=AR%20Bristol%20Myers%20Squibb%20OR%20Bristol%20Myers%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=Silvana%20Kurkdjian%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=AR%20Silvana%20Kurkdjian%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=ipilimumab+OR+Opdivo+OR+nivolumab+when:1d&hl=es-419&gl=AR&ceid=AR:es-419",
            "https://news.google.com/rss/search?q=Sotyktu+OR+deucravacitinib+OR+mavacamten+when:1d&hl=es-419&gl=AR&ceid=AR:es-419",
            "https://news.google.com/rss/search?q=Camzyos+OR+abatacept+OR+Orencia+when:1d&hl=es-419&gl=AR&ceid=AR:es-419",
            "https://news.google.com/rss/search?q=belatacept+OR+Nulojix+OR+daclatasvir+when:1d&hl=es-419&gl=AR&ceid=AR:es-419",
            "https://news.google.com/rss/search?q=Daklinza+OR+entecavir+OR+Baraclude+when:1d&hl=es-419&gl=AR&ceid=AR:es-419"
            ], 
            "keywords": ["Bristol", "Bristol-Myers", "Bristol Myers", "Bristol Myers Squibb", "Bristol-Myers Squibb", "BMS", "opdivo", "nivolumab", "Sotyktu", "deucravacitinib", "mavacamten", "Camzyos", "abatacept", "Orencia", "belatacept", "Nulojix", "daclatasvir", "Daklinza", "daclatasvir", "Daklinza", "entecavir", "Baraclude", "Silvana Kurkdjian"], "exclusiones": ["parkinson"], "limite": 20 },
            { "id": "bms_tema_2", "nombre": "Noticias del Sector", "nombre_largo": "Noticias del Sector", "img_local": "banners/bms_noticiasdelsector.jpg", "img_url": "https://drive.google.com/file/d/1FhuuaWsEr2ywBp_QzKGuvwZOm1W6gekK/view", "rss": [
            "https://news.google.com/rss/search?q=AR%20CILFA%20OR%20ANEFITS%20OR%20Medicamentos%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", #AR
            "https://news.google.com/rss/search?q=AR%20%22Obras%20sociales%22%20OR%20%22Mario%20Lugones%22%20OR%20%22Ministerio%20de%20Salud%22%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", #AR
            "https://news.google.com/rss/search?q=AR%20Prepagas%20OR%20Farma%20OR%20Farmac%C3%A9uticas%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", #AR
            "https://news.google.com/rss/search?q=AR%20%22Laboratorios%20farmac%C3%A9uticos%22%20OR%20%22IA%20Salud%22%20OR%20%22I%2BD%20farmac%C3%A9utica%22%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", #AR
            "https://news.google.com/rss/search?q=Gen%C3%A9ricos%20OR%20UIA%20OR%20CAEME%20OR%20%22Sistema%20de%20salud%22%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419" #global
            ],
            "keywords": ["CILFA", "ANEFITS", "obras sociales", "Mario Lugones", "Ministerio de Salud", "prepagas", "farma", "farmacéuticas", "farmacéuticos", "laboratorios farmacéuticos", "IA", "I+D farmacéutica", "genéricos", "UIA", "CAEME", "sistema de salud"], "exclusiones": ["PAMI", "patentes"], "limite": 15,
            "contexto_ia": "El interés es sobre notas relacionadas a las keywords que se encuentran enlistadas. REGLA ESTRICTA: La nota debe tratar sobre el sector salud/farmacéutico nacional. Rechazar policiales aislados, accidentes o casos clínicos individuales." },
            { "id": "bms_tema_3", "nombre": "Propiedad Intelectual / Biosimilares", "nombre_largo": "Propiedad Intelectual / Biosmilares", "img_local": "banners/bms_propiedadintelectualbiosimilares.jpg", "img_url": "https://drive.google.com/file/d/12A4oDRQ7BlmY_zop1a0ThahV1JOFQ8vk/view", 
            "rss": [
            "https://news.google.com/rss/search?q=Biosimilares+OR+Patentes+OR+PCT+when:1d&hl=es-419&gl=AR&ceid=AR:es-419"
            ], 
            "keywords": ["biosimilares", "patentes", "farmacéuticas", "PCT"], "exclusiones": ["autos", "parkinson"], "limite": 10 },
            { "id": "bms_tema_4", "nombre": "Competencia", "nombre_largo": "Competencia", "img_local": "banners/bms_competencia.jpg", "img_url": "https://drive.google.com/file/d/1rZfcOHZGfwsk40-L8Ti0fIlp6z6spM9G/view", 
            "rss": [ #mayoria de busquedas en AR
            "https://news.google.com/rss/search?q=Elea+OR+%22Laboratorio+Bag%C3%B3%22+OR+Bayer+-Leverkusen+-futbol+-champions+when:1d&hl=es-419&gl=AR&ceid=AR:es-419",
            "https://news.google.com/rss/search?q=AR%20Pfizer%20OR%20Sanofi%20OR%20Novartis%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=AR%20Roche%20OR%20AstraZeneca%20OR%20GSK%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=AR%20%22Novo%20Nordisk%22%20OR%20%22Boehringer%20Ingelheim%22%20OR%20Teva%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=AR%20MSD%20OR%20Abbott%20OR%20Takeda%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=%22Eli+Lilly%22+OR+Roemmers+OR+Gador+when:1d&hl=es-419&gl=AR&ceid=AR:es-419",
            "https://news.google.com/rss/search?q=Casasco+OR+Baliarda+OR+Montpellier+when:1d&hl=es-419&gl=AR&ceid=AR:es-419",
            "https://news.google.com/rss/search?q=Raffo+OR+Bernab%C3%B3+OR+Andr%C3%B3maco+when:1d&hl=es-419&gl=AR&ceid=AR:es-419",
            "https://news.google.com/rss/search?q=Biosidus+OR+Richmond+OR+Temis+when:1d&hl=es-419&gl=AR&ceid=AR:es-419",
            "https://news.google.com/rss/search?q=Lostal%C3%B3+OR+Craveri+OR+Finadiet+when:1d&hl=es-419&gl=AR&ceid=AR:es-419",
            "https://news.google.com/rss/search?q=AR%20Abbvie%20OR%20Genmab%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            ], 
            "keywords": ["Elea", "Laboratorios Bagó", "Laboratorios Bago", "Bayer", "Pfizer", "Sanofi", "Novartis", "Roche", "AstraZeneca", "GSK", "Novo Nordisk", "Boehringer Ingelheim", "Teva", "Merck", "MSD", "Abbott", "Takeda", "Eli Lilly", "Roemmers", "Gador", "Baliarda", "Montpellier", "Raffo", "Bernabó", "Andrómaco", "Biosidus", "Richmond", "Laboratorios Richmond" "Temis", "Lostaló", "Craveri", "Finadiet", "AbbVie", "Genmab"], 
            "exclusiones": ["Bayer Leverkusen", "Bayern", "fútbol", "futbol", "champions", "bundesliga", "goles", "jugador", "partido", "Xabi Alonso", "agri", "agricola", "cultivos", "agricultura", "semillas", "parkinson"], "limite": 10,
            "contexto_ia": "El interés es sobre los laboratorios listados. REGLA ESTRICTA: Las noticias deben estar focalizadas en noticias en las que se hable sobre algun laboratorio enlistado, ya sean medicamentos, vacunas, campañas o pases corporativos. Rechazar noticias de filiales, inversiones o lanzamientos exclusivos en otros países (ej. España, México, Europa, EEUU)." },
            { "id": "bms_tema_5", "nombre": "Areas Terapeuticas", "nombre_largo": "Áreas Terapéuticas", "img_local": "banners/bms_areasterapeuticas.jpg", "img_url": "https://drive.google.com/file/d/1HXv0m__Xixd0NgE607eAWrVXFT73Xdy2/view", "es_separador": True, "rss": [], "keywords": [], "exclusiones": [], "limite": 0 },
            { "id": "bms_tema_6", "nombre": "Onco-Hematologia", "nombre_largo": "Onco-Hematologia", "img_local": "banners/bms_oncohematologia.jpg", "img_url": "https://drive.google.com/file/d/1o8SGZMYZSZSsxqcYCZKPEhwWAh9T8sVx/view", 
            "rss": [
            "https://news.google.com/rss/search?q=AR%20C%C3%A1ncer%20OR%20oncolog%C3%ADa%20OR%20Onco-hematologia%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=AR%20Linfoma%20OR%20Tumor%20OR%20%22Octubre%20Rosa%22%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=AR%20Lalcec%20OR%20FUCA%20OR%20Macma%20OR%20AAOC%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"
            ],
            "keywords": ["cáncer", "cancer", "cáncer de mama", "metástasis", "metastasis", "tumores", "tumor", "melanoma", "linfoma", "oncología", "linfoma", "octubre rosa", "lalcec", "Lalcec", "FUCA", "Macma", "AAOC"], "exclusiones": ["parkinson"], "limite": 10,
            "contexto_ia": "El interés es sobre avances médicos, tratamientos, tumores, linfomas y campañas de prevención del cáncer. REGLA ESTRICTA: Si la nota NO especifica un país explícitamente pero trata el tema médico, DEBE SER APROBADA. Solo rechazar si la noticia trata de regulaciones, sistemas de salud o estadísticas exclusivas de otros países (ej. hospitales de España)." },
            { "id": "bms_tema_7", "nombre": "CAR-T", "nombre_largo": "CAR-T", "img_local": "banners/bms_cart.jpg", "img_url": "https://drive.google.com/file/d/1B6Rt1GJRhH2opmm9vnmTaLrRu8vVS0dW/view", 
            "rss": [
            "https://news.google.com/rss/search?q=CAR-T+OR+%22terapia+g%C3%A9nica%22+OR+inmunoterapia+OR+linfocitos+when:1d&hl=es-419&gl=AR&ceid=AR:es-419"
            ], 
            "keywords": ["CAR-T", "CAR T", "inmunoterapia", "terapia génica", "linfocitos T", "células cancerosas"], "exclusiones": ["parkinson"], "limite": 10 },
            { "id": "bms_tema_8", "nombre": "Cardiología", "nombre_largo": "Cardiología", "img_local": "banners/bms_cardiologia.jpg", "img_url": "https://drive.google.com/file/d/1JtpFFXjYVcr-4nCyE_XaxLtfmobCp2_M/view", 
            "rss": [
            "https://news.google.com/rss/search?q=AR%20Cardiovascular%20OR%20Cardiolog%C3%ADa%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=AR%20%22Infarto%22%20OR%20%22Insuficiencia%20card%C3%ADaca%22%20OR%20%22Arritmia%22%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", #AR
            "https://news.google.com/rss/search?q=AR%20%22Fibrilaci%C3%B3n%20auricular%22%20OR%20%22Hipertensi%C3%B3n%20arterial%22%20OR%20Cardiopat%C3%ADa%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", #AR
            "https://news.google.com/rss/search?q=AR%20%22Angina%20de%20pecho%22%20OR%20%22ACV%22%20OR%20Trombosis%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", #AR
            "https://news.google.com/rss/search?q=AR%20Aterosclerosis%20OR%20Colesterol%20OR%20Hipercolesterolemia%20OR%20miocardiopat%C3%ADa%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419" #AR
            ], 
            "keywords": ["ACV", "cardiología", "cardiologia", "cardiovascular", "salud cardiovascular", "enfermedades cardiovasculares", "corazón", "salud del corazón", "prevensión cardiovascular", "riesgo cardiovascular", "infarto", "infarto agudo de miocardio", "insuficiencia cardíaca", "arritmia", "Fibrilación auricular", "hipertensión arterial", "cardiopatía", "cardiopatía isquémica", "angina de pecho", "accidente cerebrovascular", "trombosis", "aterosclerosis", "colesterol", "hipercolesterolemia", "miocardiopatía", "presión arterial", "presion arterial", "cardíaco", "cardiaco", "infarto"], "exclusiones": [], "limite": 10,
            "contexto_ia": "El interés es sobre cardiología, afecciones cardiovasculares y prevención médica. REGLA ESTRICTA: Si la nota NO especifica un país explícitamente pero trata el tema médico, DEBE SER APROBADA. Solo rechazar si la noticia trata de regulaciones, sistemas de salud o estadísticas exclusivas de otros países." },
            { "id": "bms_tema_9", "nombre": "Artritis", "nombre_largo": "Artritis", "img_local": "banners/bms_artritis.jpg", "img_url": "https://drive.google.com/file/d/1qaHdfmIDmmgnDRj9VhJsU5qYuKw6B_ug/view", 
            "rss": [
            "https://news.google.com/rss/search?q=Artritis+OR+Artrosis+OR+%22Enfermedades+reum%C3%A1ticas%22+when:1d&hl=es-419&gl=AR&ceid=AR:es-419",
            "https://news.google.com/rss/search?q=Reumatolog%C3%ADa+OR+%22Salud+articular%22+OR+Articulaciones+when:1d&hl=es-419&gl=AR&ceid=AR:es-419",
            "https://news.google.com/rss/search?q=Osteoartritis+OR+Espondiloartritis+OR+%22Artritis+reactiva%22+when:1d&hl=es-419&gl=AR&ceid=AR:es-419"
            ], 
            "keywords": ["artritis", "articulaciones", "enfermedades reumáticas", "enfermedad reumática", "reuma", "artrotis", "reumatología", "salud articular", "enfermedades articulares", "dolor articular", "inflamación articular", "artritis reumatoide", "artritis psoriásica", "osteoartritis", "artritis idiopática juvenil", "espondiloartritis", "artritis reactiva", "gota"], "exclusiones": ["parkinson"], "limite": 10,
            "contexto_ia": "El interés es sobre artritis, artrosis, enfermedades reumáticas y prevención. REGLA ESTRICTA: Si la nota NO especifica un país explícitamente pero trata el tema médico, DEBE SER APROBADA. Solo rechazar si la noticia trata de regulaciones, sistemas de salud o estadísticas exclusivas de otros países." },
            { "id": "bms_tema_10", "nombre": "Psoriasis", "nombre_largo": "Psoriasis", "img_local": "banners/bms_psoriasis.jpg", "img_url": "https://drive.google.com/file/d/1VEZeFSymEKe5vHrNKLD08419502G_nqH/view", 
            "rss": [
            "https://news.google.com/rss/search?q=psoriasis+OR+%22Enfermedad+psori%C3%A1sica%22+OR+%22Salud+de+la+piel%22+when:1d&hl=es-419&gl=AR&ceid=AR:es-419"
            ], 
            "keywords": ["psoriasis", "enfermedad psoriásica", "psoriasis crónica", "salud de la piel"], "exclusiones": ["parkinson"], "limite": 10,
            "contexto_ia": "El interés es sobre psoriasis, enfermedades psoriásicas y tratamientos. REGLA ESTRICTA: Si la nota NO especifica un país explícitamente pero trata el tema médico, DEBE SER APROBADA. Solo rechazar si la noticia trata de regulaciones, sistemas de salud o estadísticas exclusivas de otros países." },
            { "id": "bms_tema_11", "nombre": "Trasplante", "nombre_largo": "Trasplante", "img_local": "banners/bms_trasplante.jpg", "img_url": "https://drive.google.com/file/d/1pHzriblnIvQl44uQrooGJXI4qGIE_YLU/view", 
            "rss": [
            "https://news.google.com/rss/search?q=%22Donaci%C3%B3n+de+%C3%B3rganos%22+OR+%22Donaci%C3%B3n+de+tejidos%22+OR+Incucai+when:1d&hl=es-419&gl=AR&ceid=AR:es-419",
            "https://news.google.com/rss/search?q=%22Procuraci%C3%B3n+de+%C3%B3rganos%22+OR+%22M%C3%A9dula+%C3%B3sea%22+OR+%22Ablaci%C3%B3n+de+%C3%B3rganos%22+OR+Trasplante+when:1d&hl=es-419&gl=AR&ceid=AR:es-419"
            ], 
            "keywords": ["trasplante", "trasplantes", "donación de órganos", "donacion de organos", "donación de tejidos", "tejidos", "incucai", "INCUCAI", "procuración de órganos", "médula ósea", "ablación de órganos", "trasplante"], "exclusiones": ["parkinson"], "limite": 10,
            "contexto_ia": "El interés es sobre trasplantes, donación y ablación de órganos. REGLA ESTRICTA: Si la nota NO especifica un país explícitamente pero trata el tema médico/donación, DEBE SER APROBADA. Solo rechazar explícitamente si se nombra una organización, en caso de donación de otro país distinto a Argentina o si se trata de un caso particular" }
        ]
    },
    "Arredo": {
        "color_primario": "#0000FF", "hoja_excel": "Arredo", "temas_excluir": [], "banner_principal_local": "banners/arredo_principal.jpg", "banner_principal_url": "https://drive.google.com/file/d/1MESH-P0uDrBHX83uNEstihGcH2eEC6UU/view",
        "secciones": [
            { "id": "arredo_tema_1", "nombre": "Exclusivas", "nombre_largo": "Exclusivas", "img_local": "banners/arredo_exclusivas.jpg", "img_url": "https://drive.google.com/file/d/18HsLa3b-kNOtgaR5YYxMlaUo6UvHpxJH/view", "rss": ["https://news.google.com/rss/search?q=Arredo%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["Arredo"], "exclusiones": [], "limite": 20 },
            { "id": "arredo_tema_2", "nombre": "Mención", "nombre_largo": "Menciones", "img_local": "banners/arredo_menciones.jpg", "img_url": "https://drive.google.com/file/d/19U90rGK_pWlKGssHxlYX9Zu-cQGoA4Ce/view", "rss": ["https://news.google.com/rss/search?q=Arredo%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["Arredo"], "exclusiones": [], "limite": 20 },
            { "id": "arredo_tema_3", "nombre": "Recursos Humanos", "nombre_largo": "Recursos Humanos", "img_local": "banners/arredo_recursoshumanos.jpg", "img_url": "https://drive.google.com/file/d/1zXnXWvMT-CKfFEgB2dbjqNZWtOvOCisQ/view", "rss": ["https://news.google.com/rss/search?q=Empleabilidad%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["empleabilidad", "inclusión laboral", "informalidad", "becas", "pasantías", "mejores empresas", "mejor empresa", "trabajar", "empleo", "derechos laborales", "mercado laboral", "liderazgo"], "exclusiones": [], "limite": 10 },
            { "id": "arredo_tema_4", "nombre": "Diversidad y Género", "nombre_largo": "Diversidad y Género", "img_local": "banners/arredo_diversidadygenero.jpg", "img_url": "https://drive.google.com/file/d/17P15vUG1zciLz_-j3sFKUax-nIpqAcsO/view", "rss": ["https://news.google.com/rss/search?q=AR%20Diversidad%20y%20g%C3%A9nero%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["mujeres", "inclusión", "mujeres", "mujeres emprendedoras", "mujeres profesionales", "violencia de género", "brecha salarial", "primer empleo", "empleo joven"], "exclusiones": [], "limite": 10 },
            { "id": "arredo_tema_5", "nombre": "Sustentabilidad", "nombre_largo": "Sustentabilidad", "img_local": "banners/arredo_sustentabilidad.jpg", "img_url": "https://drive.google.com/file/d/1WSuNM_EBYjj45-K2T-qtFtONuseJ7TCU/view", "rss": ["https://news.google.com/rss/search?q=AR%20Sustentabilidad%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["Empresa B", "sustentabilidad", "energía renovable", "reciclar", "reciclado", "economía circular"], "exclusiones": [], "limite": 10 },
            { "id": "arredo_tema_6", "nombre": "Competencia", "nombre_largo": "Competencia", "img_local": "banners/arredo_competencia.jpg", "img_url": "https://drive.google.com/file/d/1VxLJRHbvfqtOgLBWeVqGquFxnNX0-swx/view", "rss": ["https://news.google.com/rss/search?q=Home%20Collection%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=Duvet%20Home%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=Kavanagh%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=Landmark%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=AR%20%22Casablanca%22%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=Jean%20Cartier%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=%22Ad%20Home%22%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=%22Egger%22%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=H%26G%20Home%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=%22Alto%20Rancho%22%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=Franco%20Valente%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["Home Collection", "Duvet Home", "Kavanagh", "Landmark", "Indian", "Casablanca", "Jean Cartier", "Ad Home", "Egger", "H&G Home", "AltoRancho", "Franco Valente"], "exclusiones": [], "limite": 10 },
            { "id": "arredo_tema_7", "nombre": "Noticias de Interes", "nombre_largo": "Noticias de Interes", "img_local": "banners/arredo_noticiasdeinteres.jpg", "img_url": "https://drive.google.com/file/d/1rVjjNmlVdhJU2Ed7wJVV4wwhkqeF70rH/view", "rss": ["https://news.google.com/rss/search?q=industria%20textil%20ARG%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=inflaci%C3%B3n%20ARG%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["textil", "industria", "industria textil", "fabrica", "fabricas", "inflación", "pymes", "consumo", "pobreza", "dormir", "decoración", "ropa de cama", "hábitos de sueño", "ecommerce"], "exclusiones": [], "limite": 20 }
        ]
    },
    "Amanco Wavin": {
        "color_primario": "#000099", "hoja_excel": "Amanco", "temas_excluir": [], "banner_principal_local": "banners/amanco_principal.jpg", "banner_principal_url": "https://drive.google.com/file/d/1gFQAqAPm3xiGlDKM72Plr5fT19IF-5Z4/view",
        "secciones": [
            { "id": "amanco_tema_1", "nombre": "Exclusivas", "nombre_largo": "Exclusivas", "img_local": "banners/amanco_exclusivas.jpg", "img_url": "https://drive.google.com/file/d/1_vg5keIN7jMt7FCOFjGxgVNbXGxGnjOW/view", "rss": ["https://news.google.com/rss/search?q=Amanco%20Wavin%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=AR%20Amanco%20Wavin%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["Amanco Wavin"], "exclusiones": [], "limite": 20 },
            { "id": "amanco_tema_2", "nombre": "Competencia", "nombre_largo": "Competencia", "img_local": "banners/amanco_competencia.jpg", "img_url": "https://drive.google.com/file/d/1nQos7Azcml2O5DRZCD4Hfrs-xe5Mao8W/view", "rss": ["https://news.google.com/rss/search?q=FV%20OR%20Ferrum%20OR%20Rotoplas%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=%22DEMA%22%20OR%20Aqualaf%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=Awaduct%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"
            ], "keywords": ["FV", "Ferrum", "Rotoplas", "DEMA", "Duke", "Aqualaf", "AWADUCT", "Roca"], "exclusiones": [], "limite": 10 },
            { "id": "amanco_tema_3", "nombre": "Industria e Infraestructura", "nombre_largo": "Industria e Infraestructura", "img_local": "banners/amanco_industriaeinfraestructura.jpg", "img_url": "https://drive.google.com/file/d/1-6eOexICM6t-Iiro5dIUfP1WDSLxz7U6/view", "rss": [ "https://news.google.com/rss/search?q=AR%20prefabricada%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=ducha%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",  "https://news.google.com/rss/search?q=AR%20alba%C3%B1il%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=Camara%20argentina%20de%20la%20construcci%C3%B3n%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=CAMARCO%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=AR%20Infraestructura%20OR%20Oficios%20OR%20cloacas%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=AR%20%22mano%20de%20obra%22%20OR%20Rutas%20OR%20construir%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=AR%20inflaci%C3%B3n%20OR%20obras%20OR%20agua%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=AR%20riego%20OR%20plomero%20OR%20plomer%C3%ADa%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=AR%20ba%C3%B1o%20OR%20ba%C3%B1os%20OR%20h%C3%ADdricos%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=AR%20materiales%20OR%20%22Loma%20Negra%22%20OR%20%22cr%C3%A9dito%20hipotecario%22%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=AR%20aysa%20OR%20%22obra%20p%C3%BAblica%22%20OR%20%22construcci%C3%B3n%20modular%22%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=AR%20vivienda%20OR%20%22instalaciones%20sanitarias%22%20OR%20%22sistemas%20de%20tuber%C3%ADas%22%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=AR%20%22materiales%20de%20construcci%C3%B3n%22%20OR%20geosint%C3%A9ticos%20OR%20%22infraestructura%20vial%22%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=AR%20impermeabilizaci%C3%B3n%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["vivienda", "obra pública", "Infraestructura", "rutas", "construcción", "construir", "albañil", "inflación", "obras", "agua", "riego", "plomero", "plomería", "baño", "baños", "hídricos", "materiales", "Loma Negra", "prefabricada", "casa", "casas", "Aysa", "AySa", "Camarco", "Oficios", "cloacas", "mano de obra", "crédito hipotecario", "construcción modular", "instalaciones sanitarias", "sistemas de tuberías", "materiales de construcción", "geosintéticos", "infraestructura vial", "impermeabilización"], "exclusiones": ["rural", "sanitaria", "futbol"], "limite": 15 },
            { "id": "amanco_tema_4", "nombre": "Sustentabilidad", "nombre_largo": "Sustentabilidad", "img_local": "banners/amanco_sustentabilidad.jpg", "img_url": "https://drive.google.com/file/d/1ILvTnUcm-FF7lbWStCXUqYsRe8pyhxHB/view", "rss": ["https://news.google.com/rss/search?q=AR%20Sustentabilidad%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=AR%20%22uso%20eficiente%20del%20agua%22%20OR%20%22ahorro%20de%20agua%22%20OR%20reciclaje%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=AR%20%22El%20Ni%C3%B1o%22%20OR%20%22materiales%20reciclados%22%20OR%20%22productos%20sustentables%22%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=AR%20%22eficiencia%20de%20recursos%22%20OR%20%22gesti%C3%B3n%20de%20residuos%22%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["sustentable", "sustentabilidad", "sostenible", "Empresa B", "uso eficiente del agua", "ahorro de agua", "reciclaje", "El Niño", "materiales reciclados", "productos sustentables", "eficiencia de recursos", "gestión de residuos"], "exclusiones": [], "limite": 10 }
        ]
    },
    "Booking": {
        "color_primario": "#0000FF", "hoja_excel": "Booking", "temas_excluir": [], "banner_principal_local": "banners/booking_principal.jpg", "banner_principal_url": "https://drive.google.com/file/d/1TKf_eTU4sWBk_9pYG5iBI4r6CKA52Fz4/view",
        "secciones": [
            { "id": "booking_tema_1", "nombre": "Exclusivas", "nombre_largo": "Exclusivas", "img_local": "banners/booking_exclusivas.jpg", "img_url": "https://drive.google.com/file/d/1IkOGzUtBEw_TWkf5AgdWK4-5yXmCk5gf/view", "rss": ["https://news.google.com/rss/search?q=Booking%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=AR%20Booking%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=Booking.com%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=Booking%20Holding%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=Jimena%20Guti%C3%A9rrez%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=Traveller%20Review%20Awards%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["Booking", "Booking.com", "Booking Argentina", "Booking Holding", "Jimena Gutiérrez", "Traveller Review Awards",], "exclusiones": [], "limite": 20 },
            { "id": "booking_tema_2", "nombre": "Competencia", "nombre_largo": "Competencia", "img_local": "banners/booking_competencia.jpg", "img_url": "https://drive.google.com/file/d/1SD6Qf6FxN8lvIuwqiywS8hCThh5IGH4B/view", "rss": ["https://news.google.com/rss/search?q=AR%20Airbnb%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=%22Almundo%22%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=Turismocity%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=Tripadvisor%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=Expedia%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",            "https://news.google.com/rss/search?q=%22Despegar%22%20OR%20Paula%20Cristi%20when%3A10d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=%22Atr%C3%A1palo%22%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=Citavis%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["Airbnb", "Turismocity", "Almundo", "Tripadvisor", "TripAdvisor", "Expedia", "Despegar", "Atrápalo", "Citavis", ], "exclusiones": [], "limite": 20 },
            { "id": "booking_tema_3", "nombre": "Turismo", "nombre_largo": "Turismo", "img_local": "banners/booking_turismo.jpg", "img_url": "https://drive.google.com/file/d/1PVMiBHJuTBdm7YQn6OF1c9F31gvyckZR/view", "rss": ["https://news.google.com/rss/search?q=turismo%20site%3Ainfobae.com%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=turismo%20site%3Aclarin.com%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=turismo%20site%3Acronista.com%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=turismo%20site%3Alanacion.com.ar%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=turismo%20site%3Aambito.com%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=turismo%20site%3Aperfil.com%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=turismo%20site%3Atn.com.ar%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=turismo%20site%3Aiprofesional.com%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=turismo%20site%3Apagina12.com.ar%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=AR%20%22Turismo%22%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=AR%20%22Vacaciones%22%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=AR%20%22viajes%22%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["turismo", "plataforma de viajes", "alojamiento", "alquiler temporario", "destinos turísticos", "viajes", "tendencias de viaje", "viajes gastronómicos", "turismo sostenible", "estafas en viajes", "fin de semana largo", "destinos más buscados"], "exclusiones": ["jugadores", "jugador", "Lionel Scaloni", "futbol", "futbolista", "Messi", "selección", "famosos", "actor", "actriz", "romance", "novio", "novia", "farándula", "gran hermano", "teatro", "separación", "escándalo", "modelo", "cantante"], "limite": 20 }
        ]
    },
    "Mail Boxes": {
        "color_primario": "#0000FF", "hoja_excel": "Mail Boxes", "temas_excluir": [], "banner_principal_local": "banners/mailboxes_principal.jpg", "banner_principal_url": "https://drive.google.com/file/d/1TPWQwHYQaclaJ7G3jZjON8C-TddFHf37/view",
        "secciones": [
            { "id": "mailboxes_tema_1", "nombre": "Exclusivas", "nombre_largo": "Exclusivas", "img_local": "banners/mailboxes_exclusivas.jpg", "img_url": "https://drive.google.com/file/d/1BmHMJZe8BrRGyBxuqZZE7qyvXWWSp5aD/view", "rss": ["https://news.google.com/rss/search?q=%22Mail%20Boxes%22%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["Mail Boxes", "Mail Boxes Etc", "MBE"], "exclusiones": [], "limite": 20 },
            { "id": "mailboxes_tema_2", "nombre": "Competencia", "nombre_largo": "Competencia", "img_local": "banners/mailboxes_competencia.jpg", "img_url": "https://drive.google.com/file/d/1_5zAh9euq4ESEk3y6yVr4qwAB1Auk3WS/view", "rss": ["https://news.google.com/rss/search?q=Andreani%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=%22Correo%20Argentino%22%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=OCA%20env%C3%ADos%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=%22Fasttrack%20Argentina%22%20OR%20%22Aerobox%20Argentina%22%20OR%20%22Del%20Mundo%20Courier%22%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=%22DHL%20Argentina%22%20OR%20%22FedEx%20Argentina%22%20OR%20UPS%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=OCASA%20OR%20OCA%20OR%20%22Urbano%20Express%22%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=Lancioni%20OR%20%22Cruz%20del%20Sur%22%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["Andreani", "Correo Argentino", "OCA", "DHL", "FedEx", "UPS", "Fasttrack", "Aerobox", "Del Mundo Courier", "OCASA", "Urbano Express", "Lancioni", "Cruz del Sur"], "exclusiones": ["pickups", "Pick-ups", "vehiculos", "SUV", "up"], "limite": 20,
                "contexto_ia": "El interés es sobre noticias donde la empresa de mensajería/courier/correo/logística listada sea la PROTAGONISTA de la nota: sus servicios, tarifas, operaciones, sucursales, inversiones, tecnología, alianzas, compras o fusiones, conflictos gremiales, cambios regulatorios que la afecten, demoras o novedades de envíos. REGLA ESTRICTA: RECHAZAR homónimos y usos ajenos al negocio de envíos: UPS como equipo de energía/baterías, OCA como ave o sigla de otra organización, apellidos de personas, patrocinios deportivos (ej. FedEx Cup, DHL en deportes o automovilismo), empresas de transporte de pasajeros o turismo, y notas policiales, políticas o económicas donde la empresa solo se menciona de pasada." },
            { "id": "mailboxes_tema_3", "nombre": "Noticias de Interés", "nombre_largo": "Noticias de interés", "img_local": "banners/mailboxes_interes.jpg", "img_url": "https://drive.google.com/file/d/1NLuVTcB-z23LR_pm0GDj71J0TcaJzIYs/view", "rss": ["https://news.google.com/rss/search?q=courier%20env%C3%ADos%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=log%C3%ADstica%20e-commerce%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=AR%20%22Importaci%C3%B3n%20Argentina%22%20OR%20Exportaci%C3%B3n%20OR%20%22Desregulaci%C3%B3n%20aduaneras%22%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=AR%20%22Desregulaci%C3%B3n%20de%20transporte%22%20OR%20%22Comercio%20exterior%22%20OR%20%22Transporte%20de%20cargas%22%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=AR%20Log%C3%ADstica%20OR%20Courier%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["courier", "envíos", "logística", "e-commerce", "paquetería", "Importación", "Exportación", "Desregulación aduaneras", "Desregulación de transporte", "Comercio exterior", "Transporte de cargas"], "exclusiones": [], "limite": 20,
                "contexto_ia": "El interés es sobre eCommerce (compras online, tiendas y marketplaces, productos comprados por internet o al exterior), envíos y logística de paquetes, mensajería y courier, y transporte de cargas, siempre dentro del contexto de Argentina. REGLA ESTRICTA: la LOGÍSTICA solo interesa si se vincula con mensajería, courier, paquetería, eCommerce o transporte de cargas. Importación, exportación, aduana y comercio exterior solo interesan si afectan envíos, courier, compras online o logística de cargas (régimen de importación de paquetes, trabas o desregulaciones aduaneras, transporte de cargas). RECHAZAR: logística interna de fábricas o almacenes sin envíos ni eCommerce, logística sanitaria, militar o deportiva, transporte de pasajeros, aviación comercial o turismo, precios de combustibles sin vínculo a cargas, balanzas comerciales, precios o cosechas de commodities (soja, carne, etc.), política o economía general que solo mencione importación o exportación" },
        ]
    }
}

IDS_SINTESIS = ["exclusivas", "mars_tema_1", "mars_tema_2", "mars_tema_3", "bms_tema_1", "arredo_tema_1", "arredo_tema_2", "amanco_tema_1", "booking_tema_1", "mars_competencia", "bms_tema_4", "arredo_tema_6", "amanco_tema_2", "booking_tema_2", "mailboxes_tema_1", "mailboxes_tema_2"]  # v5.47
IDS_EXCLUSIVAS = ["exclusivas", "bms_tema_1", "arredo_tema_1", "amanco_tema_1", "booking_tema_1", "mailboxes_tema_1"]
MAX_NOTAS_POR_BUSQUEDA = 3  # v5.70
CLIENTES_SIN_TOPE_BUSQUEDA = ['Mars', 'MSD Salud Animal', 'Mail Boxes']  # v5.81: clientes sin tope por búsqueda (todas sus secciones)
SECCIONES_SIN_TOPE_BUSQUEDA = ['bms_tema_1', 'bms_tema_4', 'arredo_tema_1', 'arredo_tema_2', 'arredo_tema_6', 'booking_tema_1', 'booking_tema_2', 'amanco_tema_1', 'amanco_tema_2']  # v5.81: Exclusivas/Mención/Competencia
def limite_ajustado(limite, timeframe):  # v5.70: +5 a todos los límites; +5 más si la búsqueda es de 3 días o de toda la semana
    try: base = int(limite) + 5
    except Exception: return limite
    return base + (5 if timeframe == "3d" else (10 if timeframe in ("5d", "7d") else 0))  # v5.71: 3 días +5 extra; semana +10 extra
FEED_TERMINOS = {}  # v5.67: feed_id -> término de búsqueda (para el indicador de progreso)
IDS_EXCLUIR_TIER3 = ['amanco_tema_3']  # v5.66: secciones donde las notas Tier 3 se excluyen (agregar ids para sumar más)
IDS_SIN_METRICAS = ['mars_competencia', 'bms_tema_4', 'booking_tema_2', 'mailboxes_tema_2', 'arredo_tema_6']  # v5.58: Competencia sin métricas (se suma Arredo)
IDS_COMPETENCIA = ["mars_competencia", "bms_tema_4", "arredo_tema_6", "amanco_tema_2", "booking_tema_2", "mailboxes_tema_2"]

# ====================================================================
# MOTOR DE SCRAPING Y EXTRACCIÓN DE METADATA (FUNCIONES AUXILIARES)
# ====================================================================
def formatear_fecha(texto_fecha):
    try:
        if not texto_fecha: return ""
        dt = email.utils.parsedate_to_datetime(texto_fecha)
        return dt.strftime("%d/%m/%Y")
    except: return ""

def tipo_metricas(sec_id):  # v5.43: 'booking' (solo Ad Value), 'full' (Alcance/Tier/Ad Value) o 'none'
    if sec_id == 'booking_tema_1': return 'booking'
    if sec_id in IDS_SINTESIS and sec_id not in IDS_SIN_METRICAS: return 'full'
    return 'none'

def remover_acentos(texto): 
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def es_bloqueo_waf(texto):
    firmas = ["performing security verification", "attention required! | cloudflare", "403 forbidden", "access denied", "just a moment...", "error 1020"]
    return any(f in (texto or "").lower() for f in firmas)

def corregir_mojibake(texto):
    reemplazos = {'Ã¡': 'á', 'Ã©': 'é', 'Ã-': 'í', 'Ã³': 'ó', 'Ãº': 'ú', 'Ã±': 'ñ', 'Ã': 'Á', 'Ã‰': 'É', 'Ã': 'Í', 'Ã“': 'Ó', 'Ãš': 'Ú', 'Ã‘': 'Ñ'}
    for mal, bien in reemplazos.items(): texto = (texto or "").replace(mal, bien)
    return texto

def limpiar_titulo(t):
    if not t: return "Sin Título"
    t = re.sub(r'\s+[-|::]+\s+[^|:-]{1,35}$', '', t)
    return t.strip()
    

def limpiar_nombre_medio(medio):
    if not medio: return "Portal Argentino"
    texto = str(medio).strip()
    texto = re.sub(r'\.(com|net|org|info|gob|edu|tv)(\.[a-z]{2})?$', '', texto, flags=re.IGNORECASE)
    texto = re.sub(r'\.(ar|es|mx|cl|co|pe|uy|py)$', '', texto, flags=re.IGNORECASE)
    texto = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', texto)
    texto = texto.replace('-', ' ').replace('_', ' ')
    
    # Agregamos "somos", "radio", "salud" y "cure" al separador automático de prefijos
    texto = re.sub(r'^(el|la|los|las|diario|infobae|portal|noticias|somos|radio|salud|cure)(?=[a-z]{3,})', r'\1 ', texto, flags=re.IGNORECASE)
    texto = re.sub(r'\s+', ' ', texto).strip()
    texto_final = texto.title()
    
    # Reemplazos exactos forzados para los casos más rebeldes
    correcciones = {
        "Curecompass": "Cure Compass",
        "Somosjujuy": "Somos Jujuy",
        "Radiotucuman": "Radio Tucumán",
        "Saludnews24": "Salud News 24",
        "Agromeat": "Agro Meat",
        "Apea": "A.P.E.A.",
        "Bichosdecampo": "Bichos de Campo",
        "Es": "Esdairynews",
        "Sercampo": "Ser Campo",
        "Suenaacampo": "Suena a Campo",
        "Todolecheria": "Todo Lechería",
        "Marcelafittipaldi": "Marcela Fittipaldi",
        "InfoNegocios": "Info Negocios",
        "Vetcomunicaciones": "Vet Comunicaciones",
        "Tn": "TN",
        "Vetmarketportal": "Vet Market",
        "Bhinfo": "BH Info",
        "Norteenlinea": "Norte en Línea",
        "Forbesargentina": "Forbes Argentina",
        "Infonegocios": "Info Negocios",
        "Infocampo": "Info Campo",
        "Palabradecampo": "Palabra de Campo",
        "Saladillocampo": "Saladillo Campo",
        "Valorcarne": "Valor Carne",
        "Todojujuy": "Todo Jujuy",
        "Rtsmedios": "RTS Medios",
    }
    return correcciones.get(texto_final, texto_final)

def limpiar_basura_periodistica(texto):
    texto = texto or ""
    texto = re.sub(r'(http[s]?://\S+|www\.\S+)', '', texto, flags=re.IGNORECASE)
    for p in [r'Añadir .*? a tus preferidos en Google', r'Seguinos en .*', r'PUBLICIDAD', r'\d{1,2}/\d{1,2}/\d{2,4}\s*\|\s*\d{1,2}:\d{2}']:
        texto = re.sub(p, '', texto, flags=re.IGNORECASE)
        
    return " ".join(texto.split())

def url_limpia_para_duplicados(url):
    if not url: return ""
    u = url.lower().strip()
    u = u.split('?')[0].split('#')[0]
    u = re.sub(r'^https?://', '', u)
    u = re.sub(r'^www\.', '', u)
    u = u.rstrip('/')
    return u

def contiene_palabra_clave(texto, palabras_clave):
    if not palabras_clave: return True
    texto_limpio = re.sub(r'(http[s]?://\S+|www\.\S+)', '', (texto or ""), flags=re.IGNORECASE)
    t_norm = remover_acentos(texto_limpio.lower())
    return any(re.search(r'\b' + re.escape(remover_acentos(k.lower())) + r'\b', t_norm, re.IGNORECASE) for k in palabras_clave)

def contiene_exclusion(texto, exclusiones):
    if not exclusiones: return False
    texto_limpio = re.sub(r'(http[s]?://\S+|www\.\S+)', '', (texto or ""), flags=re.IGNORECASE)
    t_norm = remover_acentos(texto_limpio.lower())
    return any(re.search(r'\b' + re.escape(remover_acentos(ex.lower())) + r'\b', t_norm, re.IGNORECASE) for ex in exclusiones)

def evaluar_relevancia_ia_lotes(lote_notas, cliente_nombre, nombre_seccion, palabras_clave, exclusiones, logger=None, contexto_ia=""):
    if not lote_notas: return {}
    
    try:
        kws = ", ".join(palabras_clave) if palabras_clave else "sin palabras clave específicas"
        excl = ", ".join(exclusiones) if exclusiones else "ninguna"
        
        prompt = (f'Sos un analista de prensa. Cliente: "{cliente_nombre}". Sección: "{nombre_seccion}".\n'
                  f'Palabras clave de interés: {kws}.\n'
                  f'Temas que NO le interesan: {excl}.\n')
        
        if contexto_ia:
            prompt += f'REGLA ESTRICTA PARA ESTA SECCIÓN: {contexto_ia}\n\n'
            
        prompt += (f'Evaluá las siguientes {len(lote_notas)} notas numeradas. Confirmá si el TEMA general de cada nota '
                   f'realmente se relaciona con el interés del cliente.\n'
                   f'Respondé EXACTAMENTE con este formato para cada nota (un renglón por nota):\n'
                   f'0: SI\n'
                   f'1: NO: [motivo breve de 1 frase del por qué no aplica]\n\n'
                   f'Notas a evaluar:\n')
                   
        for item in lote_notas:
            texto_reducido = item['texto'][:600].replace('\n', ' ')
            prompt += f"{item['id']}: {texto_reducido}\n"
            
        resp = llamar_groq({"model": "openai/gpt-oss-20b", "messages": [{"role": "user", "content": prompt}],
                            "temperature": 0, "max_tokens": 400, "reasoning_effort": "low"}, timeout=25, logger=logger, cliente=cliente_nombre)
        resultado_crudo = resp.json()["choices"][0]["message"]["content"].strip()
        if logger: logger(f"    🤖 IA analizó bloque de {len(lote_notas)} notas juntas.")
        
        resultados = {}
        for linea in resultado_crudo.split('\n'):
            linea = linea.strip()
            if not linea: continue
            match = re.search(r'^(\d+)[:\.-]?\s*(SI|NO)(?:[:\s]+(.*))?', linea, re.IGNORECASE)
            if match:
                n_id = match.group(1)
                es_si = match.group(2).upper() == 'SI'
                motivo = match.group(3).strip() if match.group(3) else ("Tema no alineado." if not es_si else "Relevante")
                resultados[n_id] = (es_si, motivo)
        
        for item in lote_notas:
            if str(item['id']) not in resultados:
                resultados[str(item['id'])] = (True, "Aprobada por fallback (IA no retornó ID)")
        return resultados
    except Exception as e:
        if logger: logger(f"    ⚠️ Filtro IA Lotes falló ({e}). Se conservan por defecto.")
        return {str(item['id']): (True, "Filtro IA no disponible") for item in lote_notas}

_ABREVIATURAS = ['Sr.', 'Sra.', 'Dr.', 'Dra.', 'Lic.', 'Ing.', 'Prof.', 'Gral.', 'Av.', 'Cía.', 'EE.UU.', 'S.A.']
def _proteger_abreviaturas(texto):
    for abr in _ABREVIATURAS: texto = re.sub(re.escape(abr), abr.replace('.', '∎'), texto, flags=re.IGNORECASE)
    return texto
def _restaurar_abreviaturas(texto): return texto.replace('∎', '.')

def extraer_oracion_clave(texto, palabras_clave, sec_id=""):
    texto_limpio = _proteger_abreviaturas(re.sub(r'([^\.\!\?])\s*\n+\s*', r'\1 ', limpiar_basura_periodistica(texto)))
    oraciones = [_restaurar_abreviaturas(o) for o in re.split(r'(?<=[.!?])\s+', texto_limpio)]
    patron = "|".join(r'\b' + re.escape(k) + r'\b' for k in sorted(palabras_clave, key=len, reverse=True)) if palabras_clave else ""
    
    for oracion in oraciones:
        if len(oracion.strip()) >= 15 and contiene_palabra_clave(oracion, palabras_clave):
            o = oracion.strip()
            if len(o) > 2000:  # v5.40: oraciones larguísimas (listas de participantes): recorte alrededor de la keyword
                m = re.search(patron, o, flags=re.IGNORECASE) if patron else None
                if m:
                    ini, fin = max(0, m.start() - 300), min(len(o), m.end() + 300)
                    o = ("…" if ini else "") + o[ini:fin] + ("…" if fin < len(o) else "")
                else:
                    o = o[:2000]
            if patron:
                if str(sec_id) in ("booking_tema_1", "booking_tema_2"):  # v5.44: Booking: keywords en rojo estándar, sin negrita
                    return re.sub(f"({patron})", r'<span style="color: #FF0000; font-weight: normal;">\1</span>', o, flags=re.IGNORECASE)
                return re.sub(f"({patron})", r"<strong>\1</strong>", o, flags=re.IGNORECASE)
            return o
    return ""

def transformar_link_drive(url):
    if not url: return ""
    url_limpia = str(url).replace(" ", "").strip()
    match = re.search(r'drive\.google\.com/file/d/([a-zA-Z0-9_-]+)', url_limpia)
    if match: return f"https://lh3.googleusercontent.com/d/{match.group(1)}"
    return url_limpia

def obtener_resumen_metadata(page):
    try:
        meta = page.locator('meta[property="og:description"], meta[name="description"]').first
        if meta.count() > 0:
            desc = meta.get_attribute("content", timeout=2000)
            if desc and len(desc.strip()) > 15 and not es_bloqueo_waf(desc): 
                return desc.strip()
    except: pass
    return ""

# ---------- v5.80: EXTRACCIÓN DE FECHA MEJORADA ----------
_MESES_ES = {'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8, 'septiembre': 9, 'setiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12,
             'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'ago': 8, 'sep': 9, 'sept': 9, 'oct': 10, 'nov': 11, 'dic': 12}

def _fecha_valida(d, m, y):
    try:
        dt = datetime.datetime(int(y), int(m), int(d))
        hoy = datetime.datetime.now()
        if dt > hoy + datetime.timedelta(days=1) or dt < hoy - datetime.timedelta(days=1100): return ""
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return ""

def _iso_a_fecha(val):
    """ISO 8601 (con o sin hora/zona) -> DD/MM/YYYY en horario de Argentina (UTC-3)."""
    m = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})(?:[T\s]+(\d{1,2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?\s*(Z|[+-]\d{2}:?\d{2})?)?', str(val or ''))
    if not m: return ""
    y, mo, d, hh, mm, ss, tz = m.groups()
    try:
        if hh is not None and tz:
            dt = datetime.datetime(int(y), int(mo), int(d), int(hh), int(mm), int(ss or 0))
            off = 0 if tz == 'Z' else (1 if tz[0] == '+' else -1) * (int(tz[1:3]) * 60 + int(tz[-2:]))
            dt = dt - datetime.timedelta(minutes=off) - datetime.timedelta(hours=3)  # a UTC y luego a ART
            return _fecha_valida(dt.day, dt.month, dt.year)
    except Exception:
        pass
    return _fecha_valida(d, mo, y)

def _texto_a_fecha(txt):
    """Fechas escritas: '8 de octubre de 2026', '08/10/2026', '08-10-26', 'octubre 8, 2026'."""
    t = remover_acentos(str(txt or '').lower())
    m = re.search(r'(\d{1,2})\s*(?:de\s+)?([a-z]{3,10})\.?,?\s*(?:de\s+|del\s+)?(20\d{2})', t)
    if m and m.group(2) in _MESES_ES:
        f = _fecha_valida(m.group(1), _MESES_ES[m.group(2)], m.group(3))
        if f: return f
    m = re.search(r'([a-z]{3,10})\.?\s+(\d{1,2}),?\s+(20\d{2})', t)
    if m and m.group(1) in _MESES_ES:
        f = _fecha_valida(m.group(2), _MESES_ES[m.group(1)], m.group(3))
        if f: return f
    m = re.search(r'(?<!\d)(\d{1,2})[/\-.](\d{1,2})[/\-.](20\d{2}|\d{2})(?!\d)', t)
    if m:
        y = m.group(3) if len(m.group(3)) == 4 else "20" + m.group(3)
        f = _fecha_valida(m.group(1), m.group(2), y)
        if f: return f
    return ""

_JS_FECHAS = """() => {
  const out = {metas: [], times: [], ld: [], textos: []};
  const claves = ['article:published_time','og:article:published_time','datepublished','pubdate','publishdate','publish_date','date','dc.date','dc.date.issued','dc.date.created','sailthru.date','parsely-pub-date','cxenseparse:recs:publishtime','og:updated_time','article:modified_time','datemodified'];
  document.querySelectorAll('meta').forEach(m => {
    const k = (m.getAttribute('property') || m.getAttribute('name') || m.getAttribute('itemprop') || '').toLowerCase();
    const v = m.getAttribute('content');
    if (v && claves.includes(k)) out.metas.push([k, v]);
  });
  document.querySelectorAll('time[datetime], [itemprop="datePublished"]').forEach(t => {
    const v = t.getAttribute('datetime') || t.getAttribute('content') || t.innerText;
    if (v) out.times.push([ (t.getAttribute('itemprop') || '') + ' ' + (t.className || ''), v.slice(0, 60)]);
  });
  document.querySelectorAll('script[type="application/ld+json"]').forEach(sc => {
    try {
      const walk = o => { if (!o || typeof o !== 'object') return;
        if (Array.isArray(o)) return o.forEach(walk);
        if (o.datePublished) out.ld.push(['datePublished', String(o.datePublished)]);
        else if (o.dateCreated) out.ld.push(['dateCreated', String(o.dateCreated)]);
        Object.values(o).forEach(walk); };
      walk(JSON.parse(sc.textContent));
    } catch (e) {}
  });
  document.querySelectorAll('[class*="fecha"],[class*="date"],[class*="time"],[class*="publish"],[class*="byline"],[class*="meta"],[id*="fecha"],[id*="date"]').forEach(e => {
    const t = (e.innerText || '').trim();
    if (t && t.length < 120 && out.textos.length < 12) out.textos.push(t);
  });
  const art = document.querySelector('article') || document.body;
  out.cuerpo = (art.innerText || '').slice(0, 1200);
  return out;
}"""

def _candidatos_fecha(page):
    try: return page.evaluate(_JS_FECHAS)
    except Exception: return None

def obtener_fecha_metadata(page, _cand=None):
    """Fecha 'fuerte': metadatos de publicación (meta, JSON-LD, <time>). Devuelve DD/MM/YYYY o ''."""
    c = _cand or _candidatos_fecha(page)
    if not c: return ""
    for k, v in c.get('metas', []):
        if 'modified' in k or 'updated' in k: continue
        f = _iso_a_fecha(v)
        if f: return f
    for k, v in c.get('ld', []):
        f = _iso_a_fecha(v)
        if f: return f
    for k, v in c.get('times', []):
        f = _iso_a_fecha(v) or _texto_a_fecha(v)
        if f: return f
    return ""

def obtener_fecha_debil(page, url="", _cand=None):
    """Último recurso (después del RSS): fecha en textos visibles, URL o fecha de modificación."""
    c = _cand or _candidatos_fecha(page) or {}
    for t in c.get('textos', []):
        f = _texto_a_fecha(t)
        if f: return f
    u = str(url or '')
    m = re.search(r'(20\d{2})[/\-_]?(\d{2})[/\-_]?(\d{2})(?!\d)', u)
    if m:
        f = _fecha_valida(m.group(3), m.group(2), m.group(1))
        if f: return f
    f = _texto_a_fecha((c.get('cuerpo', '') or '')[:600])
    if f: return f
    for k, v in c.get('metas', []):
        if 'modified' in k or 'updated' in k:
            f = _iso_a_fecha(v)
            if f: return f
    return ""

def fecha_sin_dato():
    return "??/" + datetime.datetime.now().strftime("%m/%Y")  # v5.80: si no se encontró, el día queda como ?? para detectarlo

def _sin_titulo(cuerpo, titulo):  # v5.49: saca del cuerpo las líneas que son el título, para que la oración clave sea del texto de la nota y no el título
    _c = lambda x: re.sub(r'[^a-z0-9]', '', remover_acentos(str(x).lower()))
    t = _c(titulo)
    if len(t) < 10: return cuerpo
    return "\n".join(l for l in str(cuerpo).split("\n") if not (len(_c(l)) >= 10 and (_c(l) in t or (t in _c(l) and len(_c(l)) < len(t) + 40))))

# ---------- v5.55: AUTO-ACTUALIZACIÓN DEL .EXE ----------
# version.txt en GitHub: línea 1 = versión (ej. 2.1), línea 2 = URL de descarga directa del .exe nuevo (ej. link de GitHub Releases)
def _vtuple(v):
    try: return tuple(int(x) for x in re.findall(r'\d+', str(v)))
    except Exception: return (0,)

def consultar_version_remota():
    try:
        r_ = requests.get(URL_VERSION_GITHUB, timeout=6)
        if r_.status_code != 200: return None, None
        lineas = [l.strip() for l in r_.text.splitlines() if l.strip()]
        return (lineas[0] if lineas else None), (lineas[1] if len(lineas) > 1 else None)
    except Exception:
        return None, None

def descargar_y_preparar_update(url):
    """Descarga el .exe nuevo junto al actual, lo valida y lanza un .bat que lo reemplaza (con rollback). Devuelve (ok, msg)."""
    try:
        if not getattr(sys, 'frozen', False): return False, "Solo se actualiza desde el .exe compilado."
        exe = os.path.abspath(sys.executable)
        nuevo = exe + ".new"
        with requests.get(url, stream=True, timeout=30) as resp:
            resp.raise_for_status()
            with open(nuevo, 'wb') as f:
                for chunk in resp.iter_content(1024 * 1024): f.write(chunk)
        if os.path.getsize(nuevo) < 5 * 1024 * 1024:  # validación mínima: un .exe real pesa MBs
            os.remove(nuevo); return False, "La descarga está incompleta o es inválida."
        bat = exe + ".update.bat"
        carpeta = os.path.dirname(exe)
        with open(bat, 'w', encoding='utf-8') as f:  # v5.56: sin 'timeout' (falla sin consola) ni %n% dentro de paréntesis; espera por ping
            f.write(f'''@echo off
cd /d "{carpeta}"
ping -n 6 127.0.0.1 >nul
set n=0
:retry
set /a n+=1
move /y "{exe}" "{exe}.bak" >nul 2>&1
if not exist "{exe}" goto swap
if %n% GEQ 15 goto fail
ping -n 3 127.0.0.1 >nul
goto retry
:swap
move /y "{nuevo}" "{exe}" >nul 2>&1
if not exist "{exe}" move /y "{exe}.bak" "{exe}" >nul 2>&1
goto run
:fail
del "{nuevo}" >nul 2>&1
:run
start "" "{exe}"
del "%~f0"
''')
        subprocess.Popen(['cmd', '/c', bat], creationflags=0x08000000, close_fds=True, cwd=carpeta)  # CREATE_NO_WINDOW
        return True, "Actualizando..."
    except Exception as e:
        return False, f"Error al actualizar: {e}"

def completar_bloque_pre(b, palabras_clave, sec_id=""):  # v5.52: nota excluida antes de leerse y aprobada a mano: la lee ahora como en la 1ª vez
    try:
        with sync_playwright() as p:
            br = p.chromium.launch(headless=True, args=["--no-sandbox"])
            ctx = br.new_context(viewport={"width": 1920, "height": 1080}, user_agent="Mozilla/5.0")
            pg = ctx.new_page()
            pg.goto(b.get('link', ''), timeout=15000, wait_until="domcontentloaded")
            pg.wait_for_timeout(1500)
            if re.search(r'//(news|consent)\.google\.', pg.url or ''):
                try: pg.wait_for_url(lambda u: not re.search(r'//(news|consent)\.google\.', u), timeout=6000)
                except Exception: pass
            pg.wait_for_timeout(1500)
            b['link_destino'] = pg.url
            _cf = _candidatos_fecha(pg); _ff = obtener_fecha_metadata(pg, _cf)  # v5.80
            if _ff: b['fecha'] = _ff
            elif not b.get('fecha'): b['fecha'] = obtener_fecha_debil(pg, pg.url, _cf) or fecha_sin_dato()
            try: pg.evaluate("document.querySelectorAll('aside, footer, nav, .sidebar, .widget, [class*=\"related\"], [class*=\"popular\"]').forEach(el => el.remove())")
            except Exception: pass
            b['bajada_real'] = obtener_resumen_metadata(pg)
            b['oracion_clave'] = ""
            for sel in ("(document.querySelector('article') || document.body).innerText", "document.body.innerText"):
                try: cuerpo = pg.evaluate("() => " + sel)
                except Exception: cuerpo = ""
                b['oracion_clave'] = extraer_oracion_clave(_sin_titulo(cuerpo or "", b.get('titulo', '')), palabras_clave, sec_id)
                if b['oracion_clave']: break
            br.close()
    except Exception:
        pass
    b['leida'] = True

def construir_bloque_texto(resumen_meta, oracion, titulo, palabras_clave="", sec_id="", resumen_rss=""):
    secciones_destacadas = ['exclusivas', 'mars_tema_1', 'mars_tema_2', 'mars_tema_3', 'bms_tema_1', 'arredo_tema_1', 'arredo_tema_2', 'amanco_tema_1', 'booking_tema_1', 'mars_competencia', 'bms_tema_4', 'arredo_tema_6', 'amanco_tema_2', 'booking_tema_2', 'mailboxes_tema_1', 'mailboxes_tema_2']  # v5.47
    
    resumen_meta_limpio = limpiar_basura_periodistica(corregir_mojibake(resumen_meta)).replace("<em>", "").replace("</em>", "")
    titulo_limpio = limpiar_basura_periodistica(corregir_mojibake(titulo))
    
    tit_n = remover_acentos(titulo_limpio.lower()).strip()
    tit_compact = re.sub(r'[^a-z0-9]', '', tit_n)
    
    if resumen_meta_limpio and tit_compact:
        meta_n = remover_acentos(resumen_meta_limpio.lower()).strip()
        meta_compact = re.sub(r'[^a-z0-9]', '', meta_n)
        if len(tit_compact) > 10 and (tit_compact in meta_compact or meta_compact in tit_compact):
            resumen_meta_limpio = ""

    texto_final = ""
    
    # 1. Recuperamos el resumen base EXACTAMENTE igual que siempre
    if resumen_meta_limpio and len(resumen_meta_limpio.strip()) > 15:
        texto_final = resumen_meta_limpio.strip()
    elif oracion and not oracion.startswith("[Nota inaccesible"):
        texto_final = oracion.strip()
    elif resumen_rss:
        r_rss = limpiar_basura_periodistica(corregir_mojibake(resumen_rss))
        o_rss = extraer_oracion_clave(re.sub(r'<[^>]+>', '', r_rss), palabras_clave, sec_id) if r_rss else ""
        _rss_c = re.sub(r'[^a-z0-9]', '', remover_acentos(re.sub(r'<[^>]+>', '', r_rss).lower()))
        _rss_es_titulo = bool(tit_compact) and tit_compact in _rss_c and len(_rss_c) < len(tit_compact) + 40  # v5.48: RSS de Google News = título + medio, no es bajada
        _o_c = re.sub(r'[^a-z0-9]', '', remover_acentos(re.sub(r'<[^>]+>', '', o_rss or '').lower()))
        if bool(tit_compact) and _o_c and (_o_c in tit_compact or (tit_compact in _o_c and len(_o_c) < len(tit_compact) + 40)):
            o_rss = ""  # v5.51: la "oración" del RSS es el título (+medio): no es bajada
        if o_rss:
            texto_final = o_rss.strip()
        elif r_rss and len(r_rss.strip()) > 15 and not _rss_es_titulo:
            texto_final = re.sub(r'<[^>]+>', '', r_rss).strip()

    # 2. Lógica para sumar la oración en Competencia
    es_competencia = str(sec_id) in IDS_COMPETENCIA or str(sec_id) in IDS_EXCLUSIVAS  # v5.47: Exclusivas y Competencia de todos los clientes suman la oración con la keyword
    
    if es_competencia and oracion and not oracion.startswith("[Nota inaccesible"):
        oracion_limpia = re.sub(r'<[^>]+>', '', oracion).strip()
        texto_limpio = re.sub(r'<[^>]+>', '', texto_final).strip()
        
        # Comparamos para no duplicar si la oración resultó ser idéntica a la bajada
        # v5.49: si la keyword NO aparece en la bajada, se suma la oración con la keyword a continuación (sin salto de línea)
        if texto_limpio and oracion_limpia and not contiene_palabra_clave(texto_limpio, palabras_clave) and oracion_limpia not in texto_limpio:
            texto_final = f"{texto_final} {oracion.strip()}"
        elif not texto_final:
            texto_final = oracion.strip()

    # Convertimos el feo [...] en puntos suspensivos limpios sin borrar texto
    texto_final = texto_final.replace(" [...]", "...").replace("[...]", "...")

    # 3. Retorno
    if sec_id in secciones_destacadas:
        if texto_final:
            return f"<p>{texto_final}</p>"
        else:
            return f"<p style='color: #888888; font-style: italic;'>[Mención no detectada automáticamente en el texto visible]</p>"
    else:
        if texto_final:
            return f"<p>{texto_final}</p>"
        else:
            return "<p style='color: #888888; font-style: italic;'>Sin resumen disponible.</p>"

def buscar_metricas_medio(df_medios, url, medio_nombre):
    alcance, tier, ad_value = "?", "?", "?"
    if df_medios is None or df_medios.empty:
        return alcance, tier, ad_value

    cols_norm = {c: str(c).lower().strip() for c in df_medios.columns}
    col_medios = next((c for c, norm in cols_norm.items() if 'medio' in norm), None)
    col_alcance = next((c for c, norm in cols_norm.items() if 'alcance' in norm), None)
    col_tier = next((c for c, norm in cols_norm.items() if 'tier' in norm), None)
    col_advalue = next((c for c, norm in cols_norm.items() if 'ad' in norm and 'value' in norm), None)

    if not col_medios:
        return alcance, tier, ad_value 

    netloc_clean = urlparse(url).netloc.replace("www.", "").split('.')[0].lower()
    medio_norm = limpiar_nombre_medio(medio_nombre).lower()
    medio_orig_lower = str(medio_nombre).strip().lower()
    
    def super_limpiar(texto):
        t = str(texto).lower().strip()
        t = re.sub(r'\.(com|net|org|ar|es|mx|cl|co|pe|uy|py|info|tv).*$', '', t)
        t = re.sub(r'[^a-z0-9]', '', t)
        return t

    medios_col_raw = df_medios[col_medios].astype(str)
    medios_col_super_clean = medios_col_raw.apply(super_limpiar)

    n_clean_se = super_limpiar(netloc_clean)
    m_norm_se = super_limpiar(medio_norm)
    m_orig_se = super_limpiar(medio_orig_lower)

    fila = df_medios[
        (medios_col_raw.str.strip().str.lower() == netloc_clean) | 
        (medios_col_raw.str.strip().str.lower() == medio_norm) | 
        (medios_col_raw.str.strip().str.lower() == medio_orig_lower)
    ]
    
    if fila.empty:
        fila = df_medios[
            (medios_col_super_clean == n_clean_se) | 
            (medios_col_super_clean == m_norm_se) | 
            (medios_col_super_clean == m_orig_se)
        ]
        
    if fila.empty and len(m_norm_se) > 3:
        mask = medios_col_super_clean.apply(lambda x: len(x) > 3 and (x in m_norm_se or m_norm_se in x))
        fila = df_medios[mask]

    if not fila.empty:
        if col_alcance: alcance = str(fila[col_alcance].iloc[0])
        if col_tier: tier = str(fila[col_tier].iloc[0])
        if col_advalue: ad_value = str(fila[col_advalue].iloc[0])
        
    return alcance, tier, ad_value

def _num_orden(v):
    try: return float(re.sub(r'[^0-9]', '', str(v))) if re.search(r'\d', str(v)) else 0.0
    except Exception: return 0.0

def _rank_red(n):  # v5.53: Twitter/X=0, IG=1, FB=2, otras=3, None=no es red social
    t = " ".join(str(n.get(k, '')) for k in ('medio', 'link', 'link_destino')).lower()
    if re.search(r'twitter|(?<![a-z0-9])x\.com', t): return 0
    if 'instagram' in t: return 1
    if 'facebook' in t: return 2
    if any(x in t for x in ('threads', 'tiktok', 'linkedin')): return 3
    return None

def sort_key_final(n, sec_id):
    es_grafica = 0 if n.get('tipo_medio') == 'Gráfica' else 1
    medio_lower = str(n.get('medio', '')).lower()
    ts_fecha = parse_fecha_sortable(n.get('fecha', ''))
    if sec_id in IDS_SINTESIS and sec_id not in IDS_SIN_METRICAS:
        red = _rank_red(n)
        tier_val = int(_num_orden(n.get('tier', ''))) if _num_orden(n.get('tier', '')) in (1, 2, 3) else 99
        if es_grafica == 0: cat = 0
        elif red is not None: cat = 2
        elif tier_val in (1, 2, 3): cat = 1
        else: cat = 3
        # v5.53: Gráficas > Online T1/T2/T3 (Ad Value, Alcance, alfabético) > Redes T1/T2/T3 (X, IG, FB; Ad Value, Alcance, alfabético)
        a_, b_ = (red, tier_val) if cat == 2 else (tier_val, 0)  # v5.54: redes = primero por red (X, IG, FB), luego tier
        return (cat, a_, b_, -_num_orden(n.get('ad_value', '')), -_num_orden(n.get('alcance', '')), medio_lower, -ts_fecha)
    return (es_grafica, 99, 0, 0, 0, medio_lower, -ts_fecha)

def insertar_nota_ordenada(lista, nota, sec_id):  # v5.53: inserta la nota según las reglas de orden de la sección
    k = sort_key_final(nota, sec_id)
    for i, x in enumerate(lista):
        if sort_key_final(x, sec_id) > k:
            lista.insert(i, nota); return
    lista.append(nota)

def es_tier_1_o_2(tier_val):
    try:
        t_clean = str(tier_val).lower().replace('tier', '').strip()
        if t_clean in ['1', '2', '1.0', '2.0']:
            return True
    except Exception:
        pass
    return False

def parse_fecha_sortable(texto_fecha):
    if not texto_fecha: return 0
    t_str = str(texto_fecha).strip()
    try:
        dt = datetime.datetime.strptime(t_str, "%d/%m/%Y")
        return dt.timestamp()
    except Exception:
        try:
            dt = datetime.datetime.strptime(t_str, "%Y-%m-%d")
            return dt.timestamp()
        except Exception:
            return 0

# ====================================================================
# GESTIÓN DE HISTORIAL ANTIDUPLICADOS POR CLIENTE (EXCEL Y JSON)
# ====================================================================
def cargar_historial_cliente(cliente_nombre):
    links_historial = set()
    sheet_name = cliente_nombre[:30]

    if os.path.exists(HISTORIAL_EXCEL):
        try:
            xls = pd.ExcelFile(HISTORIAL_EXCEL)
            if sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name)
                for col in df.columns:
                    for val in df[col].dropna():
                        v_str = str(val).strip().lower()
                        if v_str.startswith("http"):
                            links_historial.add(v_str)
        except Exception as e:
            print(f"⚠️ Error al leer historial Excel para {cliente_nombre}: {e}")

    if os.path.exists(HISTORIAL_JSON):
        try:
            with open(HISTORIAL_JSON, "r", encoding="utf-8") as f:
                data_json = json.load(f)
                if isinstance(data_json, dict):
                    client_links = data_json.get(cliente_nombre, [])
                    for l in client_links:
                        links_historial.add(str(l).strip().lower())
        except Exception as e:
            print(f"⚠️ Error al leer historial JSON: {e}")

    return links_historial

def guardar_en_historial_excel(cliente_nombre, data_auditoria):
    try:
        sheets_dict = {}
        if os.path.exists(HISTORIAL_EXCEL):
            try:
                xls = pd.ExcelFile(HISTORIAL_EXCEL)
                for sheet in xls.sheet_names:
                    sheets_dict[sheet] = pd.read_excel(xls, sheet_name=sheet)
            except Exception:
                sheets_dict = {}

        sheet_name = cliente_nombre[:30]
        
        if sheet_name in sheets_dict:
            df_client = sheets_dict[sheet_name]
        else:
            df_client = pd.DataFrame()

        secciones_dict = {}
        for col in df_client.columns:
            secciones_dict[col] = [str(x).strip() for x in df_client[col].dropna() if str(x).strip()]

        nuevos_links_json = []
        for sec in data_auditoria:
            sec_nombre = sec['nombre']
            if sec_nombre not in secciones_dict:
                secciones_dict[sec_nombre] = []
            
            for ev in sec.get('evaluaciones', []):
                if ev.get('estado') == 'SUMADA' and ev.get('link'):
                    link_orig_clean = str(ev['link']).strip()
                    nuevos_links_json.append(link_orig_clean.lower())

                    link_excel = str(ev.get('link_destino') or ev.get('link')).strip()
                    if link_excel and link_excel not in secciones_dict[sec_nombre]:
                        secciones_dict[sec_nombre].append(link_excel)
                        nuevos_links_json.append(link_excel.lower())

        max_len = max([len(v) for v in secciones_dict.values()], default=0)
        df_actualizado = pd.DataFrame()
        for col_name, links_list in secciones_dict.items():
            padded = links_list + [None] * (max_len - len(links_list))
            df_actualizado[col_name] = padded

        sheets_dict[sheet_name] = df_actualizado

        with pd.ExcelWriter(HISTORIAL_EXCEL, engine='openpyxl') as writer:
            for s_name, df_sheet in sheets_dict.items():
                df_sheet.to_excel(writer, sheet_name=s_name, index=False)

        data_json = {}
        if os.path.exists(HISTORIAL_JSON):
            try:
                with open(HISTORIAL_JSON, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        data_json = loaded
            except Exception:
                data_json = {}

        client_set = set(data_json.get(cliente_nombre, []))
        client_set.update(nuevos_links_json)
        data_json[cliente_nombre] = list(client_set)

        with open(HISTORIAL_JSON, "w", encoding="utf-8") as f:
            json.dump(data_json, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"⚠️ Error al guardar en historial Excel: {e}")

def extraer_gacetilla_mas_reciente(df_gacetillas, cliente_nombre):
    if df_gacetillas is None or df_gacetillas.empty:
        return None
    try:
        cols = {remover_acentos(str(c).lower().strip()): c for c in df_gacetillas.columns}
        
        col_cliente = next((orig for k, orig in cols.items() if 'cliente' in k), None)
        col_fecha = next((orig for k, orig in cols.items() if 'fecha' in k or 'date' in k), None)
        col_gacetilla = next((orig for k, orig in cols.items() if 'gacetilla' in k or 'titulo' in k or 'frase' in k or 'busqueda' in k or 'tema' in k), None)
        
        if col_cliente and col_gacetilla:
            cli_norm = remover_acentos(str(cliente_nombre).lower().strip())
            df_sub = df_gacetillas[df_gacetillas[col_cliente].astype(str).apply(lambda x: cli_norm in remover_acentos(x.lower()))].copy()
            if not df_sub.empty:
                if col_fecha:
                    df_sub['fecha_dt'] = pd.to_datetime(df_sub[col_fecha], dayfirst=True, errors='coerce')
                    df_sub = df_sub.sort_values('fecha_dt', ascending=False)
                texto = str(df_sub[col_gacetilla].iloc[0]).strip()
                if texto and texto.lower() != 'nan':
                    return texto
        
        col_cli_direct = next((orig for k, orig in cols.items() if remover_acentos(str(cliente_nombre).lower()) in k or k in remover_acentos(str(cliente_nombre).lower())), None)
        if col_cli_direct:
            vals = [str(v).strip() for v in df_gacetillas[col_cli_direct].dropna().tolist() if str(v).strip() and str(v).lower() != 'nan']
            if vals:
                return vals[-1]
    except Exception as e:
        print(f"Error parseando gacetillas: {e}")
        
    return None

def obtener_gacetilla_cliente_cached(cliente_nombre):
    global GACETILLAS_CACHE
    if GACETILLAS_CACHE is None:
        try:
            match = re.search(r'/d/([a-zA-Z0-9-_]+)', LINK_EXCEL_DRIVE)
            if match:
                file_id = match.group(1)
                url_descarga = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
                req_excel = urllib.request.Request(url_descarga, headers={'User-Agent': 'Mozilla/5.0'})
                resp_excel = urllib.request.urlopen(req_excel)
                xls_cargado = pd.ExcelFile(io.BytesIO(resp_excel.read()))
                hoja_gacetillas = next((s for s in xls_cargado.sheet_names if "gacetilla" in remover_acentos(s.lower())), None)
                if hoja_gacetillas:
                    GACETILLAS_CACHE = pd.read_excel(xls_cargado, sheet_name=hoja_gacetillas)
        except Exception as e:
            print(f"Error cargando gacetillas cache: {e}")

    if GACETILLAS_CACHE is not None:
        return extraer_gacetilla_mas_reciente(GACETILLAS_CACHE, cliente_nombre)
    return None

def es_seccion_general(sec_id, nombre_seccion):
    sec_id_lower = str(sec_id).lower()
    nombre_lower = remover_acentos(str(nombre_seccion).lower())
    for kw in SECCIONES_DIRECTAS_KEYWORDS:
        if kw in sec_id_lower or kw in nombre_lower:
            return False
    return True

def obtener_url_fuente_rss(item):
    try:
        src = getattr(item, 'source', None)
        if src is not None and hasattr(src, 'get'):
            return str(src.get('url') or "").strip()
    except Exception:
        pass
    return ""

def _hostnames_en_texto(texto):
    t = urllib.parse.unquote((texto or "")).lower()
    hosts = []
    for h in re.findall(r'https?://([^/\s?#]+)', t):
        h = h.split('@')[-1].split(':')[0].strip('.')
        if h.startswith('www.'): h = h[4:]
        if h: hosts.append(h)
    return hosts

def _motivo_host_extranjero(host):
    host = (host or "").strip('.').lower()
    if host.startswith('www.'): host = host[4:]
    if not host or '.' not in host:
        return ""
    for tld in DOMINIOS_EXTRANJEROS:
        if host.endswith(tld):
            return f"dominio {tld}"
    for dom in DOMINIOS_EXTRANJEROS_EXACTOS:
        if host == dom or host.endswith('.' + dom):
            return f"portal extranjero conocido {dom}"
    labels = host.split('.')
    if len(labels) >= 3 and labels[0] in SUBDOMINIOS_EXTRANJEROS:
        return f"edición de otro país ({labels[0]}.)"
    return ""

def motivo_portal_extranjero(url, medio, texto="", url_fuente=""):
    for texto_url, etiqueta in ((url, "URL"), (url_fuente, "fuente RSS")):
        for host in _hostnames_en_texto(texto_url):
            m = _motivo_host_extranjero(host)
            if m:
                return f"{m} en {etiqueta}"

    medio_lower = (medio or "").lower()
    for token in re.findall(r'[a-z0-9-]+(?:\.[a-z0-9-]+)+', medio_lower):
        m = _motivo_host_extranjero(token)
        if m:
            return f"{m} en nombre del medio"

    url_lower = urllib.parse.unquote((url or "")).lower()
    for ruta in RUTAS_EXTRANJERAS_KEYWORDS:
        if ruta in url_lower:
            return f"ruta {ruta}"

    medio_norm = remover_acentos(medio_lower)
    url_fuente_lower = (url_fuente or "").lower()
    for kw in PORTALES_EXTRANJEROS_KEYWORDS:
        if kw in medio_norm or kw in url_lower or kw in url_fuente_lower:
            return f"portal extranjero '{kw}'"

    return ""

def es_portal_extranjero(url, medio, texto="", url_fuente=""):
    return bool(motivo_portal_extranjero(url, medio, texto, url_fuente))

def es_fecha_en_rango(texto_fecha, timeframe):
    if not texto_fecha:
        return True
    try:
        dt_item = email.utils.parsedate_to_datetime(texto_fecha)
        dt_now = datetime.datetime.now(datetime.timezone.utc) if dt_item.tzinfo else datetime.datetime.now()
        
        dias = 1
        if timeframe == "3d": dias = 3
        elif timeframe in ["5d", "7d"]: dias = 5
        
        limite_segundos = (dias * 86400) + (4 * 3600)
        diferencia = (dt_now - dt_item).total_seconds()
        
        return 0 <= diferencia <= limite_segundos
    except Exception:
        return True

def prefiltrar_item_rss(it, timeframe, exclusiones=None, df_medios=None):
    """v5.35: detecta en el feed (antes de clasificar/IA) notas fuera de rango o con exclusiones.
    Devuelve 'fecha', 'exclusion' o ''. Las notas Tier 1/2 se conservan (devuelve '') para que
    procesar_seccion las registre en la auditoría."""
    try:
        fecha = it.pubDate.text if getattr(it, 'pubDate', None) else ""
        motivo = ""
        if fecha and not es_fecha_en_rango(fecha, timeframe):
            motivo = "fecha"
        elif exclusiones:
            tit = it.title.text if getattr(it, 'title', None) else ""
            desc = it.description.text if getattr(it, 'description', None) else ""
            if contiene_exclusion(f"{tit} {desc}", exclusiones):
                motivo = "exclusion"
        if not motivo:
            return ""
        if df_medios is not None:
            link = it.link.text if getattr(it, 'link', None) and it.link.text else ""
            medio = it.source.text if getattr(it, 'source', None) and it.source.text else urlparse(link).netloc.replace("www.", "").split('.')[0].capitalize()
            _, tier, _ = buscar_metricas_medio(df_medios, link, medio)
            if es_tier_1_o_2(tier):
                return ""
        return ""  # v5.36: se conservan TODAS (fecha/exclusión se registran en la auditoría dentro de procesar_seccion)
    except Exception:
        return ""

def aplicar_prefiltro_rss(tuplas, timeframe, exclusiones, df_medios, logger, etiqueta):
    """v5.35: filtra lista de tuplas (item, origen, feed_id): primero rango de fechas, luego exclusiones."""
    conservadas, n_fecha, n_excl = [], 0, 0
    for t in tuplas:
        m = prefiltrar_item_rss(t[0], timeframe, exclusiones, df_medios)
        if m == "fecha": n_fecha += 1
        elif m == "exclusion": n_excl += 1
        else: conservadas.append(t)
    if n_fecha or n_excl:
        logger(f"  🧹 Prefiltro {etiqueta}: {n_fecha} fuera de rango ({timeframe}) y {n_excl} por exclusiones descartadas antes de la IA.")
    return conservadas

def registrar_actividad(usuario, accion, detalles):
    return  # v5.78: registro de actividad desactivado (ya no se escribe registro_uso.csv)

# ====================================================================
# COMPONENTE DE CONSOLA / MONITOR DE PROCESOS INTERACTIVO
# ====================================================================
class MonitorConsola:
    def __init__(self, parent_container):
        self.container = parent_container
        with self.container:
            self.scroll = ui.scroll_area().classes('w-full h-96 bg-[#0f172a] text-slate-200 p-4 rounded-xl border border-slate-800 shadow-inner font-mono text-xs')
            with self.scroll:
                self.content = ui.column().classes('w-full gap-1 p-0')

    def push(self, msg):
        msg_str = str(msg)
        msg_html = re.sub(
            r'(https?://[^\s]+)',
            r'<a href="\1" target="_blank" rel="noopener noreferrer" class="text-sky-400 underline hover:text-sky-300 font-semibold" onclick="event.stopPropagation();">\1</a>',
            msg_str
        )

        if "✓ SUMADA" in msg_str:
            line_html = f'<div class="text-emerald-400 font-semibold bg-emerald-950/40 px-2 py-1 rounded border-l-4 border-emerald-500">{msg_html}</div>'
        elif "🔀 Feed Excel" in msg_str or "🔍 Búsqueda Extra" in msg_str or "📰 Gacetilla Excel" in msg_str:
            line_html = f'<div class="text-sky-300 bg-sky-950/40 px-2 py-1 rounded border-l-4 border-sky-500 font-semibold">{msg_html}</div>'
        elif "EXCLUIDA" in msg_str or "OMITIDA" in msg_str or "⛔" in msg_str or "❌" in msg_str or "🌎" in msg_str or "📅" in msg_str or "🔁" in msg_str or "📜" in msg_str or "✂️" in msg_str:
            line_html = f'<div class="text-rose-300 bg-rose-950/30 px-2 py-1 rounded border-l-4 border-rose-600/70">{msg_html}</div>'
        elif "🔎 ANALIZANDO SECCIÓN" in msg_str:
            line_html = f'<div class="text-amber-300 font-bold text-sm mt-3 mb-1 border-b border-amber-500/30 pb-1">{msg_html}</div>'
        elif "🤖 IA" in msg_str:
            line_html = f'<div class="text-purple-300 bg-purple-950/40 px-2 py-0.5 rounded border-l-2 border-purple-500">{msg_html}</div>'
        elif "🔎 Revisando" in msg_str or "📦" in msg_str:
            line_html = f'<div class="text-slate-300 px-2 py-0.5">{msg_html}</div>'
        elif "🔗 Destino" in msg_str:
            line_html = f'<div class="text-slate-400 px-2 py-0.5 italic">{msg_html}</div>'
        else:
            line_html = f'<div class="text-slate-200 px-2 py-0.5">{msg_html}</div>'

        with self.content:
            ui.html(line_html)
        self.scroll.scroll_to(percent=1.0)

    def clear(self):
        self.content.clear()

# ====================================================================
# CLASES Y ESTADO GLOBAL
# ====================================================================
class ObjetoManual:
    def __init__(self, url, titulo_texto="Nota Manual", desc_texto=""):
        class ElementoTexto:
            def __init__(self, texto): self.text = texto
        self.link = ElementoTexto(url)
        self.title = ElementoTexto(titulo_texto)
        self.description = ElementoTexto(desc_texto)
        self.pubDate = ElementoTexto("")
        self.source = ElementoTexto("Manual")

class AppState:
    def __init__(self):
        self.cliente = list(CLIENTES_CONFIG.keys())[0]
        self.timeframe = "1d"
        self.extra_searches = [{"q": "", "sec": ""}]
        self.links_manuales = {}
        self.graficas = {}
        self.log_box = None
        self.log_container = None
        self.timer_label = None
        self.status_chip = None
        self.progress_label = None
        self.rss_label = None
        self.last_data_editor = None
        self.last_data_auditoria = None
        # --- NUEVO ---
        self.is_paused = False  
        self.stop_req = False  # v5.50
        self.btn_stop = None  # v5.50
        self.btn_procesar = None 
        self.btn_pausa = None    
        # -------------
        self.init_secciones()

    def init_secciones(self):
        config = CLIENTES_CONFIG[self.cliente]
        self.links_manuales = {sec['id']: "" for sec in config["secciones"] if not sec.get('es_separador')}
        self.graficas = {sec['id']: [{"medio": "", "titulo": "", "fecha": datetime.datetime.now().strftime("%Y-%m-%d"), "link": "", "bajada": "", "alcance": "", "tier": "", "ad_value": ""}] for sec in config["secciones"] if not sec.get('es_separador')}
        
    def add_grafica(self, sec_id):
        self.graficas[sec_id].append({"medio": "", "titulo": "", "fecha": datetime.datetime.now().strftime("%Y-%m-%d"), "link": "", "bajada": "", "alcance": "", "tier": "", "ad_value": ""})
        
    def add_extra_search(self):
        self.extra_searches.append({"q": "", "sec": ""})

state = AppState()

# ====================================================================
# CARGA Y SINCRONIZACIÓN DE EXCEL (MÉTRICAS, FEEDS, GACETILLAS Y FEEDS GLOBALES)
# ====================================================================
def sincronizar_base_medios(cliente_nombre, logger):
    global GACETILLAS_CACHE
    logger("📁 Sincronizando Base de Medios, Feeds y Gacetillas desde Google Drive...")
    df_medios = None
    df_feeds = None
    df_gacetillas = None
    df_feeds_globales = None
    try:
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', LINK_EXCEL_DRIVE)
        if match:
            file_id = match.group(1)
            url_descarga = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
            req_excel = urllib.request.Request(url_descarga, headers={'User-Agent': 'Mozilla/5.0'})
            resp_excel = urllib.request.urlopen(req_excel)
            xls_cargado = pd.ExcelFile(io.BytesIO(resp_excel.read()))
            
            df_medios = pd.read_excel(xls_cargado, sheet_name=0)
            
            hoja_cliente = CLIENTES_CONFIG[cliente_nombre].get("hoja_excel", cliente_nombre)
            if hoja_cliente in xls_cargado.sheet_names:
                df_feeds = pd.read_excel(xls_cargado, sheet_name=hoja_cliente)
                logger(f"✅ Hoja del cliente '{hoja_cliente}' cargada correctamente.")
            else:
                logger(f"⚠️ No se encontró la hoja '{hoja_cliente}' en el Excel del Drive.")

            hoja_gacetillas = next((s for s in xls_cargado.sheet_names if "gacetilla" in remover_acentos(s.lower())), None)
            if hoja_gacetillas:
                df_gacetillas = pd.read_excel(xls_cargado, sheet_name=hoja_gacetillas)
                GACETILLAS_CACHE = df_gacetillas
                logger(f"✅ Hoja de Gacetillas ('{hoja_gacetillas}') cargada correctamente.")

            hoja_globales = next((s for s in xls_cargado.sheet_names if "feeds globales" in remover_acentos(s.lower()) or "feed global" in remover_acentos(s.lower()) or "globales" in remover_acentos(s.lower())), None)
            if hoja_globales:
                df_feeds_globales = pd.read_excel(xls_cargado, sheet_name=hoja_globales)
                logger(f"✅ Hoja de Feeds Globales ('{hoja_globales}') cargada correctamente.")
                
            logger("✅ Base de Medios sincronizada correctamente.")
    except Exception as e:
        logger(f"⚠️ No se pudo descargar la Base de Medios: {e}")
    return df_medios, df_feeds, df_gacetillas, df_feeds_globales

def extraer_todos_rss_excel(df_feeds):
    if df_feeds is None or df_feeds.empty:
        return []
    urls_encontradas = []
    for col in df_feeds.columns:
        for val in df_feeds[col].dropna():
            v_str = str(val).strip()
            if v_str.startswith("http"):
                urls_encontradas.append(v_str)
    return list(dict.fromkeys(urls_encontradas))

def extraer_feeds_globales(df_globales):
    if df_globales is None or df_globales.empty:
        return []
    urls_encontradas = []
    primer_col = df_globales.columns[0]
    for val in df_globales[primer_col].dropna():
        v_str = str(val).strip()
        if v_str.startswith("http"):
            urls_encontradas.append(v_str)
    return list(dict.fromkeys(urls_encontradas))

# v5.84: lector del Word compartido: toma SOLO los links hipervinculados debajo de cada cliente y sección
WORD_CLIENTES_TITULO = {'Arredo': 'arredo', 'Amanco Wavin': 'amanco', 'BMS': 'bristol', 'Booking': 'booking', 'Mars': 'mars', 'MSD Salud Animal': 'msd', 'Mail Boxes': 'mail box'}
WORD_ALIAS_SECCION = {'rrhh': 'recursos humanos', 'noticias generales': 'noticias de interes'}
WORD_DOMINIOS_IGNORADOS = ('docs.google.com', 'drive.google.com')

def _norm_word(t):
    t = unicodedata.normalize('NFD', str(t).lower())
    t = ''.join(c for c in t if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', t).strip()

def leer_links_word(ruta, cliente_nombre, secciones):
    """Devuelve (links_por_seccion {sec_id: [urls]}, sin_seccion [urls], error)."""
    import zipfile, shutil, tempfile
    import xml.etree.ElementTree as ET
    W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
    try:
        tmp = os.path.join(tempfile.gettempdir(), 'clipping_word_tmp.docx')
        if str(ruta).lower().startswith('http'):  # v5.85: acepta link de Google Docs / Drive (con acceso "cualquiera con el link")
            _m = re.search(r'/(?:document|file)/d/([A-Za-z0-9_-]+)', ruta)
            if not _m: return {}, [], "El link no parece ser de Google Docs/Drive."
            _id = _m.group(1)
            _url = f"https://docs.google.com/document/d/{_id}/export?format=docx" if '/document/d/' in ruta else f"https://drive.google.com/uc?export=download&id={_id}"
            _r = requests.get(_url, timeout=60)
            if _r.status_code != 200 or not _r.content.startswith(b'PK'):
                return {}, [], "No se pudo descargar el documento. Verificá que el acceso sea 'Cualquier persona con el enlace'."
            open(tmp, 'wb').write(_r.content)
        else:
            shutil.copyfile(ruta, tmp)
        z = zipfile.ZipFile(tmp)
        doc = ET.fromstring(z.read('word/document.xml'))
        rels = {r.get('Id'): r.get('Target') for r in ET.fromstring(z.read('word/_rels/document.xml.rels'))}
        estilos = {}
        if 'word/styles.xml' in z.namelist():
            for st in ET.fromstring(z.read('word/styles.xml')).iter(W + 'style'):
                n = st.find(W + 'name')
                if n is not None: estilos[st.get(W + 'styleId')] = (n.get(W + 'val') or '').lower()
        z.close()
    except Exception as e:
        return {}, [], f"No se pudo leer el Word: {e}"
    kw = WORD_CLIENTES_TITULO.get(cliente_nombre, _norm_word(cliente_nombre))
    secs = [(s['id'], _norm_word(s['nombre'])) for s in secciones if not s.get('es_separador')]
    res, sin_sec = {}, []
    en_cliente, sec_act = False, None
    for p in doc.iter(W + 'p'):
        ps = p.find(W + 'pPr/' + W + 'pStyle')
        estilo = estilos.get(ps.get(W + 'val'), (ps.get(W + 'val') or '').lower()) if ps is not None else ''
        texto = ''.join(t.text or '' for t in p.iter(W + 't')).strip()
        if estilo in ('title', 'titulo', 'título'):
            en_cliente = kw in _norm_word(texto); sec_act = None
            continue
        if not en_cliente: continue
        links = []
        for h in p.iter(W + 'hyperlink'):
            rid = h.get(R + 'id')
            u = rels.get(rid, '') if rid else ''
            if u.lower().startswith('http') and not any(d in u.lower() for d in WORD_DOMINIOS_IGNORADOS): links.append(u.strip())
        if links:
            if sec_act: res.setdefault(sec_act, []).extend(links)
            else: sin_sec.extend(links)
            continue
        n = _norm_word(texto)
        for a, b in WORD_ALIAS_SECCION.items():
            if n.startswith(a): n = b + ' ' + n
        mejor, mejor_len = None, 0
        for sid, nom in secs:
            if n.startswith(nom) or (len(nom) >= 6 and n.startswith(nom[:6].strip())):
                if len(nom) > mejor_len: mejor, mejor_len = sid, len(nom)
        if mejor: sec_act = mejor
    for k in res:
        vistos = set(); res[k] = [u for u in res[k] if not (u in vistos or vistos.add(u))]
    return res, sin_sec, None

# v5.86: velocidad: resolver links de Google News sin navegador, lectura previa con requests y bloqueo de recursos pesados
_CACHE_GNEWS = {}
_UA_RAPIDO = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36", "Accept-Language": "es-AR,es;q=0.9"}
_BLOQUEAR_RECURSOS = ("image", "media", "font")
_BLOQUEAR_DOMINIOS = ("doubleclick.net", "googlesyndication.com", "google-analytics.com", "googletagmanager.com", "facebook.net", "connect.facebook.com", "hotjar.com", "taboola.com", "outbrain.com", "adsystem.com")

def bloquear_recursos_pesados(route):
    try:
        req = route.request
        if req.resource_type in _BLOQUEAR_RECURSOS or any(d in req.url for d in _BLOQUEAR_DOMINIOS):
            return route.abort()
        return route.continue_()
    except Exception:
        try: route.continue_()
        except Exception: pass

def resolver_google_news(url):
    """Devuelve la URL real de un link de Google News sin abrir el navegador (o None si no se pudo)."""
    if url in _CACHE_GNEWS: return _CACHE_GNEWS[url]
    res = None
    try:
        import base64
        m = re.search(r'/(?:rss/)?articles/([^?/]+)', url)
        if m and 'news.google.' in url:
            gid = m.group(1)
            b = base64.urlsafe_b64decode(gid + '=' * (-len(gid) % 4))
            if b.startswith(b'\x08\x13\x22'): b = b[3:]
            if b.endswith(b'\xd2\x01\x00'): b = b[:-3]
            ln = b[0]
            txt = (b[2:ln + 1] if ln >= 0x80 else b[1:ln + 1]).decode('utf-8', 'ignore')
            if txt.startswith('http'):
                res = txt
            elif txt.startswith('AU_yqL'):
                r = None
                for u_art in (f"https://news.google.com/articles/{gid}", f"https://news.google.com/rss/articles/{gid}"):
                    r = requests.get(u_art, headers=_UA_RAPIDO, timeout=6)
                    d = BeautifulSoup(r.text, 'html.parser').select_one('c-wiz > div[jscontroller]')
                    if d and d.get('data-n-a-sg'): break
                    d = None
                if d:
                    req_in = ["Fbv4je", f'["garturlreq",[["X","X",["X","X"],null,null,1,1,"US:en",null,1,null,null,null,null,null,0,1],"X","X",1,[1,1,1],1,1,null,0,0,null,0],"{d.get("data-n-a-id")}",{d.get("data-n-a-ts")},"{d.get("data-n-a-sg")}"]']
                    payload = "f.req=" + urllib.parse.quote(json.dumps([[req_in]]))
                    rp = requests.post("https://news.google.com/_/DotsSplashUi/data/batchexecute", headers={"content-type": "application/x-www-form-urlencoded;charset=UTF-8", "User-Agent": _UA_RAPIDO["User-Agent"]}, data=payload, timeout=8)
                    cand = json.loads(json.loads(rp.text.split("\n\n")[1])[:-2][0][2])[1]
                    if str(cand).startswith('http'): res = cand
    except Exception:
        res = None
    _CACHE_GNEWS[url] = res
    return res

def navegar_rapido(page, link):
    """Intenta cargar la nota con una descarga simple + página sin recursos. Devuelve True si usó la vía rápida; si no, navega normal."""
    try:
        destino = resolver_google_news(link) if 'news.google.' in link else link
        if destino and destino.startswith('http'):
            r = requests.get(destino, headers=_UA_RAPIDO, timeout=8)
            ct = r.headers.get('content-type', '')
            if r.status_code == 200 and 'html' in ct.lower():
                html = r.text
                texto_p = ' '.join(p.get_text(' ', strip=True) for p in BeautifulSoup(html, 'html.parser').find_all('p'))
                if len(texto_p) >= 700:
                    objetivo = destino.split('#')[0].rstrip('/')
                    def _h(route):
                        rq = route.request
                        if rq.resource_type == 'document' and rq.url.split('#')[0].rstrip('/') == objetivo:
                            return route.fulfill(status=200, content_type='text/html; charset=utf-8', body=html)
                        return route.abort()
                    page.route("**/*", _h)
                    page.goto(destino, timeout=15000, wait_until="domcontentloaded")
                    return True
    except Exception:
        pass
    try: page.unroute("**/*")
    except Exception: pass
    page.goto(link, timeout=15000, wait_until="domcontentloaded")
    return False

def fecha_y_dominio_nota(ev):
    """v5.88: texto gris para la pantalla de revisión: fecha de la nota y dominio con el que termina."""
    bd = ev.get('bloque_data') or {}
    fecha = str(bd.get('fecha', '') or '').strip() or 'sin fecha'
    dom = ''
    for c in (ev.get('link_destino'), bd.get('link_destino'), bd.get('url_fuente'), ev.get('link')):
        try:
            h = urlparse(str(c or '')).netloc.lower().replace('www.', '')
            if h and 'google.' not in h:
                dom = h; break
        except Exception:
            pass
    return f"📅 {fecha}  ·  🌐 {dom or 'dominio no disponible'}"

def procesar_seccion(context, sec_id, nombre_seccion, items_rss_preasignados, links_manuales, notas_graficas_sec, palabras_clave, exclusiones, color_tema, limite_notas, logger, cliente_nombre, df_medios, timeframe_google, links_sumados_global, urls_resueltas_global, historial_previo, titulos_resueltos_global, start_time_seccion, solo_manuales=False, contexto_ia=""):
    items = []
    evaluaciones_auditoria = []
    notas_pendientes_ia = []
    secciones_destacadas = ['exclusivas', 'mars_tema_1', 'mars_tema_2', 'mars_tema_3', 'bms_tema_1', 'arredo_tema_1', 'arredo_tema_2', 'amanco_tema_1', 'booking_tema_1', 'mars_competencia', 'bms_tema_4', 'arredo_tema_6', 'amanco_tema_2', 'booking_tema_2', 'mailboxes_tema_1', 'mailboxes_tema_2']  # v5.47

    # v5.46: en estas secciones NO se excluye por nota ya incluida en otra sección (sí se sigue excluyendo la repetida dentro de la propia sección)
    _nom_sec = remover_acentos(str(nombre_seccion).lower()).strip()
    omitir_duplicados = _nom_sec in ("exclusivas", "competencia", "competencias") or (cliente_nombre == "Mars" and _nom_sec in ("corporativo", "pet nutrition", "snacking"))
    # Foto de lo ya registrado al entrar: lo que esté ahí (de otras secciones) no cuenta como duplicado; lo que se sume dentro de esta sección sí
    _base_links = set(links_sumados_global) if omitir_duplicados else set()
    _base_urls = set(urls_resueltas_global) if omitir_duplicados else set()
    _base_tits = set(titulos_resueltos_global) if omitir_duplicados else set()
    _es_dup_link = lambda k: k in links_sumados_global and k not in _base_links
    _es_dup_url = lambda k: k in urls_resueltas_global and k not in _base_urls
    _es_dup_tit = lambda k: k in titulos_resueltos_global and k not in _base_tits

    requiere_ia = USAR_FILTRO_IA and (es_seccion_general(sec_id, nombre_seccion) or bool(contexto_ia))
    
    if links_manuales:
        logger(f"  ➜ Procesando {len(links_manuales)} link(s) manuales...")
        for url_manual in reversed(links_manuales):
            items.append((ObjetoManual(url_manual, "Nota Manual", ""), 'Manual', 'manual'))

    if items_rss_preasignados and not solo_manuales:
        for it_tuple in items_rss_preasignados:
            if len(it_tuple) == 3:
                items.append(it_tuple)
            elif len(it_tuple) == 2:
                items.append((it_tuple[0], it_tuple[1], 'general'))
            else:
                items.append((it_tuple[0], 'Desconocido', 'general'))

    noticias_procesadas = []

    for ng in notas_graficas_sec:
        m_limpio = limpiar_nombre_medio(ng['medio'])
        fecha_format = datetime.datetime.strptime(ng['fecha'], "%Y-%m-%d").strftime("%d/%m/%Y") if ng.get('fecha') else datetime.datetime.now().strftime("%d/%m/%Y")
        alcance, tier, ad_value = buscar_metricas_medio(df_medios, ng['link'], m_limpio)
        alcance, tier, ad_value = [str(ng.get(k_, '')).strip() or v_ for k_, v_ in (('alcance', alcance), ('tier', tier), ('ad_value', ad_value))]  # v5.43: valores cargados a mano pisan la búsqueda

        bloque_ng = {
            "medio": m_limpio, "tipo_medio": "Gráfica", "fecha": fecha_format,
            "alcance": alcance, "tier": tier, "ad_value": ad_value, "titulo": ng['titulo'], "link": ng['link'],
            "bajada_real": ng['bajada'], "oracion_clave": ng['bajada'], "origen": "grafica"
        }

        link_norm = str(ng['link']).strip().lower()
        u_clean = url_limpia_para_duplicados(ng['link'])

        if False:  # v5.58: el historial NO afecta a notas manuales (gráficas)
            logger(f"    📜 EXCLUIDA [Gráfica] por historial anterior del cliente: {m_limpio[:20]} - {ng['titulo'][:30]}...")
            if True:
                evaluaciones_auditoria.append({
                    "medio": m_limpio, "titulo": ng['titulo'], "link": ng['link'],
                    "estado": "EXCLUIDA_HISTORIAL", "motivo": "Nota ya publicada en un clipping de días anteriores", "es_ia": False,
                    "origen_fuente": "Gráfica", "bloque_data": bloque_ng
                })
            continue

        if (link_norm and _es_dup_link(link_norm)) or _es_dup_url(u_clean):  # v5.46
            logger(f"    🔁 EXCLUIDA [Gráfica] por nota duplicada: {m_limpio[:20]} - {ng['titulo'][:30]}...")
            if True:
                evaluaciones_auditoria.append({
                    "medio": m_limpio, "titulo": ng['titulo'], "link": ng['link'],
                    "estado": "EXCLUIDA_DUPLICADA", "motivo": "Nota ya ingresada en otra sección del reporte actual", "es_ia": False,
                    "origen_fuente": "Gráfica", "bloque_data": bloque_ng
                })
            continue

        noticias_procesadas.append(bloque_ng)
        if link_norm: links_sumados_global.add(link_norm)
        urls_resueltas_global.add(u_clean)

        evaluaciones_auditoria.append({
            "medio": m_limpio, "titulo": ng['titulo'], "link": ng['link'],
            "estado": "SUMADA", "motivo": "Nota Gráfica ingresada manualmente", "es_ia": False,
            "origen_fuente": "Gráfica", "bloque_data": bloque_ng
        })
        logger(f"    ✓ SUMADA [Gráfica]: {m_limpio[:20]} - {ng['titulo'][:30]}...")

    organicas_ok = 0
    _feed_prev = None
    _excl_sec = set()
    _aud_idx = 0
    _term_act = ''
    _n_busq = max(1, sum(1 for _k in FEED_TERMINOS if str(_k).startswith(f"google_{sec_id}_")))
    _tope_busqueda = max(MAX_NOTAS_POR_BUSQUEDA, -(-int(limite_notas) // _n_busq))
    _es_google = False
    _aprob_term = {}
    _excl_claves = set(); _idx_ev = 0  # v5.75: notas ya excluidas en otra búsqueda de esta sección
    organicas_por_feed = {}
    notas_por_medio = {}
    def _cupo_ok(nota):  # v5.58: Booking Turismo: máximo 5 notas por sitio (consume cupo si hay lugar)
        if sec_id != 'booking_tema_3': return True
        k_ = str(nota.get('medio', '')).strip().lower()
        if notas_por_medio.get(k_, 0) >= 5: return False
        notas_por_medio[k_] = notas_por_medio.get(k_, 0) + 1
        return True
    vistos_urls_seccion = set()
    vistos_titulos_seccion = set()
    repetidas_seccion = 0

    if aplica_filtro_ar(cliente_nombre, sec_id):
        def _prio_item(t):
            if t[1] == 'Manual': return -1
            if t[1] != 'Google News': return -0.5  # v5.34: nicho/Excel/gacetilla/extras siempre antes que Google News
            try:
                med = t[0].source.text if getattr(t[0], 'source', None) is not None else ""
                return 0 if es_diario_ar_prioritario(med, t[0].link.text) else 1
            except Exception: return 1
        items.sort(key=_prio_item)  # sort estable: respeta el orden previo dentro de cada grupo

    for item_tuple in items:
        if getattr(state, 'stop_req', False): break  # v5.50: entrega parcial
        # --- NUEVO: CHECK DE PAUSA (Congela y descuenta tiempo) ---
        if getattr(state, 'is_paused', False):
            inicio_pausa = time.time()
            while getattr(state, 'is_paused', False) and not getattr(state, 'stop_req', False):
                time.sleep(0.5)
            # Sumamos los segundos que estuvo pausado para NO perjudicar el límite
            start_time_seccion += (time.time() - inicio_pausa)
        if getattr(state, 'stop_req', False): break  # v5.50
        # ----------------------------------------------------------

        if time.time() - start_time_seccion > 180:  # v5.72: límite por sección de 3 minutos
            logger(f"    ⏳ ¡Tiempo límite alcanzado! Interrumpiendo búsqueda de nuevas notas en esta sección.")
            break

        item = item_tuple[0]
        origen = item_tuple[1]
        feed_id = item_tuple[2]
        if origen != 'Manual' and feed_id != _feed_prev:  # v5.67: indicador de búsqueda actual y aprobadas x/límite
            _feed_prev = feed_id
            _term_act = FEED_TERMINOS.get(feed_id, str(feed_id))
            _es_google = (origen == 'Google News')  # v5.77: solo se informa en búsquedas de Google
            if _es_google:
                logger(f"§RSS|{_term_act}")
                logger(f"  🔎 Extrayendo de: [{_term_act}] | Aprobadas en esta búsqueda: {_aprob_term.get(_term_act, 0)}")
        
        if origen != 'Manual':  # v5.75: si ya se excluyó en otra búsqueda de la misma sección, se omite directo
            for _ev in evaluaciones_auditoria[_idx_ev:]:
                if str(_ev.get('estado', '')).startswith('EXCLUIDA'):
                    _excl_claves.add(str(_ev.get('link', '')).strip().lower())
            _idx_ev = len(evaluaciones_auditoria)
            try:
                _lk = item.link.text.strip().lower()
            except Exception:
                _lk = ''
            if _lk and _lk in _excl_claves:
                continue

        if origen != 'Manual' and organicas_ok >= limite_notas:
            logger(f"    ⏹️ ¡Límite global de {limite_notas} notas alcanzado! Se interrumpe la búsqueda en esta sección.")
            break
            
        if origen == 'Google News' and cliente_nombre not in CLIENTES_SIN_TOPE_BUSQUEDA and sec_id not in SECCIONES_SIN_TOPE_BUSQUEDA:  # v5.80: tope por búsqueda = max(3, límite de la sección / cantidad de búsquedas)
            if _aprob_term.get(FEED_TERMINOS.get(feed_id, feed_id), 0) >= _tope_busqueda:
                continue

        link_orig = item.link.text
        link_norm = link_orig.strip().lower()
        for _ev in evaluaciones_auditoria[_aud_idx:]:  # v5.75: nota ya excluida en otra búsqueda de esta sección -> se omite directo
            if str(_ev.get('estado', '')).startswith('EXCLUIDA'): _excl_sec.add(str(_ev.get('link', '')).strip().lower())
        _aud_idx = len(evaluaciones_auditoria)
        if origen != 'Manual' and link_norm in _excl_sec:
            continue
        titulo_bruto = item.title.text if item.title else "Sin Título"
        desc_rss = item.description.text if hasattr(item, 'description') and item.description else ""
        fecha_rss_raw = item.pubDate.text if hasattr(item, 'pubDate') and item.pubDate else ""
        fecha_rss = formatear_fecha(fecha_rss_raw)

        if origen != 'Manual':
            titulo = limpiar_titulo(titulo_bruto)
        else:
            titulo = titulo_bruto

        medio = item.source.text if hasattr(item, 'source') and item.source and item.source.text != "Manual" else urlparse(link_orig).netloc.replace("www.", "").split('.')[0].capitalize()

        if origen != 'Manual':
            clave_url = url_limpia_para_duplicados(link_orig)
            clave_titulo = (re.sub(r'[^a-z0-9]', '', remover_acentos(titulo.lower())),
                            re.sub(r'[^a-z0-9]', '', remover_acentos(str(medio).lower())))
            if (clave_url and clave_url in vistos_urls_seccion) or (clave_titulo[0] and clave_titulo in vistos_titulos_seccion):
                repetidas_seccion += 1
                continue
            if clave_url: vistos_urls_seccion.add(clave_url)
            if clave_titulo[0]: vistos_titulos_seccion.add(clave_titulo)

        url_fuente = obtener_url_fuente_rss(item)

        _al_pre, _ti_pre, _ad_pre = buscar_metricas_medio(df_medios, url_fuente or link_orig, medio)  # v5.52: métricas también para notas excluidas antes de leerse
        bloque_pre = {
            "medio": limpiar_nombre_medio(medio), "tipo_medio": "Online", "fecha": fecha_rss, "leida": False,
            "alcance": _al_pre, "tier": _ti_pre, "ad_value": _ad_pre, "titulo": titulo, "link": link_orig,
            "bajada_real": desc_rss, "oracion_clave": desc_rss, "resumen_rss": desc_rss, "origen": origen,
            "url_fuente": url_fuente
        }

        if origen not in ('Manual', 'Manual Online') and link_norm and link_norm in historial_previo:  # v5.58: solo afecta a notas de feed/Google
            logger(f"    📜 EXCLUIDA por historial anterior del cliente: {medio[:20]} - {titulo[:30]}...")
            _, tier_test, _ = buscar_metricas_medio(df_medios, link_orig, medio)
            if True:
                evaluaciones_auditoria.append({
                    "medio": medio, "titulo": titulo, "link": link_orig,
                    "estado": "EXCLUIDA_HISTORIAL", "motivo": "Nota ya publicada en un clipping de días anteriores", "es_ia": False,
                    "origen_fuente": origen, "bloque_data": bloque_pre
                })
            continue

        t_compact_pre = re.sub(r'[^a-z0-9]', '', remover_acentos(titulo.lower()))
        
        if (link_norm and _es_dup_link(link_norm)) or (t_compact_pre and _es_dup_tit(t_compact_pre) and len(t_compact_pre) > 15):  # v5.46
            logger(f"    🔁 EXCLUIDA por nota duplicada (URL origen o Título): {medio[:20]} - {titulo[:30]}...")
            _, tier_test, _ = buscar_metricas_medio(df_medios, link_orig, medio)
            if True:
                evaluaciones_auditoria.append({
                    "medio": medio, "titulo": titulo, "link": link_orig,
                    "estado": "EXCLUIDA_DUPLICADA", "motivo": "La nota o el título exacto ya fue incluido en otra sección o de forma manual", "es_ia": False,
                    "origen_fuente": origen, "bloque_data": bloque_pre
                })
            continue

        if origen != 'Manual' and not es_fecha_en_rango(fecha_rss_raw, timeframe_google):
            logger(f"    📅 EXCLUIDA por antigüedad (> {timeframe_google}): {medio[:20]} - {titulo[:30]}...")
            _, tier_test, _ = buscar_metricas_medio(df_medios, link_orig, medio)
            if True:
                evaluaciones_auditoria.append({
                    "medio": medio, "titulo": titulo, "link": link_orig,
                    "estado": "EXCLUIDA_FECHA", "motivo": f"Excede el rango de tiempo seleccionado ({timeframe_google})", "es_ia": False,
                    "origen_fuente": origen, "bloque_data": bloque_pre
                })
            continue

        if origen != 'Manual':
            texto_pre = f"{titulo} {desc_rss}"
            _, tier_test, _ = buscar_metricas_medio(df_medios, link_orig, medio)
            es_top_tier = True

            if sec_id in IDS_EXCLUIR_TIER3 and str(tier_test).lower().replace('tier', '').strip() in ('3', '3.0'):  # v5.66
                logger(f"    🚫 EXCLUIDA por Tier 3: {medio[:20]} - {titulo[:30]}...")
                evaluaciones_auditoria.append({
                    "medio": medio, "titulo": titulo, "link": link_orig,
                    "estado": "EXCLUIDA_TIER_3", "motivo": "Tier 3", "es_ia": False,
                    "origen_fuente": origen, "bloque_data": bloque_pre
                })
                continue

            motivo_extr = motivo_portal_extranjero(link_orig, medio, texto_pre, url_fuente)
            if motivo_extr:
                logger(f"    🌎 EXCLUIDA por portal extranjero [{motivo_extr}]: {medio[:20]} ({link_orig})")
                if es_top_tier:
                    evaluaciones_auditoria.append({
                        "medio": medio, "titulo": titulo, "link": link_orig,
                        "estado": "EXCLUIDA_EXTRANJERO", "motivo": f"Portal o dominio identificado como extranjero ({motivo_extr})", "es_ia": False,
                        "origen_fuente": origen, "bloque_data": bloque_pre
                    })
                continue

            if sec_id in SECCIONES_FILTRO_AR_ESTRICTO_RSS and aplica_filtro_ar(cliente_nombre, sec_id) \
               and not es_sitio_permitido_ar(link_orig, medio, texto_pre):
                logger(f"    🌎 EXCLUIDA [Competencia] sitio no argentino (sin leer nota): {medio[:20]} ({link_orig})")
                evaluaciones_auditoria.append({
                    "medio": medio, "titulo": titulo, "link": link_orig,
                    "estado": "EXCLUIDA_EXTRANJERO", "motivo": "Sitio no argentino (Competencia, sin leer nota)", "es_ia": False,
                    "origen_fuente": origen, "bloque_data": bloque_pre
                })
                continue

            if contiene_exclusion(texto_pre, exclusiones):
                logger(f"    ⛔ EXCLUIDA por filtro de exclusiones: {medio[:20]} - {titulo[:30]}...")
                if es_top_tier:
                    evaluaciones_auditoria.append({
                        "medio": medio, "titulo": titulo, "link": link_orig,
                        "estado": "EXCLUIDA_EXCLUSION", "motivo": "Contiene términos en lista de exclusión", "es_ia": False,
                        "origen_fuente": origen, "bloque_data": bloque_pre
                    })
                continue

        origen_str = origen
        logger(f"    🔎 Revisando [{origen_str}]: {medio[:20]} - {titulo[:30]}...")
        
        page = context.new_page()
        bajada, oracion, fecha_web, link_destino = "", "", "", link_orig
        fecha_debil = ""
        
        try:
            _rapido = navegar_rapido(page, link_orig)  # v5.86
            page.wait_for_timeout(250 if _rapido else 1200)
            if page.url and re.search(r'//(news|consent)\.google\.', page.url):
                try:
                    page.wait_for_url(lambda u: not re.search(r'//(news|consent)\.google\.', u), timeout=5000)
                except Exception:
                    pass
            if page.url:
                link_destino = page.url
                if origen != 'Manual':
                    logger(f"    🔗 Destino: {link_destino}")
                
            u_clean = url_limpia_para_duplicados(link_destino)
            if _es_dup_url(u_clean):  # v5.46
                logger(f"    🔁 EXCLUIDA por url de destino duplicada: {medio[:20]} - {titulo[:30]}...")
                _, tier_test, _ = buscar_metricas_medio(df_medios, link_orig, medio)
                if True:
                    evaluaciones_auditoria.append({
                        "medio": medio, "titulo": titulo, "link": link_orig, "link_destino": link_destino,
                        "estado": "EXCLUIDA_DUPLICADA", "motivo": "La url destino exacta ya fue procesada (Ej: carga manual)", "es_ia": False,
                        "origen_fuente": origen, "bloque_data": bloque_pre
                    })
                try: page.close() 
                except: pass
                continue
            
            try:
                page.evaluate('''
                    document.querySelectorAll('aside, footer, nav, .sidebar, .widget, [class*="sidebar"], [id*="sidebar"], [class*="related"], [class*="popular"], [class*="trending"], [class*="most-read"], [class*="recomendado"]').forEach(el => el.remove());
                ''')
            except: pass

            t_web = page.title()
            
            if t_web:
                t_clean = limpiar_titulo(t_web)
                if titulo in ["Manual", "Nota Manual"]:
                    titulo = t_clean if t_clean else "Nota Manual"
                    domain = urlparse(page.url).netloc.lower()
                    if 'instagram.com' not in domain and 'facebook.com' not in domain and 'x.com' not in domain and 'twitter.com' not in domain: 
                        medio = urlparse(page.url).netloc.replace("www.", "").split('.')[0].capitalize()
            
            bajada = obtener_resumen_metadata(page)
            _cand_f = _candidatos_fecha(page)
            fecha_web = obtener_fecha_metadata(page, _cand_f)
            if not fecha_web: fecha_debil = obtener_fecha_debil(page, page.url, _cand_f)
            # v5.40: todas las notas (no manuales ni redes): la keyword se busca también en el CUERPO de la página (antes solo título + bajada)
            if (origen != 'Manual' or str(sec_id) in IDS_EXCLUSIVAS or str(sec_id) in IDS_COMPETENCIA) and not oracion and not any(rs in link_destino.lower() for rs in ['instagram.com', 'facebook.com', 'x.com', 'twitter.com']):
                try:
                    _cuerpo = page.evaluate("() => (document.querySelector('article') || document.body).innerText")
                    oracion = extraer_oracion_clave(_sin_titulo(_cuerpo or "", titulo), palabras_clave, sec_id)
                    if not oracion:
                        _cuerpo = page.evaluate("() => document.body.innerText")
                        oracion = extraer_oracion_clave(_sin_titulo(_cuerpo or "", titulo), palabras_clave, sec_id)
                except Exception:
                    pass
                if not oracion:  # v5.52: la página puede no haber terminado de cargar: espera, scrollea y reintenta una vez
                    try:
                        page.mouse.wheel(0, 4000); page.wait_for_timeout(2500)
                        for _sel in ("(document.querySelector('article') || document.body).innerText", "document.body.innerText"):
                            oracion = extraer_oracion_clave(_sin_titulo(page.evaluate("() => " + _sel) or "", titulo), palabras_clave, sec_id)
                            if oracion: break
                    except Exception:
                        pass
            
            # --- NUEVA LÓGICA REDES SOCIALES ---
            domain_url = urlparse(link_destino).netloc.lower()
            
            if any(rs in domain_url for rs in ['instagram.com', 'facebook.com', 'x.com', 'twitter.com']):
                nombre_usuario = ""
                texto_post = ""
                # Si IG bloquea la lectura web, bajada estará vacía. Usamos desc_rss (que trae Google News) como salvavidas.
                texto_meta = bajada if (bajada and len(bajada) > 10) else (desc_rss if 'desc_rss' in locals() else "")
                
                if 'instagram.com' in domain_url and texto_meta:
                    # Extrae el usuario aislando lo que hay entre el guion y el primer espacio
                    m_user = re.search(r'-\s*([a-zA-Z0-9_.]+)\s+', texto_meta)
                    if m_user: nombre_usuario = m_user.group(1)
                    
                    # Extrae el texto del post (todo lo que está entre comillas al final)
                    m_text = re.search(r':\s*"(.*?)"?$', texto_meta, re.DOTALL)
                    if m_text: texto_post = m_text.group(1).strip()
                
                # Respaldo visual por si el salvavidas falla
                try:
                    rs_data = page.evaluate('''() => {
                        let data = {user: '', text: ''};
                        let userEl = document.querySelector('header a, h2, h3, h1 a');
                        if (userEl) data.user = userEl.innerText.trim();
                        let textEl = document.querySelector('h1, article div[role="button"] + div span'); 
                        if (textEl) data.text = textEl.innerText.trim();
                        return data;
                    }''')
                    if rs_data:
                        if not nombre_usuario and rs_data.get('user'): nombre_usuario = rs_data['user']
                        if not texto_post and rs_data.get('text'): texto_post = rs_data['text']
                except:
                    pass
                
                if nombre_usuario:
                    medio = nombre_usuario
                elif origen == 'Manual':
                    medio = "Instagram"
                
                if texto_post:
                    texto_limpio = " ".join(texto_post.split())
                    # Eliminamos el límite de caracteres para que la oración salga completa
                    titulo = texto_limpio 
                    if not oracion: oracion = texto_post 
            # ------------------------------------------------------------------
                
        except Exception as e:
            if origen != 'Manual': 
                logger(f"    ❌ EXCLUIDA por error al acceder a la web: {medio[:20]} - {titulo[:30]}...")
                _, tier_test, _ = buscar_metricas_medio(df_medios, link_orig, medio)
                if True:
                    evaluaciones_auditoria.append({
                        "medio": medio, "titulo": titulo, "link": link_orig, "link_destino": link_destino,
                        "estado": "EXCLUIDA_ERROR", "motivo": f"Inaccesible o error web: {str(e)}", "es_ia": False,
                        "origen_fuente": origen, "bloque_data": bloque_pre
                    })
                try: page.close() 
                except: pass
                continue
            logger(f"    ⚠️ Forzada [{origen_str}]: {titulo[:30]}")
            
        try: page.close()
        except: pass

        u_clean = url_limpia_para_duplicados(link_destino)
        
        is_social = any(rs in link_destino.lower() for rs in ['instagram.com', 'facebook.com', 'x.com', 'twitter.com'])
        
        # TRUCO: Si mandamos la URL "instagram.com", el buscador hace match con el tier genérico de "Instagram" 
        # y frena. Al ocultarle la URL, lo obligamos a buscar SOLO por el nombre del usuario (ej: revistamercado).
        url_busqueda_excel = "" if (is_social and medio.lower() != "instagram") else (page.url if 'page' in locals() and page else link_orig)
        
        alcance, tier, ad_value = buscar_metricas_medio(df_medios, url_busqueda_excel, medio)
        fecha_final = fecha_web or fecha_rss or fecha_debil or fecha_sin_dato()  # v5.80

        # --- CONSTRUCCIÓN DEL BLOQUE ---
        # Si es red social, conservamos los guiones bajos originales (ej: revista_mercado) para la interfaz visual.
        medio_final = medio if (is_social and medio.lower() != "instagram") else limpiar_nombre_medio(medio)

        bloque_noticia = {
            "medio": medio_final, "tipo_medio": "Online", "fecha": fecha_final,
            "alcance": alcance, "tier": tier, "ad_value": ad_value, "titulo": titulo, "link": link_orig,
            "link_destino": link_destino,
            "bajada_real": bajada, "oracion_clave": oracion, "resumen_rss": item.description.text if hasattr(item, 'description') and item.description else "", "origen": origen
        }

        t_compact_post = re.sub(r'[^a-z0-9]', '', remover_acentos(titulo.lower()))

        if origen != 'Manual':
            texto_eval = f"{titulo} {bajada} {oracion}"
            es_top_tier = True

            motivo_extr = motivo_portal_extranjero(link_destino, medio, texto_eval, url_fuente)
            if motivo_extr:
                logger(f"    🌎 EXCLUIDA por portal extranjero [{motivo_extr}]: {medio[:20]}...")
                if es_top_tier:
                    evaluaciones_auditoria.append({
                        "medio": medio, "titulo": titulo, "link": link_orig, "link_destino": link_destino,
                        "estado": "EXCLUIDA_EXTRANJERO", "motivo": f"Contenido o portal identificado como extranjero ({motivo_extr})", "es_ia": False,
                        "origen_fuente": origen, "bloque_data": bloque_noticia
                    })
                continue

            if aplica_filtro_ar(cliente_nombre, sec_id) and not es_sitio_permitido_ar(link_destino, medio, texto_eval):
                logger(f"    🌎 EXCLUIDA por sitio no argentino: {medio[:20]} ({link_destino})")
                if es_top_tier:
                    evaluaciones_auditoria.append({
                        "medio": medio, "titulo": titulo, "link": link_orig, "link_destino": link_destino,
                        "estado": "EXCLUIDA_EXTRANJERO", "motivo": "Sitio no argentino (no .ar, no está en lista permitida y no habla de Argentina)", "es_ia": False,
                        "origen_fuente": origen, "bloque_data": bloque_noticia
                    })
                continue

            if contiene_exclusion(texto_eval, exclusiones):
                logger(f"    ⛔ EXCLUIDA por filtro de exclusiones: {medio[:20]} - {titulo[:30]}...")
                if es_top_tier:
                    evaluaciones_auditoria.append({
                        "medio": medio, "titulo": titulo, "link": link_orig, "link_destino": link_destino,
                        "estado": "EXCLUIDA_EXCLUSION", "motivo": "Término excluido detectado en contenido", "es_ia": False,
                        "origen_fuente": origen, "bloque_data": bloque_noticia
                    })
                continue

            if not contiene_palabra_clave(texto_eval, palabras_clave):
                logger(f"    🔍 EXCLUIDA por no coincidir palabras clave: {medio[:20]} - {titulo[:30]}...")
                if es_top_tier:
                    evaluaciones_auditoria.append({
                        "medio": medio, "titulo": titulo, "link": link_orig, "link_destino": link_destino,
                        "estado": "EXCLUIDA_KEYWORD", "motivo": "Palabra clave no presente en contenido visible", "es_ia": False,
                        "origen_fuente": origen, "bloque_data": bloque_noticia
                    })
                continue
            
            if requiere_ia:
                cache_key = f"{sec_id}_{link_norm}"
                if cache_key in CACHE_IA_SESION:
                    es_rel, motivo_ia = CACHE_IA_SESION[cache_key]
                    if not es_rel:
                        logger(f"    🤖 EXCLUIDA por IA (Caché Rápida): {medio[:20]} - {titulo[:30]}... ({motivo_ia})")
                        if es_top_tier:
                            evaluaciones_auditoria.append({
                                "medio": medio, "titulo": titulo, "link": link_orig, "link_destino": link_destino,
                                "estado": "EXCLUIDA_IA", "motivo": motivo_ia, "es_ia": True,
                                "origen_fuente": origen, "bloque_data": bloque_noticia
                            })
                        continue
                else:
                    notas_pendientes_ia.append({
                        "id": len(notas_pendientes_ia),
                        "texto": texto_eval,
                        "nota_info": bloque_noticia,
                        "link_norm": link_norm,
                        "medio": medio,
                        "titulo": titulo,
                        "link_orig": link_orig,
                        "link_destino": link_destino,
                        "origen": origen,
                        "es_top_tier": es_top_tier,
                        "t_compact_post": t_compact_post
                    })
                    
                    # --- NUEVO: EVALUACIÓN EN CALIENTE (Lotes de 6) ---
                    if len(notas_pendientes_ia) >= 6:
                        logger(f"    📦 Evaluando lote rápido de {len(notas_pendientes_ia)} notas en caliente...")
                        resultados_lote = evaluar_relevancia_ia_lotes(notas_pendientes_ia, cliente_nombre, nombre_seccion, palabras_clave, exclusiones, logger, contexto_ia)
                        
                        for item_ia in notas_pendientes_ia:
                            n_id = str(item_ia['id'])
                            es_rel, motivo_ia = resultados_lote.get(n_id, (True, "Filtro IA no disponible"))
                            
                            cache_key = f"{sec_id}_{item_ia['link_norm']}"
                            CACHE_IA_SESION[cache_key] = (es_rel, motivo_ia)
                            
                            if not es_rel:
                                logger(f"    🤖 EXCLUIDA por IA: {item_ia['medio'][:20]} - {item_ia['titulo'][:30]}... ({motivo_ia})")
                                if item_ia['es_top_tier']:
                                    evaluaciones_auditoria.append({
                                        "medio": item_ia['medio'], "titulo": item_ia['titulo'], "link": item_ia['link_orig'], "link_destino": item_ia['link_destino'],
                                        "estado": "EXCLUIDA_IA", "motivo": motivo_ia, "es_ia": True,
                                        "origen_fuente": item_ia['origen'], "bloque_data": item_ia['nota_info']
                                    })
                            else:
                                if organicas_ok < limite_notas and _cupo_ok(item_ia['nota_info']):
                                    noticias_procesadas.append(item_ia['nota_info'])
                                    if item_ia['link_norm']: links_sumados_global.add(item_ia['link_norm'])
                                    
                                    u_clean_lote = url_limpia_para_duplicados(item_ia['link_destino'])
                                    urls_resueltas_global.add(u_clean_lote)
                                    
                                    if item_ia['t_compact_post'] and len(item_ia['t_compact_post']) > 15:
                                        titulos_resueltos_global.add(item_ia['t_compact_post'])

                                    evaluaciones_auditoria.append({
                                        "medio": limpiar_nombre_medio(item_ia['medio']), "titulo": item_ia['titulo'], "link": item_ia['link_orig'], "link_destino": item_ia['link_destino'],
                                        "estado": "SUMADA", "motivo": "Aprobada por IA (en caliente)", "es_ia": False,
                                        "origen_fuente": item_ia['origen'], "bloque_data": item_ia['nota_info']
                                    })
                                    logger(f"    ✓ SUMADA [{item_ia['origen']}]: {item_ia['medio'][:20]} - {item_ia['titulo'][:30]}...")
                                    organicas_ok += 1
                                    _aprob_term[_term_act] = _aprob_term.get(_term_act, 0) + 1; (logger(f"    📊 [{_term_act}] aprobadas en esta búsqueda: {_aprob_term[_term_act]}") if _es_google else None); logger(f"§PROG|{nombre_seccion}|{organicas_ok}|{limite_notas}")  # v5.69
                                else:
                                    logger(f"    ⏹️ OMITIDA por límite alcanzado: {item_ia['medio'][:20]}...")
                                    
                        # Vaciamos la lista para procesar el siguiente lote
                        notas_pendientes_ia = []
                    # --------------------------------------------------
                    continue 
                    
        if origen != 'Manual' and not _cupo_ok(bloque_noticia):
            logger(f"    ⏹️ OMITIDA por tope de 5 notas del sitio: {medio[:20]}...")
            continue
        noticias_procesadas.append(bloque_noticia)
        if link_norm: links_sumados_global.add(link_norm)
        urls_resueltas_global.add(u_clean)
        
        if t_compact_post and len(t_compact_post) > 15:
            titulos_resueltos_global.add(t_compact_post)

        evaluaciones_auditoria.append({
            "medio": limpiar_nombre_medio(medio), "titulo": titulo, "link": link_orig, "link_destino": link_destino,
            "estado": "SUMADA", "motivo": "Aprobada e incluida en reporte", "es_ia": False,
            "origen_fuente": origen, "bloque_data": bloque_noticia
        })
        logger(f"    ✓ SUMADA [{origen_str}]: {medio[:20]} - {titulo[:30]}...")
        
        if origen != 'Manual': 
            organicas_ok += 1
            _aprob_term[_term_act] = _aprob_term.get(_term_act, 0) + 1; (logger(f"    📊 [{_term_act}] aprobadas en esta búsqueda: {_aprob_term[_term_act]}") if _es_google else None); logger(f"§PROG|{nombre_seccion}|{organicas_ok}|{limite_notas}")  # v5.69
            organicas_por_feed[feed_id] = organicas_por_feed.get(feed_id, 0) + 1

    if repetidas_seccion:
        logger(f"    ♻️ {repetidas_seccion} nota(s) repetida(s) entre los feeds de esta sección: se evaluaron una sola vez.")

    if notas_pendientes_ia:
        # --- ORDENAR Y LIMITAR A 15 NOTAS ---
        def prioridad_ia(nota):
            ni = nota['nota_info']
            vacios = ['?', 'nan', '', 'null', 'none']
            # Prioridad 1: el medio figura en el Excel (tiene tier, alcance o ad value cargado)
            en_excel = 1 if any(str(ni.get(k, '?')).strip().lower() not in vacios for k in ('tier', 'alcance', 'ad_value')) else 0
            # Prioridad 2: sitio argentino (dominio .ar)
            try: host = urlparse(str(nota['link_destino'])).netloc.lower().split(':')[0]
            except Exception: host = ""
            es_ar = 1 if (host.endswith('.ar') or '.ar.' in host) else 0
            es_prio = 1 if (aplica_filtro_ar(cliente_nombre, sec_id) and es_diario_ar_prioritario(nota['medio'], nota['link_destino'])) else 0
            return (es_prio, en_excel, es_ar)
            
        notas_pendientes_ia.sort(key=prioridad_ia, reverse=True)
        
        if len(notas_pendientes_ia) > LIMITE_POOL_IA:
            logger(f"    ✂️️ Recortando pool de IA: de {len(notas_pendientes_ia)} a {LIMITE_POOL_IA} notas (priorizando Excel y sitios locales).")
            descartadas = notas_pendientes_ia[LIMITE_POOL_IA:]
            notas_pendientes_ia = notas_pendientes_ia[:LIMITE_POOL_IA]
            
            for item in descartadas:
                logger(f"    ⏹️ OMITIDA por límite de IA (Max {LIMITE_POOL_IA}): {item['medio'][:20]} - {item['titulo'][:30]}...")
                if item['es_top_tier']:
                    evaluaciones_auditoria.append({
                        "medio": item['medio'], "titulo": item['titulo'], "link": item['link_orig'], "link_destino": item['link_destino'],
                        "estado": "EXCLUIDA_LIMITE_IA", "motivo": f"Excluida para no superar el límite de {LIMITE_POOL_IA} consultas IA por sección", "es_ia": False,
                        "origen_fuente": item['origen'], "bloque_data": item['nota_info']
                    })
        # ------------------------------------------

        logger(f"    📦 Evaluando {len(notas_pendientes_ia)} notas pendientes con IA (Por Lotes)...")
        batch_size = 6
        for i in range(0, len(notas_pendientes_ia), batch_size):
            lote = notas_pendientes_ia[i:i+batch_size]
            resultados_lote = evaluar_relevancia_ia_lotes(lote, cliente_nombre, nombre_seccion, palabras_clave, exclusiones, logger, contexto_ia)
            
            for item in lote:
                n_id = str(item['id'])
                es_rel, motivo_ia = resultados_lote.get(n_id, (True, "Filtro IA no disponible"))
                
                cache_key = f"{sec_id}_{item['link_norm']}"
                CACHE_IA_SESION[cache_key] = (es_rel, motivo_ia)
                
                if not es_rel:
                    logger(f"    🤖 EXCLUIDA por IA (*): {item['medio'][:20]} - {item['titulo'][:30]}... ({motivo_ia})")
                    if item['es_top_tier']:
                        evaluaciones_auditoria.append({
                            "medio": item['medio'], "titulo": item['titulo'], "link": item['link_orig'], "link_destino": item['link_destino'],
                            "estado": "EXCLUIDA_IA", "motivo": motivo_ia, "es_ia": True,
                            "origen_fuente": item['origen'], "bloque_data": item['nota_info']
                        })
                else:
                    if organicas_ok < limite_notas and _cupo_ok(item['nota_info']):
                        noticias_procesadas.append(item['nota_info'])
                        if item['link_norm']: links_sumados_global.add(item['link_norm'])
                        
                        u_clean_lote = url_limpia_para_duplicados(item['link_destino'])
                        urls_resueltas_global.add(u_clean_lote)
                        
                        if item['t_compact_post'] and len(item['t_compact_post']) > 15:
                            titulos_resueltos_global.add(item['t_compact_post'])

                        evaluaciones_auditoria.append({
                            "medio": limpiar_nombre_medio(item['medio']), "titulo": item['titulo'], "link": item['link_orig'], "link_destino": item['link_destino'],
                            "estado": "SUMADA", "motivo": "Aprobada por IA Lotes e incluida en reporte", "es_ia": False,
                            "origen_fuente": item['origen'], "bloque_data": item['nota_info']
                        })
                        logger(f"    ✓ SUMADA [{item['origen']}]: {item['medio'][:20]} - {item['titulo'][:30]}...")
                        organicas_ok += 1
                        _aprob_term[_term_act] = _aprob_term.get(_term_act, 0) + 1; (logger(f"    📊 [{_term_act}] aprobadas en esta búsqueda: {_aprob_term[_term_act]}") if _es_google else None); logger(f"§PROG|{nombre_seccion}|{organicas_ok}|{limite_notas}")  # v5.69
                    else:
                        logger(f"    ⏹️ OMITIDA por límite alcanzado post-IA: {item['medio'][:20]}...")

    notas_manuales = [n for n in noticias_procesadas if n['origen'] in ['Manual', 'grafica']]
    notas_google = [n for n in noticias_procesadas if n['origen'] not in ['Manual', 'grafica']]

    notas_manuales = sorted(notas_manuales, key=lambda n: sort_key_final(n, sec_id))
    notas_google = sorted(notas_google, key=lambda n: sort_key_final(n, sec_id))

    noticias_finales = sorted(notas_manuales + notas_google, key=lambda n: sort_key_final(n, sec_id))  # v5.53: un solo orden

    for noti in noticias_finales:
        # 1. Armamos el bloque de texto normal por defecto
        bloque_texto = construir_bloque_texto(noti['bajada_real'], noti['oracion_clave'], noti['titulo'], palabras_clave, sec_id, noti.get('resumen_rss', ''))
        
        etiqueta_tipo = noti['tipo_medio']
        if etiqueta_tipo == "Online":
            medio_eval = str(noti['medio']).lower()
            link_eval = str(noti.get('link', '')).lower()
            link_dest = str(noti.get('link_destino', '')).lower()
            if "instagram" in medio_eval or "instagram.com" in link_eval or "instagram.com" in link_dest:
                etiqueta_tipo = "IG"
            elif "facebook" in medio_eval or "facebook.com" in link_eval or "facebook.com" in link_dest:
                etiqueta_tipo = "FB"
            elif "twitter" in medio_eval or "x.com" in link_eval or "twitter.com" in link_eval or "x.com" in link_dest or "twitter.com" in link_dest:
                etiqueta_tipo = "X"
                
        # --- NUEVO: Borrar el texto inferior si es una Red Social ---
        if etiqueta_tipo in ["IG", "FB", "X"]:
            bloque_texto = ""
        # ------------------------------------------------------------
            
        tipo_html = f" <strong style='color: {color_tema}; font-size: 14px; font-family: Tahoma, sans-serif;'>({etiqueta_tipo})</strong> " if noti['tipo_medio'] != "Gráfica" else " "
        
        if sec_id == 'booking_tema_1':
            info_metricas = f" <strong style='color: {color_tema}; font-size: 14px; font-family: Tahoma, sans-serif;'>Ad. Value: $ {noti['ad_value']}</strong> -"
        elif sec_id in IDS_SINTESIS and sec_id not in IDS_SIN_METRICAS:
            info_metricas = f" <span style='color: {color_tema}; font-size: 14px; font-family: Tahoma, sans-serif;'>(Alcance: {noti['alcance']} Tier: {noti['tier']})</span> <strong style='color: {color_tema}; font-size: 14px; font-family: Tahoma, sans-serif;'>Ad. Value: $ {noti['ad_value']}</strong> -"
        else:
            info_metricas = " -"
            
        html_indiv = f'''<p style="margin-top: 0; margin-bottom: 4px; color: #000000;"><strong style="color: {color_tema}; font-size: 14px;">{noti['medio']}</strong>{tipo_html}<strong style="color: {color_tema}; font-size: 14px;">{noti['fecha']}</strong>{info_metricas} <a href="{noti['link']}" target="_blank" rel="noopener noreferrer" style="color: {color_tema}; text-decoration: none; font-size: 14px; font-weight: normal;">{noti['titulo']}</a></p>{bloque_texto}'''
        
        noti['html_bloque'] = html_indiv

    return noticias_finales, evaluaciones_auditoria

def orquestador_principal(links_manuales, notas_graficas, configuracion_cliente, cliente_nombre, logger, timeframe_google, busquedas_extra=None, solo_manuales=False, solo_banners=False):
    color = configuracion_cliente["color_primario"]
    estructura = configuracion_cliente["secciones"]
    excl_cliente_extra = configuracion_cliente.get('temas_excluir', [])
    if excl_cliente_extra:  # v5.37: se suman a las exclusiones de TODAS las secciones
        estructura = [s_ if s_.get('es_separador') else {**s_, 'exclusiones': list(dict.fromkeys(list(s_.get('exclusiones', [])) + excl_cliente_extra))} for s_ in estructura]
        logger(f"🚫 Temas excluidos por el cliente: {', '.join(excl_cliente_extra)}")
    data_editor = []
    data_auditoria = []
    links_sumados_global = set()
    urls_resueltas_global = set()
    titulos_resueltos_global = set()
    historial_previo = cargar_historial_cliente(cliente_nombre)

    if historial_previo:
        logger(f"📜 Se cargaron {len(historial_previo)} notas registradas en el historial antiduplicados exclusivo para '{cliente_nombre}'.")

    if solo_banners:
        logger("⚡ Modo Dios: Prueba Rápida activada (Generando únicamente banners vacíos)...")
        for sec in estructura:
            img_url = transformar_link_drive(sec.get('img_url', ''))
            data_editor.append({
                "id": sec['id'], "nombre": sec['nombre'], "img": img_url,
                "incluir_en_sintesis": sec['id'] in IDS_SINTESIS, "resumen_ia": "",
                "es_separador": sec.get('es_separador', False), "notas": []
            })
            data_auditoria.append({"id": sec['id'], "nombre": sec['nombre_largo'], "evaluaciones": []})
        return data_editor, data_auditoria

    df_medios, df_feeds, df_gacetillas, df_feeds_globales = sincronizar_base_medios(cliente_nombre, logger)
    
    items_rss_por_seccion = {sec['id']: [] for sec in estructura if not sec.get('es_separador')}
    # v5.36: en las secciones "Exclusivas" (exclusiones propias casi vacías) el prefiltro de RSS usa la unión de TODAS las exclusiones del cliente
    todas_excl_cliente = list(dict.fromkeys(ex for s_ in estructura if not s_.get('es_separador') for ex in s_.get('exclusiones', [])))
    excl_por_seccion = {sec['id']: (todas_excl_cliente if remover_acentos(str(sec.get('nombre', '')).lower()).strip() == 'exclusivas' else sec.get('exclusiones', [])) for sec in estructura}
    descartadas_fecha_excel = 0
    
    if not solo_manuales and df_gacetillas is not None:
        gacetilla_texto = extraer_gacetilla_mas_reciente(df_gacetillas, cliente_nombre)
        if gacetilla_texto:
            logger(f"📰 Gacetilla más reciente encontrada para {cliente_nombre}: '{gacetilla_texto}'")
            q_gacetilla = urllib.parse.quote(gacetilla_texto)
            url_gacetilla_rss = f"https://news.google.com/rss/search?q=%22{q_gacetilla}%22%20when%3A{timeframe_google}%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419"
            
            sec_dest = estructura[0]['id'] if estructura else None
            if sec_dest:
                try:
                    req = urllib.request.urlopen(urllib.request.Request(url_gacetilla_rss, headers={'User-Agent': 'Mozilla/5.0'}))
                    soup = BeautifulSoup(req.read(), "xml")
                    tuplas_gac = [(it, 'Gacetilla Excel', 'gacetilla') for it in soup.find_all('item')[:20]]
                    items_rss_por_seccion[sec_dest].extend(aplicar_prefiltro_rss(tuplas_gac, timeframe_google, excl_por_seccion.get(sec_dest, []), df_medios, logger, "Gacetilla"))
                    logger(f"  ✅ Búsqueda RSS de Gacetilla agregada a la sección '{estructura[0]['nombre']}' con timeframe {timeframe_google}.")
                except Exception as e:
                    logger(f"  ⚠️ Error al procesar RSS de Gacetilla: {e}")

    if busquedas_extra and not solo_manuales:
        logger("🔍 Procesando Búsquedas Extra configuradas...")
        mapa_secciones = {remover_acentos(s['nombre'].lower()): s['id'] for s in estructura if not s.get('es_separador')}
        mapa_secciones.update({s['id'].lower(): s['id'] for s in estructura if not s.get('es_separador')})

        for i, extra in enumerate(busquedas_extra):
            q_texto = extra.get('q', '').strip()
            sec_target = str(extra.get('sec', '')).strip()
            if not q_texto:
                continue

            sec_id_destino = mapa_secciones.get(remover_acentos(sec_target.lower())) or mapa_secciones.get(sec_target.lower())
            if not sec_id_destino and estructura:
                sec_id_destino = estructura[0]['id']

            q_encoded = urllib.parse.quote(q_texto)
            url_extra_rss = f"https://news.google.com/rss/search?q={q_encoded}%20when%3A{timeframe_google}%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419"
            
            try:
                logger(f"  🔍 Búsqueda Extra [{q_texto}] -> Sección ID: {sec_id_destino}")
                req = urllib.request.urlopen(urllib.request.Request(url_extra_rss, headers={'User-Agent': 'Mozilla/5.0'}))
                soup = BeautifulSoup(req.read(), "xml")
                items_extra = soup.find_all('item')[:20]
                feed_id_extra = f"extra_{i}"
                tuplas_extra = [(it, 'Búsqueda Extra', feed_id_extra) for it in items_extra]
                items_rss_por_seccion[sec_id_destino].extend(aplicar_prefiltro_rss(tuplas_extra, timeframe_google, excl_por_seccion.get(sec_id_destino, []), df_medios, logger, f"Extra [{q_texto}]"))
            except Exception as e:
                logger(f"  ⚠️ Error al consultar Búsqueda Extra ({q_texto}): {e}")

    if not solo_manuales:
        rss_excel_nicho = extraer_todos_rss_excel(df_feeds) if df_feeds is not None and not df_feeds.empty else []
        rss_excel_globales = extraer_feeds_globales(df_feeds_globales) if df_feeds_globales is not None and not df_feeds_globales.empty else []
        
        rss_excel_todos = list(dict.fromkeys(rss_excel_nicho + rss_excel_globales))

        if rss_excel_todos:
            logger(f"📊 Analizando {len(rss_excel_todos)} fuentes de Excel (Nicho + Feeds Globales) para clasificar notas por sección...")
            for i, url_feed in enumerate(rss_excel_todos):
                url_ajustada = url_feed.replace("when:1d", f"when:{timeframe_google}").replace("when%3A1d", f"when%3A{timeframe_google}")
                try:
                    req = urllib.request.urlopen(urllib.request.Request(url_ajustada, headers={'User-Agent': 'Mozilla/5.0'}))
                    soup = BeautifulSoup(req.read(), "xml")
                    feed_id_excel = f"excel_{i}"
                    for it in soup.find_all('item')[:20]:
                        # v5.35: rango de fechas ANTES de clasificar/redirigir a secciones
                        if prefiltrar_item_rss(it, timeframe_google, None, df_medios) == "fecha":
                            descartadas_fecha_excel += 1
                            continue
                        tit = it.title.text if it.title else ""
                        desc = it.description.text if it.description else ""
                        texto_combo = f"{tit} {desc}"
                        _ce = it.find('content:encoded') or it.find('encoded')
                        _cuerpo_feed = BeautifulSoup(_ce.text, "html.parser").get_text(" ") if _ce is not None and _ce.text else ""
                        
                        link_it = it.link.text if hasattr(it, 'link') and it.link and it.link.text else url_feed
                        source_it = it.source.text if hasattr(it, 'source') and it.source and it.source.text else urlparse(link_it).netloc.replace("www.", "").split('.')[0]
                        sitio_origen = limpiar_nombre_medio(source_it)

                        # v5.38: Exclusivas se evalúa PRIMERO y con sus exclusiones propias (no la unión del cliente): cualquier mención va ahí
                        _es_excl = lambda s_: remover_acentos(str(s_.get('nombre', '')).lower()).strip() == 'exclusivas'
                        for sec in sorted([x for x in estructura if not x.get('es_separador', False)], key=lambda x: 0 if _es_excl(x) else 1):
                            _excl_sec = sec.get('exclusiones', []) if _es_excl(sec) else excl_por_seccion.get(sec['id'], [])
                            # v5.39: la mención puede estar solo en el cuerpo del feed (content:encoded)
                            _texto_kw = f"{texto_combo} {_cuerpo_feed}"  # v5.39: todas las secciones buscan también en el cuerpo del feed
                            if contiene_palabra_clave(_texto_kw, sec['keywords']) and not contiene_exclusion(texto_combo, _excl_sec):
                                items_rss_por_seccion[sec['id']].append((it, 'Feed Excel', feed_id_excel))
                                logger(f"  🔀 Feed Excel [{sitio_origen}]: Nota '{tit[:30]}...' redirigida a 📁 {sec['nombre']}")
                                break
                except Exception: pass

    if descartadas_fecha_excel:
        logger(f"  🧹 Prefiltro Feeds Excel: {descartadas_fecha_excel} nota(s) fuera del rango ({timeframe_google}) descartadas antes de redirigir a secciones.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled", "--no-sandbox"])
        context = browser.new_context(viewport={"width": 1920, "height": 1080}, user_agent="Mozilla/5.0")
        context.route("**/*", bloquear_recursos_pesados)  # v5.86: no descarga imágenes, videos, fuentes ni trackers
        
        for sec in estructura:
            # --- NUEVO: CHECK DE PAUSA ENTRE SECCIONES ---
            while getattr(state, 'is_paused', False) and not getattr(state, 'stop_req', False):
                time.sleep(0.5)
            if getattr(state, 'stop_req', False):
                logger("🛑 Entrega parcial solicitada: se omiten las secciones restantes.")  # v5.50
                break
            # ---------------------------------------------
            
            logger(f"\n🔎 ANALIZANDO SECCIÓN: {sec['nombre_largo']}")
            start_time_seccion = time.time()
            
            if sec.get('es_separador', False):
                img_url = transformar_link_drive(sec.get('img_url', ''))
                data_editor.append({
                    "id": sec['id'],
                    "nombre": sec['nombre'],
                    "img": img_url,
                    "incluir_en_sintesis": False,
                    "resumen_ia": "",
                    "es_separador": True,
                    "notas": []
                })
                data_auditoria.append({
                    "id": sec['id'],
                    "nombre": sec['nombre_largo'],
                    "evaluaciones": []
                })
                continue

            rss_ajustado = [enlace.replace("when:1d", f"when:{timeframe_google}").replace("when%3A1d", f"when%3A{timeframe_google}") for enlace in sec['rss']]
            
            rss_ajustado = [enlace.replace("when:1d", f"when:{timeframe_google}").replace("when%3A1d", f"when%3A{timeframe_google}") for enlace in sec['rss']]
            
            items_rss_seccion = []
            if not solo_manuales:
                for i, url_busqueda in enumerate(rss_ajustado):
                    # --- NUEVO: Decodificar la URL para mostrar el nombre de la búsqueda en el log ---
                    try:
                        parsed_url = urllib.parse.urlparse(url_busqueda)
                        qs = urllib.parse.parse_qs(parsed_url.query)
                        termino_busqueda = qs.get('q', [''])[0]
                        # Limpiamos los tags de tiempo para que se lea mejor
                        termino_busqueda = urllib.parse.unquote(termino_busqueda).split(' when:')[0].replace('+', ' ').strip()
                        if not termino_busqueda: termino_busqueda = f"Feed RSS {i+1}"
                    except:
                        termino_busqueda = f"Feed RSS {i+1}"

                    logger(f"  📡 Consultando RSS: [{termino_busqueda}]")
                    
                    try:
                        req = urllib.request.urlopen(urllib.request.Request(url_busqueda, headers={'User-Agent': 'Mozilla/5.0'}))
                        feed_id_google = f"google_{sec['id']}_{i}"
                        FEED_TERMINOS[feed_id_google] = termino_busqueda
                        
                        items_extraidos = BeautifulSoup(req.read(), "xml").find_all('item')[:30]
                        
                        # --- NUEVO: Avisar cuántas notas sacó de este feed ---
                        if items_extraidos:
                            logger(f"    ✅ Se extrajeron {len(items_extraidos)} notas en bruto de este feed.")
                            def _rank_tier(_it):  # v5.66: dentro de cada búsqueda, primero tier 1 y 2, luego sin tier, al final tier 3
                                try:
                                    _m = _it.source.text if _it.source else ''
                                    _t = str(buscar_metricas_medio(df_medios, '', _m)[1]).lower().replace('tier', '').strip()
                                    return 0 if _t in ('1', '2', '1.0', '2.0') else (2 if _t in ('3', '3.0') else 1)
                                except Exception:
                                    return 1
                            items_extraidos = sorted(items_extraidos, key=_rank_tier)
                            for it in items_extraidos: 
                                items_rss_seccion.append((it, 'Google News', feed_id_google))
                        else:
                            logger(f"    ⚠️ No hay notas nuevas en este feed.")
                            
                    except Exception as e:
                        logger(f"    ❌ Falló la conexión a este RSS: {e}")

            # v5.35: rango de fechas + exclusiones de la sección antes de procesar/IA
            items_rss_seccion = aplicar_prefiltro_rss(items_rss_seccion, timeframe_google, excl_por_seccion.get(sec['id'], []), df_medios, logger, "Google News")

            # v5.34: primero las notas redirigidas desde sitios de nicho (Feed Excel/gacetilla/extras); recién después Google News de la sección
            items_rss_nicho = items_rss_por_seccion.get(sec['id'], [])
            items_rss_totales = items_rss_nicho + items_rss_seccion
            if items_rss_nicho:
                logger(f"  🎯 {len(items_rss_nicho)} nota(s) de nicho se filtran primero; luego {len(items_rss_seccion)} de Google News/RSS.")
            
            notas_seccion, eval_sec = procesar_seccion(
                context, sec['id'], sec['nombre'], items_rss_totales, 
                links_manuales.get(sec['id'], []), notas_graficas.get(sec['id'], []),
                sec['keywords'], sec.get('exclusiones', []), color, limite_ajustado(sec['limite'], timeframe_google), logger, cliente_nombre, df_medios, timeframe_google, links_sumados_global, urls_resueltas_global, historial_previo, titulos_resueltos_global, start_time_seccion, solo_manuales=solo_manuales, contexto_ia=sec.get('contexto_ia', "")
            )

            img_url = transformar_link_drive(sec.get('img_url', ''))

            data_editor.append({
                "id": sec['id'], 
                "nombre": sec['nombre'], 
                "img": img_url,
                "incluir_en_sintesis": sec['id'] in IDS_SINTESIS,
                "resumen_ia": "",
                "es_separador": False, "metricas": tipo_metricas(sec['id']),
                "notas": [{"html_bloque": n.get('html_bloque', ''), "alcance": n.get('alcance', '?'), "tier": n.get('tier', '?'), "ad_value": n.get('ad_value', '?'), "medio": n.get('medio', ''), "tipo_medio": n.get('tipo_medio', ''), "fecha": n.get('fecha', ''), "link": n.get('link', ''), "link_destino": n.get('link_destino', '')} for n in notas_seccion]
            })
            
            data_auditoria.append({
                "id": sec['id'],
                "nombre": sec['nombre_largo'],
                "evaluaciones": eval_sec
            })

        context.close()
        browser.close()
    
    return data_editor, data_auditoria

# ====================================================================
# GENERADOR HTML DE AUDITORÍA Y CONTROL
# ====================================================================
def generar_html_auditoria(cliente_nombre, timeframe, data_auditoria, color):
    fecha_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    total_sumadas = sum(sum(1 for e in sec['evaluaciones'] if e['estado'] == 'SUMADA') for sec in data_auditoria)
    total_ia = sum(sum(1 for e in sec['evaluaciones'] if e.get('es_ia')) for sec in data_auditoria)
    total_excluidas = sum(sum(1 for e in sec['evaluaciones'] if e['estado'] != 'SUMADA') for sec in data_auditoria)

    html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <title>Auditoría y Control de Clipping - {cliente_nombre}</title>
    <style>
        body {{ font-family: 'Tahoma', sans-serif; background-color: #f1f5f9; color: #1e293b; margin: 0; padding: 24px; }}
        .header {{ background-color: {color}; color: #ffffff; padding: 24px; border-radius: 12px; margin-bottom: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
        .header h1 {{ margin: 0 0 8px 0; font-size: 22px; }}
        .header p {{ margin: 0; font-size: 13px; opacity: 0.9; }}
        .stats {{ display: flex; gap: 16px; margin-top: 16px; }}
        .stat-card {{ background: rgba(255,255,255,0.15); padding: 10px 16px; border-radius: 8px; font-size: 12px; font-weight: bold; }}
        .seccion {{ background: #ffffff; border-radius: 12px; padding: 20px; margin-bottom: 20px; border: 1px solid #cbd5e1; box-shadow: 0 2px 6px rgba(0,0,0,0.02); }}
        .seccion-title {{ font-size: 16px; font-weight: bold; color: {color}; padding-bottom: 6px; cursor: pointer; outline: none; list-style: none; }}
        .seccion-title::-webkit-details-marker {{ display: none; }}
        .table {{ width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 12px; }}
        .table th {{ background: #f8fafc; text-align: left; padding: 10px; border-bottom: 2px solid #cbd5e1; color: #475569; }}
        .table td {{ padding: 10px; border-bottom: 1px solid #e2e8f0; vertical-align: top; }}
        .badge {{ display: inline-block; padding: 3px 8px; border-radius: 12px; font-size: 10px; font-weight: bold; text-transform: uppercase; }}
        .badge-sumada {{ background: #dcfce7; color: #166534; }}
        .badge-ia {{ background: #f3e8ff; color: #6b21a8; border: 1px solid #d8b4fe; }}
        .badge-excluido {{ background: #ffe4e6; color: #9f1239; }}
        .motivo-ia {{ background: #faf5ff; border-left: 3px solid #a855f7; padding: 6px 10px; margin-top: 4px; font-size: 11px; color: #581c87; border-radius: 0 4px 4px 0; }}
        .fuente-tag {{ color: #64748b; font-style: italic; font-size: 11px; margin-top: 2px; display: block; }}
        a {{ color: #0284c7; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        details[open] summary {{ border-bottom: 2px solid #e2e8f0; margin-bottom: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Reporte de Control y Auditoría de Clipping</h1>
        <p>Cliente: <strong>{cliente_nombre}</strong> | Fecha de Proceso: <strong>{fecha_str}</strong> | Rango Búsqueda: <strong>{timeframe}</strong></p>
        <div class="stats">
            <div class="stat-card">✅ Sumadas al Reporte: {total_sumadas}</div>
            <div class="stat-card">🤖 Excluidas por IA (*): {total_ia}</div>
            <div class="stat-card">🚫 Excluidas Totales (Tier 1/2): {total_excluidas}</div>
        </div>
    </div>
'''

    for sec in data_auditoria:
        html += f'''
    <div class="seccion">
        <details open>
            <summary class="seccion-title">
                📁 {sec['nombre']}
                <span style="font-size: 11px; color: #64748b; font-weight: normal; float: right; margin-top: 4px;">🔽 Clic para plegar/desplegar</span>
            </summary>
            <div>
'''
        if not sec['evaluaciones']:
            html += '<p style="color: #64748b; font-size: 12px; font-style: italic; padding-top: 10px;">Sin notas evaluadas en esta sección.</p>'
        else:
            evals_ordenadas = sorted(
                sec['evaluaciones'],
                key=lambda e: (
                    0 if e['estado'] == 'SUMADA' else 1,
                    str(e.get('estado', '')) if e['estado'] != 'SUMADA' else '',
                    remover_acentos(str(e.get('medio', '')).lower()),
                    remover_acentos(str(e.get('titulo', '')).lower())
                )
            )
            html += '''
        <table class="table">
            <thead>
                <tr>
                    <th style="width: 15%;">Medio</th>
                    <th style="width: 45%;">Título y Enlace</th>
                    <th style="width: 15%;">Estado</th>
                    <th style="width: 25%;">Detalle / Motivo de Exclusión</th>
                </tr>
            </thead>
            <tbody>
'''
            for ev in evals_ordenadas:
                es_manual = ev.get('origen_fuente') in ['Manual', 'Gráfica', 'grafica', 'manual'] or 'manual' in str(ev.get('motivo','')).lower()

                if ev['estado'] == 'SUMADA':
                    badge_html = '<span class="badge badge-sumada">MANUAL</span>' if es_manual else ''
                elif ev.get('es_ia'):
                    badge_html = '<span class="badge badge-ia">IA</span>'
                else:
                    est_clean = str(ev['estado']).replace('EXCLUIDA_', '').replace('_', ' ')
                    badge_html = f'<span class="badge badge-excluido">{est_clean}</span>'

                fuente_str = ev.get("origen_fuente", "")
                fuente_html = f'<span class="fuente-tag">Fuente: {fuente_str}</span>' if (not ev['estado'] == 'SUMADA' and fuente_str) else ''

                motivo_html = ev['motivo']
                if ev.get('es_ia'):
                    motivo_html = f'<div class="motivo-ia"><strong>* Por qué se excluyó:</strong> {ev["motivo"]}{fuente_html}</div>'
                elif not ev['estado'] == 'SUMADA':
                    motivo_html = f'{ev["motivo"]}{fuente_html}'

                html += f'''
                <tr>
                    <td><strong>{ev['medio']}</strong></td>
                    <td><a href="{ev['link']}" target="_blank" rel="noopener noreferrer">{ev['titulo']}</a></td>
                    <td>{badge_html}</td>
                    <td>{motivo_html}</td>
                </tr>
'''
            html += '</tbody></table>'
        html += '</div></details></div>'

    html += '</body></html>'
    return html

# ====================================================================
# GENERADOR HTML QUILL.JS
# ====================================================================
def generar_html_editor(banner_url, sec_data, color, cliente_nombre):
    banner_limpio = transformar_link_drive(banner_url)
    report_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    plantilla = r'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Editor de Reporte (Quill.js)</title>
    <link href="https://cdn.quilljs.com/1.3.6/quill.snow.css" rel="stylesheet">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        :root{ --tema_color:__COLOR_CLIENTE__; --bg:#f4f4f9; }
        
        body { 
            font-family: 'Tahoma', 'Inter', sans-serif; 
            background-color: #f2f4f7;
            background-image: 
                radial-gradient(circle at 15% 15%, color-mix(in srgb, var(--tema_color) 12%, transparent) 0%, transparent 45%),
                radial-gradient(circle at 85% 85%, color-mix(in srgb, var(--tema_color) 8%, transparent) 0%, transparent 45%),
                radial-gradient(color-mix(in srgb, var(--tema_color) 10%, transparent) 1px, transparent 1px);
            background-size: 100% 100%, 100% 100%, 24px 24px;
            background-attachment: fixed;
            margin: 0; 
            padding: 0;
        }
        
        .sidebar-wrapper {
            width: 68px;
            height: 100vh;
            position: fixed;
            top: 0;
            left: 0;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-right: 1px solid #e2e8f0;
            padding: 20px 10px;
            box-shadow: 2px 0 12px rgba(0,0,0,0.05);
            z-index: 100;
            box-sizing: border-box;
            overflow-x: hidden;
            transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            white-space: nowrap;
        }
        .sidebar-wrapper:hover {
            width: 260px;
            box-shadow: 6px 0 24px rgba(0,0,0,0.12);
        }
        
        .sidebar-text {
            opacity: 0;
            transition: opacity 0.2s ease 0.05s;
            margin-left: 8px;
            display: inline-block;
            vertical-align: middle;
        }
        .sidebar-wrapper:hover .sidebar-text {
            opacity: 1;
        }
        
        .btn { border:none; border-radius:8px; font-size:12px; font-weight:bold; cursor:pointer; padding: 6px 10px; margin: 2px 0; display: inline-flex; align-items: center; }
        .btn-side { 
            width: 100%; 
            height: 42px; 
            padding: 0 12px; 
            font-size: 13px; 
            margin-bottom: 8px; 
            display: flex; 
            align-items: center; 
            justify-content: flex-start;
            box-sizing: border-box;
        }
        .btn-icon-symbol { font-size: 16px; width: 24px; text-align: center; flex-shrink: 0; }
        .btn-primary { background: var(--tema_color); color: white; }
        .btn-icon { background: #ffffff; color: #333; border: 1px solid #d1d5db; border-radius: 6px; }
        .btn-icon:hover { background: #f3f4f6; }
        .btn-icon.danger { color: #dc2626; border-color: #fca5a5; background: #fef2f2; }

        .contenedor-main {
            width: calc(100% - 68px);
            margin-left: 68px;
            box-sizing: border-box;
            display: flex;
            justify-content: center;
        }

        .contenedor {
            width: 100%;
            max-width: 700px;
            padding: 36px 20px 80px;
            margin: 0 auto;
            box-sizing: border-box;
        }
        
        .seccion { 
            background: rgba(255, 255, 255, 0.98); 
            border-radius: 18px; 
            margin-bottom: 24px; 
            box-shadow: 0 8px 24px rgba(0,0,0,0.06); 
            overflow: hidden; 
            border: 1px solid #e2e8f0;
            backdrop-filter: blur(4px);
        }

        .seccion-header { 
            position: relative;
            background: linear-gradient(120deg, var(--tema_color) 0%, color-mix(in srgb, var(--tema_color) 65%, #001a1c) 100%); 
            color: #ffffff; 
            padding: 14px 20px; 
            font-size: 15px;
            font-weight: 500; 
            font-style: italic; 
            display: flex; 
            justify-content: space-between; 
            align-items: center;
            overflow: hidden;
        }
        .seccion-header::after {
            content: '';
            position: absolute;
            top: -50%;
            right: -10%;
            width: 140px;
            height: 200%;
            background: rgba(255, 255, 255, 0.08);
            transform: rotate(20deg);
            pointer-events: none;
        }
        .seccion-header .count {
            font-weight: 600;
            font-style: normal;
            font-size: 12px;
            background: rgba(255, 255, 255, 0.22);
            padding: 4px 12px;
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(4px);
        }
        
        .sintesis-quill-box .ql-container.ql-snow {
            border: 1px solid #cbd5e1 !important;
            border-radius: 12px !important;
            background: #ffffff !important;
            padding: 10px 14px !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.02) !important;
        }
        .sintesis-quill-box .ql-editor {
            padding: 0 !important;
            font-family: 'Tahoma', sans-serif !important;
            font-size: 12px !important;
            color: #333333 !important;
            line-height: 1.5 !important;
        }
        .sintesis-quill-box .ql-editor p {
            font-family: 'Tahoma', sans-serif !important;
            font-size: 12px !important;
            color: #333333 !important;
            line-height: 1.5 !important;
            margin: 0 !important;
        }
        
        .bloque-nota { border-bottom: 1px dashed #e2e8f0; padding: 12px 16px 16px; position: relative; transition: background 0.2s; }
        .bloque-nota:hover { background: #fafafa; }

        .drag-handle { cursor: grab; color: #94a3b8; font-size: 18px; padding: 0 6px; user-select: none; }
        .drag-handle:active { cursor: grabbing; }

        .ql-container.ql-snow { border: none !important; font-family: 'Tahoma', sans-serif !important; }
        .ql-editor { font-family: 'Tahoma', sans-serif !important; padding: 4px 0 !important; line-height: 1.5 !important; }
        .ql-editor p { font-family: 'Tahoma', sans-serif !important; line-height: 1.5 !important; margin: 0 0 6px 0 !important; color: #000000 !important; }
        .ql-editor p:first-child { font-size: 14px !important; }
        .ql-editor p:not(:first-child) { font-size: 12px !important; }
        .ql-editor strong, .ql-editor b { font-family: 'Tahoma', sans-serif !important; }
        .ql-editor a { font-family: 'Tahoma', sans-serif !important; text-decoration: none !important; }
        
        .ql-toolbar.ql-snow { 
            border: none !important; 
            border-bottom: 1px solid #e2e8f0 !important; 
            background: #ffffff; 
            border-radius: 8px 8px 0 0; 
            padding: 4px 10px !important; 
            margin-bottom: 6px;
            display: flex !important;
            align-items: center !important;
            flex-wrap: wrap !important;
            gap: 4px !important;
        }
        .ql-toolbar.ql-snow .ql-formats {
            display: inline-flex !important;
            align-items: center !important;
            margin-right: 8px !important;
        }
        .ql-toolbar.ql-snow button:not(.btn-tool), .ql-toolbar.ql-snow .ql-picker-label {
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            float: none !important;
            height: 26px !important;
            width: 26px !important;
            padding: 2px !important;
        }
        .btn-tool {
            width: auto !important;
            height: 26px !important;
            padding: 2px 8px !important;
            font-size: 11px !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            box-sizing: border-box !important;
        }
        
        .modal-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.5); align-items: center; justify-content: center; z-index: 100; }
        .modal-frame { background: white; width: 80%; height: 80%; border-radius: 12px; display: flex; flex-direction: column; overflow:hidden;}
        #iframe-preview { flex: 1; border: none; width: 100%; }
    
        /* v5.82: mejoras visuales del editor */
        html { scroll-behavior: smooth; }
        ::selection { background: color-mix(in srgb, var(--tema_color) 25%, white); }
        ::-webkit-scrollbar { width: 10px; height: 10px; }
        ::-webkit-scrollbar-thumb { background: color-mix(in srgb, var(--tema_color) 35%, #cbd5e1); border-radius: 8px; border: 2px solid transparent; background-clip: padding-box; }
        ::-webkit-scrollbar-track { background: transparent; }
        @keyframes fadeUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
        .seccion { animation: fadeUp .35s ease both; transition: box-shadow .25s ease, transform .25s ease; border-radius: 16px; }
        .seccion:hover { box-shadow: 0 14px 34px rgba(0,0,0,0.10); }
        .seccion-header { font-style: normal !important; font-weight: 700 !important; letter-spacing: .3px; font-size: 15px; padding: 15px 22px !important; }
        .bloque-nota { border-radius: 12px !important; border-left: 4px solid color-mix(in srgb, var(--tema_color) 70%, white) !important; transition: box-shadow .2s ease, transform .2s ease, border-color .2s ease; }
        .bloque-nota:hover { box-shadow: 0 8px 22px rgba(0,0,0,0.09); transform: translateY(-2px); border-left-color: var(--tema_color) !important; }
        .btn { transition: transform .15s ease, box-shadow .15s ease, filter .15s ease, background .15s ease; }
        .btn:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.14); }
        .btn:active { transform: translateY(0); box-shadow: none; }
        .btn-primary:hover { filter: brightness(1.08); }
        .btn-side { border-radius: 10px !important; }
        .btn-side:hover { filter: brightness(0.96); transform: translateX(2px); }
        .ql-toolbar.ql-snow { position: sticky; top: 0; z-index: 20; background: rgba(255,255,255,0.96); backdrop-filter: blur(8px); border-radius: 10px 10px 0 0; }
        .ql-container.ql-snow:focus-within, .sintesis-quill-box .ql-container.ql-snow:focus-within { box-shadow: 0 0 0 2px color-mix(in srgb, var(--tema_color) 30%, transparent); border-radius: 0 0 10px 10px; }
        .modal-overlay { backdrop-filter: blur(6px); animation: fadeUp .2s ease both; }
        .modal-frame { border-radius: 16px !important; box-shadow: 0 24px 60px rgba(0,0,0,0.35) !important; overflow: hidden; }
        @media (max-width: 640px) {
            .sidebar-wrapper { width: 52px; padding: 14px 6px; }
            .sidebar-wrapper:hover { width: 230px; }
            .contenedor-main { width: calc(100% - 52px); margin-left: 52px; }
            .contenedor { padding: 20px 10px 60px; }
            .seccion-header { padding: 12px 14px !important; font-size: 14px; }
        }
    </style>
</head>
<body>
    <div class="sidebar-wrapper">
        <div style="display:flex; align-items:center; margin-bottom: 16px; overflow:hidden;">
            <span style="font-size:20px; flex-shrink:0; width:28px; text-align:center;">📑</span>
            <div class="sidebar-text">
                <h3 style="color:var(--tema_color); margin:0; font-size:15px;">Editor Dinámico</h3>
                <div id="contador-total" style="color: #666; font-size: 11px;"></div>
                <div id="indicador-guardado" style="color: #059669; font-size: 11px; margin-top: 4px; font-weight: 500;">💾 Guardado activo</div>
            </div>
        </div>
        <button class="btn btn-primary btn-side" onclick="descargarReporteFinal()">
            <span class="btn-icon-symbol">⬇️</span>
            <span class="sidebar-text">Descargar Reporte</span>
        </button>
        <button class="btn btn-side" onclick="copiarAlPortapapeles()" style="background:#ecfdf5; color:#065f46;">
            <span class="btn-icon-symbol">📋</span>
            <span class="sidebar-text">Copiar al portapapeles</span>
        </button>
        <button class="btn btn-side" onclick="previewMailFinal()" style="background:#eef; color:#333;">
            <span class="btn-icon-symbol">👁</span>
            <span class="sidebar-text">Vista Previa</span>
        </button>
        <div id="btn-restaurar-sintesis-container"></div>
        <button class="btn btn-side" onclick="restablecerOriginal()" style="background:#fef2f2; color:#991b1b; margin-top: 12px;">
            <span class="btn-icon-symbol">🔄</span>
            <span class="sidebar-text">Restablecer Original</span>
        </button>
    </div>
    
    <div class="contenedor-main">
        <div class="contenedor" id="contenedor-secciones"></div>
    </div>
    
    <div id="modal-preview" class="modal-overlay" onclick="this.style.display='none'">
        <div class="modal-frame" onclick="event.stopPropagation()">
            <div style="padding: 10px; background:#eee; text-align:right;"><button class="btn btn-primary" onclick="document.getElementById('modal-preview').style.display='none'">Cerrar</button></div>
            <iframe id="iframe-preview"></iframe>
        </div>
    </div>

    <script src="https://cdn.quilljs.com/1.3.6/quill.js"></script>
    <script>
        const BANNER_PRINCIPAL = __BANNER_PRINCIPAL_JSON__;
        const DATA_INICIAL = __DATA_INICIAL_JSON__;
        const GROQ_API_KEYS = ["__GROQ_API_KEY__", "__GROQ_API_KEY_2__"];
        const REPORT_ID = "__REPORT_ID__";
        const STORAGE_KEY = 'clipping_draft_' + (REPORT_ID || location.pathname.replace(/[^a-zA-Z0-9]/g, '_'));

        let estado = DATA_INICIAL;

        function saveToIndexedDB(key, val) {
            try {
                let req = indexedDB.open("ClippingDB", 1);
                req.onupgradeneeded = function(e) {
                    let db = e.target.result;
                    if (!db.objectStoreNames.contains("drafts")) {
                        db.createObjectStore("drafts");
                    }
                };
                req.onsuccess = function(e) {
                    let db = e.target.result;
                    let tx = db.transaction("drafts", "readwrite");
                    tx.objectStore("drafts").put(val, key);
                };
            } catch(err) { console.error(err); }
        }

        function loadFromIndexedDB(key, callback) {
            try {
                let req = indexedDB.open("ClippingDB", 1);
                req.onupgradeneeded = function(e) {
                    let db = e.target.result;
                    if (!db.objectStoreNames.contains("drafts")) {
                        db.createObjectStore("drafts");
                    }
                };
                req.onsuccess = function(e) {
                    let db = e.target.result;
                    let tx = db.transaction("drafts", "readonly");
                    let store = tx.objectStore("drafts");
                    let getReq = store.get(key);
                    getReq.onsuccess = function() {
                        callback(getReq.result || null);
                    };
                    getReq.onerror = function() {
                        callback(null);
                    };
                };
                req.onerror = function() {
                    callback(null);
                };
            } catch(err) {
                console.error(err);
                callback(null);
            }
        }

        let restoredFromStorage = false;
        try {
            const savedLS = localStorage.getItem(STORAGE_KEY);
            if (savedLS) {
                estado = JSON.parse(savedLS);
                restoredFromStorage = true;
            }
        } catch(e) {
            console.warn("localStorage no disponible", e);
        }

        function guardarBorrador() {
            try {
                localStorage.setItem(STORAGE_KEY, JSON.stringify(estado));
            } catch(e) {}
            saveToIndexedDB(STORAGE_KEY, estado);

            const ind = document.getElementById('indicador-guardado');
            if (ind) {
                const hora = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});
                ind.innerText = '💾 Guardado ' + hora;
            }
        }

        window.addEventListener('beforeunload', function() {
            guardarBorrador();
        });

        function restablecerOriginal() {
            if (confirm('¿Restablecer el reporte al estado original generado? Se descartarán todos los cambios hechos.')) {
                try { localStorage.removeItem(STORAGE_KEY); } catch(e) {}
                estado = JSON.parse(JSON.stringify(DATA_INICIAL));
                render();
                const ind = document.getElementById('indicador-guardado');
                if (ind) ind.innerText = '🔄 Restablecido al original';
            }
        }

        function toggleSintesis(visible) {
            estado.forEach(s => s._ocultar_sintesis = !visible);
            render();
            guardarBorrador();
        }

        let quillInstances = {};
        let dragSrcSec = null, dragSrcNota = null;

        var ColorStyle = Quill.import('attributors/style/color');
        var SizeStyle = Quill.import('attributors/style/size');
        var FontStyle = Quill.import('attributors/style/font');
        Quill.register(ColorStyle, true);
        Quill.register(SizeStyle, true);
        Quill.register(FontStyle, true);

        async function regenerarResumenIA(secIdx, btnElement) {
            const sec = estado[secIdx];
            if (!sec.notas || sec.notas.length === 0) {
                alert('No hay notas en esta sección para resumir.');
                return;
            }

            let textos_notas = sec.notas.map(n => {
                let tempDiv = document.createElement('div');
                tempDiv.innerHTML = n.html_bloque.split(/<br\s*\/?>\s*<br\s*\/?>/i)[0];  // v5.42: igual que Exclusivas: solo la bajada, sin la oración extra de Competencia
                let enlace = tempDiv.querySelector('a');
                if (enlace) enlace.remove();
                let textContent = tempDiv.textContent || tempDiv.innerText || "";
                textContent = textContent.replace(/Ad\. Value: \$ [\d\.]+\s*-?/gi, '')
                                         .replace(/\(Online\)/gi, '')
                                         .replace(/\(Gráfica\)/gi, '')
                                         .replace(/\(IG\)/gi, '')
                                         .replace(/\(FB\)/gi, '')
                                         .replace(/\(X\)/gi, '')
                                         .replace(/\(Alcance:.*?\)/gi, '')
                                         .replace(/\[Mención no detectada.*?\]/gi, '')
                                         .replace(/Sin resumen disponible\./gi, '')
                                         .replace(/\d{2}\/\d{2}\/\d{4}/g, '');
                return textContent.replace(/\s+/g, ' ').trim().substring(0, 300);
            }).filter(t => t.length > 10);

            let texto_completo = textos_notas.join("\n").substring(0, 2500);
            
            let prompt = `Redacta un resumen de los siguientes textos en un único párrafo fluido de máximo 2 oraciones.\n\nReglas strictly obligatorias:\n1. NO menciones ningún sitio web, portal ni medio de comunicación.\n2. NO copies ni menciones títulos de noticias.\n3. Escribe un párrafo de lectura natural (no uses listas, ni viñetas, ni guiones).\n4. Responde ÚNICAMENTE con el texto del resumen final, sin introducciones ni comentarios extra.\n\nTextos a resumir:\n${texto_completo}`;

            btnElement.innerHTML = '⏳ Generando...';
            btnElement.disabled = true;

            try {
                let response = null;
                for (const k of GROQ_API_KEYS) {
                    response = await fetch('https://api.groq.com/openai/v1/chat/completions', {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${k}`,
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            model: "openai/gpt-oss-20b",
                            messages: [{role: "user", content: prompt}],
                            temperature: 0.3,
                            max_tokens: 1024
                        })
                    });
                    if (![429, 498, 503].includes(response.status)) break;
                }

                if (!response.ok) {
                    const errorJson = await response.json().catch(() => ({}));
                    const detail = errorJson.error ? errorJson.error.message : response.statusText;
                    throw new Error(`HTTP ${response.status}: ${detail}`);
                }

                const data = await response.json();
                let resultado = data.choices[0].message.content.trim();

                estado[secIdx].resumen_ia = resultado;
                guardarBorrador();

                let qSin = quillInstances[`quill-sintesis-${secIdx}`];
                if (qSin) {
                    qSin.root.innerHTML = `<p style="font-size: 12px; font-family: Tahoma, sans-serif; color: #333333; line-height: 1.5;">${resultado}</p>`;
                } else {
                    render();
                }
            } catch (error) {
                alert('Error al generar resumen: ' + error.message);
                console.error(error);
            } finally {
                btnElement.innerHTML = '🔄 Regenerar Resumen IA';
                btnElement.disabled = false;
            }
        }

        function actualizarContadorTotal() {
            let total = 0;
            estado.forEach(sec => total += sec.notas ? sec.notas.length : 0);
            document.getElementById('contador-total').innerHTML = 'Total notas: <strong>' + total + '</strong>';
        }

        function render() {
            const cont = document.getElementById('contenedor-secciones'); 
            cont.innerHTML = '';

            const sintesisOculta = estado.length > 0 && estado[0]._ocultar_sintesis === true;
            
            const btnContainer = document.getElementById('btn-restaurar-sintesis-container');
            if (btnContainer) {
                if (sintesisOculta) {
                    btnContainer.innerHTML = `<button class="btn btn-side" onclick="toggleSintesis(true)" style="background:#e0f2fe; color:#0369a1; margin-bottom:8px;"><span class="btn-icon-symbol">➕</span><span class="sidebar-text">Restaurar Síntesis</span></button>`;
                } else {
                    btnContainer.innerHTML = '';
                }
            }
            
            const secsSintesis = estado.filter(s => s.incluir_en_sintesis && s.notas && s.notas.length > 0);
            if (secsSintesis.length > 0 && !sintesisOculta) {
                const sinDiv = document.createElement('div');
                sinDiv.className = 'seccion';
                sinDiv.style.borderLeft = '5px solid var(--tema_color)';
                sinDiv.style.background = '#f8fafc';

                const sHeader = document.createElement('div');
                sHeader.style.cssText = 'padding: 14px 20px; font-weight: bold; font-style: italic; color: var(--tema_color); font-size: 15px; display: flex; justify-content: space-between; align-items: center;';
                sHeader.innerHTML = `<span>SÍNTESIS DEL DÍA · RESUMEN IA</span><button class="btn btn-icon danger" onclick="toggleSintesis(false)" style="font-size: 11px; padding: 3px 10px; font-style: normal;">🗑️ Eliminar Síntesis</button>`;
                sinDiv.appendChild(sHeader);

                const sBody = document.createElement('div');
                sBody.style.padding = '0 20px 20px 20px';

                secsSintesis.forEach((sec) => {
                    const secIndexReal = estado.findIndex(s => s.id === sec.id);

                    const headerSintesisDiv = document.createElement('div');
                    headerSintesisDiv.style.display = 'flex';
                    headerSintesisDiv.style.justifyContent = 'space-between';
                    headerSintesisDiv.style.alignItems = 'center';
                    headerSintesisDiv.style.marginTop = '15px';
                    headerSintesisDiv.style.marginBottom = '8px';

                    const pTitle = document.createElement('p');
                    pTitle.style.fontWeight = 'bold';
                    pTitle.style.color = 'var(--tema_color)';
                    pTitle.style.margin = '0';
                    pTitle.style.fontSize = '14px';
                    pTitle.textContent = sec.nombre;

                    const btnRegenerar = document.createElement('button');
                    btnRegenerar.className = 'btn btn-icon';
                    btnRegenerar.style.borderRadius = '999px';
                    btnRegenerar.style.padding = '4px 12px';
                    btnRegenerar.style.fontSize = '11px';
                    btnRegenerar.style.fontWeight = 'bold';
                    btnRegenerar.style.color = 'var(--tema_color)';
                    btnRegenerar.style.border = '1px solid #cbd5e1';
                    btnRegenerar.style.background = '#ffffff';
                    btnRegenerar.style.cursor = 'pointer';
                    btnRegenerar.innerHTML = '🔄 Regenerar Resumen IA';
                    btnRegenerar.onclick = function() { regenerarResumenIA(secIndexReal, this); };

                    headerSintesisDiv.appendChild(pTitle);
                    headerSintesisDiv.appendChild(btnRegenerar);
                    sBody.appendChild(headerSintesisDiv);

                    const editorSintesisWrapper = document.createElement('div');
                    editorSintesisWrapper.className = 'sintesis-quill-box';

                    const editorSintesisDiv = document.createElement('div');
                    const editorSintesisId = `quill-sintesis-${secIndexReal}`;
                    editorSintesisDiv.id = editorSintesisId;
                    
                    let contenidoInic = sec.resumen_ia ? `<p style="font-size: 12px; font-family: Tahoma, sans-serif; color: #333333; line-height: 1.5;">${sec.resumen_ia}</p>` : `<p style="font-size: 12px; font-family: Tahoma, sans-serif; color: #666666;"><em>Resumen IA vacío. Tocá el botón para generar la redacción.</em></p>`;
                    editorSintesisDiv.innerHTML = contenidoInic;

                    editorSintesisWrapper.appendChild(editorSintesisDiv);
                    sBody.appendChild(editorSintesisWrapper);
                });
                sinDiv.appendChild(sBody);
                cont.appendChild(sinDiv);
            }

            estado.forEach((sec, secIdx) => {
                if (sec.es_separador) {
                    const secDiv = document.createElement('div'); 
                    secDiv.className = 'seccion';
                    secDiv.style.cssText = 'background: transparent; border: none; box-shadow: none; text-align: center; margin: 16px 0; border-radius: 12px; overflow: hidden;';
                    if (sec.img) {
                        secDiv.innerHTML = `<img src="${sec.img}" style="max-width: 100%; height: auto; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08);" title="Banner Separador: ${sec.nombre}">`;
                    }
                    cont.appendChild(secDiv);
                    return;
                }

                const secDiv = document.createElement('div'); 
                secDiv.className = 'seccion';
                secDiv.dataset.secIdx = secIdx;
                
                secDiv.addEventListener('dragover', e => e.preventDefault());
                secDiv.addEventListener('drop', function(e) {
                    e.preventDefault();
                    if (estado[secIdx].notas.length === 0 && dragSrcSec !== null) {
                         const nota = estado[dragSrcSec].notas.splice(dragSrcNota, 1)[0];
                         estado[secIdx].notas.push(nota);
                         render();
                         guardarBorrador();
                    }
                });

                const header = document.createElement('div'); header.className = 'seccion-header';
                header.innerHTML = `<span>${sec.nombre}</span><span class="count">${sec.notas.length} nota(s)</span>`;
                secDiv.appendChild(header);
                
                if(sec.notas.length === 0) {
                     secDiv.innerHTML += `<div style="padding:20px; color: __COLOR_CLIENTE__; font-weight: bold; font-family: Tahoma, sans-serif; font-size: 12px; text-align: left;">No se produjeron menciones</div>`;
                } else {
                    sec.notas.forEach((nota, notaIdx) => {
                        const bloque = document.createElement('div'); 
                        bloque.className = 'bloque-nota';
                        bloque.setAttribute('draggable', 'true');
                        bloque.dataset.secIdx = secIdx;
                        bloque.dataset.notaIdx = notaIdx;

                        bloque.addEventListener('dragstart', function(e) {
                            dragSrcSec = parseInt(this.dataset.secIdx);
                            dragSrcNota = parseInt(this.dataset.notaIdx);
                            this.style.opacity = '0.4';
                        });
                        bloque.addEventListener('dragend', function() {
                            this.style.opacity = '1';
                            dragSrcSec = null; dragSrcNota = null;
                        });
                        bloque.addEventListener('dragover', e => e.preventDefault());
                        bloque.addEventListener('drop', function(e) {
                            e.preventDefault(); e.stopPropagation();
                            const tgtSec = parseInt(this.dataset.secIdx);
                            const tgtNota = parseInt(this.dataset.notaIdx);
                            if (dragSrcSec !== null && dragSrcNota !== null) {
                                if (dragSrcSec === tgtSec && dragSrcNota === tgtNota) return;
                                const movedNota = estado[dragSrcSec].notas.splice(dragSrcNota, 1)[0];
                                estado[tgtSec].notas.splice(tgtNota, 0, movedNota);
                                render();
                                guardarBorrador();
                            }
                        });

                        const editorContainer = document.createElement('div');
                        const editorDivId = `quill-${secIdx}-${notaIdx}`;
                        editorContainer.id = editorDivId;
                        editorContainer.innerHTML = nota.html_bloque;
                        
                        bloque.appendChild(editorContainer);
                        secDiv.appendChild(bloque);
                    });
                }
                cont.appendChild(secDiv);
            });
            initQuills();
            actualizarContadorTotal();
        }

        function initQuills() {
            const misColores = ['__COLOR_CLIENTE__', '#000000', '#e60000', '#ff9900', '#ffff00', '#008a00', '#0066cc', '#9933ff', '#ffffff'];
            quillInstances = {};

            const sintesisOculta = estado.length > 0 && estado[0]._ocultar_sintesis === true;
            const secsSintesis = estado.filter(s => s.incluir_en_sintesis && s.notas && s.notas.length > 0);
            
            if (!sintesisOculta) {
                secsSintesis.forEach((sec) => {
                    const secIndexReal = estado.findIndex(s => s.id === sec.id);
                    const editorSintesisId = `quill-sintesis-${secIndexReal}`;
                    const el = document.getElementById(editorSintesisId);
                    if (el && !quillInstances[editorSintesisId]) {
                        const q = new Quill(`#${editorSintesisId}`, {
                            theme: 'snow',
                            modules: { toolbar: false }
                        });
                        q.on('text-change', function() {
                            estado[secIndexReal].resumen_ia = q.root.innerHTML;
                            guardarBorrador();
                        });
                        quillInstances[editorSintesisId] = q;
                    }
                });
            }

            estado.forEach((sec, secIdx) => {
                if (sec.es_separador) return;
                sec.notas.forEach((nota, notaIdx) => {
                    const editorDivId = `quill-${secIdx}-${notaIdx}`;
                    const el = document.getElementById(editorDivId);
                    if (el) {
                        const q = new Quill(`#${editorDivId}`, {
                            theme: 'snow',
                            modules: { toolbar: [['bold', 'italic', 'underline', 'link'], [{ 'color': misColores }], ['clean']] }
                        });

                        q.root.addEventListener('paste', function(e) {
                            e.preventDefault();
                            const text = (e.clipboardData || window.clipboardData).getData('text/plain');
                            document.execCommand('insertText', false, text);
                        });

                        q.on('text-change', function() {
                            estado[secIdx].notas[notaIdx].html_bloque = q.root.innerHTML;
                            guardarBorrador();
                        });
                        quillInstances[editorDivId] = q;

                        const toolbar = el.previousElementSibling;
                        if (toolbar && toolbar.classList.contains('ql-toolbar')) {
                            const dragHandle = document.createElement('span');
                            dragHandle.className = 'drag-handle';
                            dragHandle.title = 'Arrastrar y soltar';
                            dragHandle.innerText = '☰';
                            dragHandle.style.cssText = 'cursor: grab; font-size: 16px; margin-right: 8px; color: #64748b; user-select: none; align-self: center;';
                            toolbar.insertBefore(dragHandle, toolbar.firstChild);

                            const actionGroup = document.createElement('div');
                            actionGroup.style.cssText = 'margin-left: auto; display: inline-flex; align-items: center; gap: 6px;';
                            
                            let optionsHtml = `<option disabled selected>⇋ Mover a...</option>`;
                            estado.forEach((s, idx) => {
                                if (idx !== secIdx && !s.es_separador) {
                                    optionsHtml += `<option value="${idx}">${s.nombre}</option>`;
                                }
                            });

                            actionGroup.innerHTML = `
                                <button class="btn btn-icon btn-tool" onclick="duplicarNota(${secIdx}, ${notaIdx})" title="Duplicar nota">⧉ Duplicar</button>
                                <button class="btn btn-icon btn-tool danger" onclick="borrarNota(${secIdx}, ${notaIdx})" title="Borrar nota">🗑 Borrar</button>
                                <select class="btn btn-icon btn-tool" style="height: 26px; font-size: 11px;" onchange="moverASeccion(${secIdx}, ${notaIdx}, this.value)">
                                    ${optionsHtml}
                                </select>
                            `;

                            toolbar.appendChild(actionGroup);
                        }
                    }
                });
            });
        }

        function moverNota(s, n, dir) {
            const target = n + dir;
            if (target < 0 || target >= estado[s].notas.length) return;
            const temp = estado[s].notas[n];
            estado[s].notas[n] = estado[s].notas[target];
            estado[s].notas[target] = temp;
            render();
            guardarBorrador();
        }

        function duplicarNota(s, n) {
            const copia = JSON.parse(JSON.stringify(estado[s].notas[n]));
            estado[s].notas.splice(n + 1, 0, copia);
            render();
            guardarBorrador();
        }

        function borrarNota(s, n) {
            if (confirm('¿Borrar esta nota?')) {
                estado[s].notas.splice(n, 1);
                render();
                guardarBorrador();
            }
        }

        function claveOrden(n, tm) {  // v5.53: misma regla que sort_key_final (Python)
            const med = String(n.medio || '').toLowerCase();
            const mf = String(n.fecha || '').match(/(\d{2})\/(\d{2})\/(\d{4})/);
            const ts = mf ? new Date(+mf[3], +mf[2] - 1, +mf[1]).getTime() : 0;
            const graf = n.tipo_medio === 'Gráfica' ? 0 : 1;
            if (tm === 'none') return [graf, 99, 0, 0, 0, med, -ts];
            const num = v => { const x = parseFloat(String(v == null ? '' : v).replace(/[^0-9]/g, '')); return isNaN(x) ? 0 : x; };
            const t = (med + ' ' + (n.link || '') + ' ' + (n.link_destino || '')).toLowerCase();
            let red = null;
            if (/twitter|(^|[^a-z0-9])x\.com/.test(t)) red = 0;
            else if (t.includes('instagram')) red = 1;
            else if (t.includes('facebook')) red = 2;
            else if (/threads|tiktok|linkedin/.test(t)) red = 3;
            const tv = num(n.tier); const tier = [1, 2, 3].includes(tv) ? tv : 99;
            const cat = graf === 0 ? 0 : (red !== null ? 2 : ([1, 2, 3].includes(tier) ? 1 : 3));
            const a_ = cat === 2 ? red : tier, b_ = cat === 2 ? tier : 0;
            return [cat, a_, b_, -num(n.ad_value), -num(n.alcance), med, -ts];
        }
        function insertarOrdenada(secIdx, nota) {
            const tm = estado[secIdx].metricas || 'none';
            const k = claveOrden(nota, tm), arr = estado[secIdx].notas;
            let pos = arr.length;
            for (let i = 0; i < arr.length && pos === arr.length; i++) {
                const c = claveOrden(arr[i], tm);
                for (let j = 0; j < k.length; j++) {
                    if (c[j] === k[j]) continue;
                    if (c[j] > k[j]) pos = i;
                    break;
                }
            }
            arr.splice(pos, 0, nota);
        }

        function moverASeccion(s, n, targetSec) {
            const target = parseInt(targetSec);
            const nota = estado[s].notas.splice(n, 1)[0];
            const tm = estado[target].metricas || 'none';
            if (nota.html_bloque && nota.alcance !== undefined && (estado[s].metricas || 'none') !== tm) {
                // v5.43: al cambiar a una sección con/sin métricas, se recompone ese tramo del encabezado de la nota
                nota.html_bloque = nota.html_bloque.replace(/(<strong style="color: ([^;"]+);[^>]*>\d{2}\/\d{2}\/\d{4}<\/strong>)([\s\S]*?)( <a href=)/, (m, g1, col, old, g4) => {
                    const st = `style='color: ${col}; font-size: 14px; font-family: Tahoma, sans-serif;'`;
                    const adv = `<strong ${st}>Ad. Value: $ ${nota.ad_value}</strong> -`;
                    let info = ' -';
                    if (tm === 'booking') info = ' ' + adv;
                    else if (tm === 'full') info = ` <span ${st}>(Alcance: ${nota.alcance} Tier: ${nota.tier})</span> ` + adv;
                    return g1 + info + g4;
                });
            }
            insertarOrdenada(target, nota);
            render();
            guardarBorrador();
        }

        function generarHtmlFinal(){
            const sintesisOculta = estado.length > 0 && estado[0]._ocultar_sintesis === true;
            let html = '<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">';
            html += '<style>body, table, td, p, div, span, a, strong, b { font-family: Tahoma, sans-serif !important; } p { margin: 0 0 6px 0 !important; line-height: 1.5 !important; color: #000000 !important; } p:first-child { font-size: 14px !important; } p:not(:first-child) { font-size: 12px !important; } a { text-decoration: none !important; }</style>';
            html += '</head><body style="margin: 0; padding: 0; background-color: #f4f4f9; font-family: Tahoma, sans-serif;">';
            html += '<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f4f4f9; padding: 20px 0;"><tr><td align="center"><table width="600" cellpadding="0" cellspacing="0" border="0" style="background-color: #ffffff; border: 1px solid #cccccc;">';
            
            html += `<tr><td align="center" style="padding: 0;"><img src="${BANNER_PRINCIPAL}" alt="Banner Principal" width="600" style="display: block; max-width: 600px; height: auto; border: 0;"></td></tr>`;
            
            const secsExc = estado.filter(s => s.incluir_en_sintesis && s.notas && s.notas.length > 0);
            if(secsExc.length > 0 && !sintesisOculta){ 
                let html_sintesis = '<tr><td style="padding: 20px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin: 8px 0 8px 0;"><tr><td style="background: #f0f4f4; border-left: 4px solid __COLOR_CLIENTE__; padding: 18px 22px; border-radius: 4px;"><p style="margin: 0 0 12px 0 !important; font-family: Tahoma, sans-serif !important; font-size: 12px !important; font-weight: bold !important; color: __COLOR_CLIENTE__ !important; letter-spacing: 0.5px; text-transform: uppercase;">SÍNTESIS DEL DÍA · RESUMEN IA</p>';

                secsExc.forEach(sec => {
                    html_sintesis += '<p style="margin: 10px 0 4px 0 !important; font-family: Tahoma, sans-serif !important; font-size: 12px !important; font-weight: bold !important; color: __COLOR_CLIENTE__ !important;">' + sec.nombre + '</p>';

                    if (sec.resumen_ia && sec.resumen_ia.trim() !== '') {
                        html_sintesis += '<div style="margin: 0 0 10px 0; font-family: Tahoma, sans-serif; font-size: 12px; line-height: 1.5; color: #333333;">' + sec.resumen_ia + '</div>';
                    } else {
                        let items = [];
                        sec.notas.forEach(n => {
                            let div = document.createElement('div'); div.innerHTML = n.html_bloque;
                            let enlace = div.querySelector('a'); let tituloReal = enlace ? enlace.textContent : 'Nota';
                            let medioElem = div.querySelector('strong'); let medioReal = medioElem ? medioElem.textContent : '';
                            let linkUrl = enlace ? enlace.getAttribute('href') : '#';
                            items.push('<li style="margin-bottom: 4px;"><strong>' + medioReal + ':</strong> <a href="' + linkUrl + '" target="_blank" rel="noopener noreferrer" style="color: __COLOR_CLIENTE__; text-decoration: none; font-size: 12px;">' + tituloReal + '</a></li>');
                        });
                        html_sintesis += '<ul style="margin: 0 0 10px 0; padding-left: 18px; font-family: Tahoma, sans-serif; font-size: 12px; line-height: 1.5; color: #333333;">' + items.join('\n') + '</ul>';
                    }
                });

                html_sintesis += '</td></tr></table></td></tr>';
                html += html_sintesis;
            }

            estado.forEach((sec, index) => {
                if(index !== 0 || (secsExc.length > 0 && !sintesisOculta)) {
                    html += '<tr><td style="font-size: 0px; line-height: 0px; height: 20px;">&nbsp;</td></tr>';
                }
                
                if(sec.img) {
                    html += `<tr><td align="center" style="padding: 0;"><img src="${sec.img}" alt="Banner Seccion" width="600" style="display: block; max-width: 600px; height: auto; border: 0;"></td></tr>`;
                }

                if(sec.notas.length === 0) {
                    if (!sec.es_separador) {
                        html += `<tr><td style="padding: 20px;"><p style="font-family: Tahoma, sans-serif; font-size: 12px; color: __COLOR_CLIENTE__; font-weight: bold; margin: 0;"><strong style="color: __COLOR_CLIENTE__;">No se produjeron menciones</strong></p></td></tr>`;
                    }
                } else {
                    sec.notas.forEach(n => { 
                        html += `<tr><td style="padding: 20px; font-family: Tahoma, sans-serif; border-bottom: 1px solid #eeeeee;">${n.html_bloque}</td></tr>`;
                    });
                }
            });
            
            html += '</table></td></tr></table></body></html>';
            return html;
        }

        function descargarReporteFinal(){
            const a = document.createElement('a');
            a.href = URL.createObjectURL(new Blob([generarHtmlFinal()], { type: 'text/html' }));
            
            const fecha = new Date();
            const dia = String(fecha.getDate()).padStart(2, '0');
            const mes = String(fecha.getMonth() + 1).padStart(2, '0');
            const anio = String(fecha.getFullYear()).slice(-2);
            
            a.download = `Clipping __CLIENTE_NOMBRE__ ${dia}-${mes}-${anio}.html`;
            a.click();
        }
        
        // v5.83: auto-scroll de la página mientras se arrastra una nota cerca del borde superior/inferior
        (function(){
            let timer = null, yAct = 0;
            document.addEventListener('dragstart', function(e){
                if (timer) return;
                timer = setInterval(function(){
                    const zona = 140, h = window.innerHeight; let v = 0;
                    if (yAct < zona) v = -Math.ceil((zona - yAct) / 5);
                    else if (yAct > h - zona) v = Math.ceil((yAct - (h - zona)) / 5);
                    if (v) window.scrollBy(0, Math.max(-40, Math.min(40, v)));
                }, 16);
            });
            document.addEventListener('dragover', function(e){ yAct = e.clientY; });
            function parar(){ if (timer) { clearInterval(timer); timer = null; } }
            document.addEventListener('dragend', parar);
            document.addEventListener('drop', parar);
        })();

        async function copiarAlPortapapeles(){  // v5.64: copia solo la tabla del reporte (sin el bloque contenedor gris)
            let html = generarHtmlFinal();
            try {
                const dp = new DOMParser().parseFromString(html, 'text/html');
                const inner = dp.querySelector('body > table > tbody > tr > td > table');
                if (inner) html = '<html><head><meta charset="utf-8">' + dp.head.innerHTML + '</head><body>' + inner.outerHTML + '</body></html>';
            } catch(e) {}
            try {
                await navigator.clipboard.write([new ClipboardItem({
                    'text/html': new Blob([html], {type:'text/html'}),
                    'text/plain': new Blob([html.replace(/<[^>]+>/g,' ')], {type:'text/plain'})
                })]);
                alert('✅ Reporte copiado. Pegalo en el mail.');
            } catch(e) {
                const d = document.createElement('div');
                d.contentEditable = 'true'; d.style.cssText = 'position:fixed;left:-9999px;top:0;';
                d.innerHTML = html; document.body.appendChild(d);
                const r = document.createRange(); r.selectNodeContents(d);
                const sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(r);
                const ok = document.execCommand('copy');
                sel.removeAllRanges(); document.body.removeChild(d);
                alert(ok ? '✅ Reporte copiado. Pegalo en el mail.' : '❌ No se pudo copiar.');
            }
        }

        function previewMailFinal(){
            document.getElementById('iframe-preview').srcdoc = generarHtmlFinal();
            document.getElementById('modal-preview').style.display = 'flex';
        }

        render();

        if (restoredFromStorage) {
            const ind = document.getElementById('indicador-guardado');
            if (ind) ind.innerText = '✨ Borrador restaurado';
        } else {
            loadFromIndexedDB(STORAGE_KEY, function(dbData) {
                if (dbData && Array.isArray(dbData)) {
                    estado = dbData;
                    render();
                    const ind = document.getElementById('indicador-guardado');
                    if (ind) ind.innerText = '✨ Borrador restaurado';
                }
            });
        }
    </script>
</body>
</html>'''
    plantilla = plantilla.replace("__COLOR_CLIENTE__", color)
    plantilla = plantilla.replace("__BANNER_PRINCIPAL_JSON__", json.dumps(banner_limpio)).replace("__DATA_INICIAL_JSON__", json.dumps(sec_data))
    _ks = keys_para_cliente(cliente_nombre)  # v5.57
    plantilla = plantilla.replace("__GROQ_API_KEY__", _ks[0]).replace("__GROQ_API_KEY_2__", _ks[1] if len(_ks) > 1 else _ks[0])
    plantilla = plantilla.replace("__REPORT_ID__", report_id)
    plantilla = plantilla.replace("__CLIENTE_NOMBRE__", cliente_nombre)
    return plantilla

# ====================================================================
# INTERFAZ NICEGUI
# ====================================================================

@ui.page('/')
async def index():
    ui.add_head_html('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');
        body {
            background-color: #f2f4f7 !important;
            background-image: 
                radial-gradient(circle at 15% 15%, rgba(15, 23, 42, 0.06) 0%, transparent 45%),
                radial-gradient(circle at 85% 85%, rgba(15, 23, 42, 0.05) 0%, transparent 45%),
                radial-gradient(rgba(15, 23, 42, 0.05) 1px, transparent 1px) !important;
            background-size: 100% 100%, 100% 100%, 24px 24px !important;
            background-attachment: fixed !important;
        }
    </style>
    <script>
        document.addEventListener('click', function(e) {
            var target = e.target.closest('a');
            if (target && target.href && target.href.startsWith('http')) {
                target.setAttribute('target', '_blank');
                target.setAttribute('rel', 'noopener noreferrer');
            }
        }, true);
    </script>
    ''')

    await ui.context.client.connected()

    # PANTALLA DE LOGIN
    if not app.storage.tab.get('authenticated', False):
        with ui.card().classes('absolute-center items-center p-8 shadow-xl rounded-2xl w-96'):
            ui.label('Hecho por Santiago Allende').classes('text-[10px] text-gray-400 mb-2')
            ui.label('🔒 Acceso Restringido').classes('text-2xl font-bold text-[#0F172A] mb-2')
            ui.label('Ingresá tus credenciales').classes('text-gray-500 mb-6')
            
            user_input = ui.input('👤 Usuario').classes('w-full mb-2')
            pass_input = ui.input('🔑 Contraseña').props('type=password').classes('w-full mb-6')
            
            def attempt_login():
                usr = user_input.value
                pwd = pass_input.value
                _us = _cargar_usuarios().get(usr)
                if _us and _verificar_pw(pwd, _us.get('hash', '')):
                    app.storage.tab['authenticated'] = True
                    app.storage.tab['username'] = usr
                    app.storage.tab['rol'] = _us.get('rol', 'usuario')
                    registrar_actividad(usr, "Inicio de sesión", "Acceso exitoso al sistema")
                    ui.navigate.reload()
                else:
                    ui.notify('❌ Usuario o contraseña incorrectos', color='negative')

            ui.button('Ingresar al Sistema', on_click=attempt_login).classes('w-full bg-[#0F172A] text-white font-bold rounded-lg')
        return

    @ui.refreshable
    def header_title():
        with ui.row().classes('items-center gap-2'):
            ui.label('🏢').classes('text-xl')
            ui.label('Ketchum Argentina').classes('text-xl font-extrabold text-white').style('font-family: "Inter", "Segoe UI", sans-serif; letter-spacing: 1.2px; text-transform: uppercase;')

    with ui.header().classes('justify-between items-center bg-[#0F172A] shadow-md px-6 py-3'):
        with ui.row().classes('items-center gap-2'):
            ui.button(icon='menu', on_click=lambda: drawer_clientes.toggle()).props('flat round dense color=white')  # v5.61: reabrir/plegar menú lateral
            header_title()
            
        def logout():
            registrar_actividad(app.storage.tab.get('username', 'usuario'), "Cierre de sesión", "Salió del sistema")
            app.storage.tab['authenticated'] = False
            ui.navigate.reload()
            
        async def chequear_actualizacion():  # v5.55
            v_rem, url_exe = await run.io_bound(consultar_version_remota)
            if not v_rem or _vtuple(v_rem) <= _vtuple(APP_VERSION): return
            with ui.dialog() as dlg, ui.card():
                ui.label(f'🆕 Hay una versión nueva: v{v_rem} (tenés v{APP_VERSION})').classes('font-bold')
                msg = ui.label('Se descarga y se reinicia el programa. No cierres nada hasta que se reabra.' if url_exe else 'Pedí el .exe nuevo al administrador.').classes('text-sm')
                async def hacer():
                    msg.set_text('⏳ Descargando...')
                    ok, m = await run.io_bound(descargar_y_preparar_update, url_exe)
                    msg.set_text(m)
                    if ok:
                        await asyncio.sleep(1); app.shutdown(); os._exit(0)
                with ui.row():
                    if url_exe: ui.button('Actualizar ahora', on_click=hacer)
                    ui.button('Más tarde', on_click=dlg.close).props('flat')
            dlg.open()
        ui.timer(2.0, chequear_actualizacion, once=True)
        with ui.row().classes('items-center gap-4'):
            ui.label('Hecho por Santiago Allende').classes('text-slate-400 text-[10px] italic')
            ui.label(f'v{APP_VERSION}').classes('text-slate-300 italic text-sm font-bold bg-slate-800 px-2 rounded')
            ui.button('🚪 Cerrar Sesión', on_click=logout).props('flat text-color=white').classes('font-bold border border-slate-600 rounded px-3 ml-2')

    # ====================================================================
    # MENÚ LATERAL Y MÓDULO DE WEB SCRAPING
    # ====================================================================
    with ui.left_drawer(value=True).classes('bg-[#f8f9fa] border-r border-gray-200 p-6') as drawer_clientes:
        
        if app.storage.tab.get('rol') == 'admin':
            with ui.card().classes('w-full p-4 mb-6 border border-amber-300 bg-amber-50 shadow-sm rounded-xl'):
                ui.label('🛠 MODO DIOS (Admin)').classes('text-xs font-bold text-amber-800 tracking-wider mb-2')
                
                ui.button('📝 Reporte SOLO MANUALES', on_click=lambda: procesar_reporte(solo_manuales=True)).props('dense outline text-color=amber-9').classes('w-full mb-2 font-bold')
                ui.button('⚡ Prueba Rápida (Solo Banners)', on_click=lambda: procesar_reporte(solo_banners=True)).props('dense color=amber-8').classes('w-full font-bold text-white')
                

            ui.separator().classes('mb-6')

        ui.label('🏢 Selección de Cliente').classes('text-lg font-bold text-gray-800 mb-2')
        def change_client(e):
            state.cliente = e.value
            state.init_secciones()
            header_title.refresh()
            main_content.refresh()
            sidebar_content.refresh()
            
        ui.select(list(CLIENTES_CONFIG.keys()), value=state.cliente, on_change=change_client).classes('w-full bg-white mb-6')
        ui.separator().classes('mb-6')
        
        ui.label('⏱️ Rango de Búsqueda').classes('text-lg font-bold text-gray-800 mb-2')
        ui.radio({"1d": "Últimas 24 hs", "3d": "Últimos 3 días", "5d": "Toda la semana"}, value=state.timeframe).bind_value(state, 'timeframe').classes('mb-6')
        ui.separator().classes('mb-6')
        
        @ui.refreshable
        def sidebar_content():
            ui.label('🔍 Búsquedas Extra').classes('text-lg font-bold text-gray-800 mb-2')
            config = CLIENTES_CONFIG[state.cliente]
            opciones_sec = [s['nombre'] for s in config['secciones'] if not s.get('es_separador')]
            
            for i, extra in enumerate(state.extra_searches):
                with ui.card().classes('w-full p-3 mb-2 shadow-sm bg-white border border-gray-100'):
                    ui.label(f"Búsqueda {i+1}").classes('text-xs text-gray-400 font-bold mb-1')
                    ui.input('Palabra o frase').bind_value(extra, 'q').classes('w-full mb-1')
                    ui.select(opciones_sec, label='Sección', value=opciones_sec[0] if opciones_sec else None).bind_value(extra, 'sec').classes('w-full')
            
            ui.button('➕ Sumar búsqueda', on_click=lambda: (state.add_extra_search(), sidebar_content.refresh())).props('outline').classes('w-full mt-2')
            
        sidebar_content()

    def mostrar_pantalla_revision(data_editor, data_auditoria):
        with ui.dialog().classes('w-full') as dialog, ui.card().classes('w-full max-w-5xl p-6 bg-slate-50 rounded-2xl shadow-2xl'):
            ui.label('🔍 Revisión y Control de Notas (Previo a Generar)').classes('text-xl font-bold text-slate-800 mb-1')
            ui.label('Podés incluir notas que hayan sido excluidas por la IA o el filtro, o quitar notas sumadas antes de descargar los archivos.').classes('text-xs text-slate-500 mb-4')

            dialog.open()
            scroll_container = ui.scroll_area().classes('w-full h-[550px] pr-2').props('id=review-scroll-area')

            with scroll_container:
                est_plegado = {}  # v5.41: estado plegado/desplegado (persiste entre refrescos)
                @ui.refreshable
                def render_lista_revision():
                    for sec_idx, sec in enumerate(data_auditoria):
                        sec_id = sec['id']
                        sec_editor = next((s for s in data_editor if s['id'] == sec_id), None)
                        
                        with ui.expansion(f"📁 {sec['nombre']} ({len(sec.get('evaluaciones', []))})", value=est_plegado.get(f'sec|{sec_id}', True), on_value_change=lambda e, k=f'sec|{sec_id}': est_plegado.__setitem__(k, e.value)).classes('w-full mb-4 p-2 border border-slate-200 bg-white rounded-xl shadow-sm').props('header-class="font-bold text-base text-slate-800"'):
                            
                            evals = sec.get('evaluaciones', [])
                            if not evals:
                                ui.label("Sin notas procesadas en esta sección.").classes('text-xs text-slate-400 italic')
                                continue

                            evals_ordenadas = sorted(
                                evals,
                                key=lambda e: (
                                    0 if e['estado'] == 'SUMADA' else 1,
                                    str(e.get('estado', '')) if e['estado'] != 'SUMADA' else '',
                                    remover_acentos(str(e.get('medio', '')).lower()),
                                    remover_acentos(str(e.get('titulo', '')).lower())
                                )
                            )

                            with ui.column().classes('w-full gap-2'):
                                grupos = {}
                                for g in dict.fromkeys(e['estado'] for e in evals_ordenadas):
                                    cnt = sum(1 for e in evals_ordenadas if e['estado'] == g)
                                    tit_g = f'✅ Aprobadas ({cnt})' if g == 'SUMADA' else f"🚫 Excluidas · {g.replace('EXCLUIDA_', '').replace('_', ' ')} ({cnt})"
                                    k_g = f'{sec_id}|{g}'
                                    with ui.expansion(tit_g, value=est_plegado.get(k_g, g == 'SUMADA'), on_value_change=lambda e, k=k_g: est_plegado.__setitem__(k, e.value)).classes('w-full border border-slate-200 rounded-lg bg-slate-50').props('dense header-class="font-bold text-sm"'):
                                        grupos[g] = ui.column().classes('w-full gap-2 p-2')
                                for ev_idx, ev in enumerate(evals_ordenadas):
                                    with grupos[ev['estado']]:
                                        es_sumada = ev['estado'] == 'SUMADA'
                                        bg_color = 'bg-emerald-50 border-emerald-200' if es_sumada else 'bg-rose-50 border-rose-200'
                                    
                                        with ui.row().classes(f'w-full items-center justify-between p-3 rounded-lg border {bg_color} text-xs'):
                                            with ui.column().classes('w-[72%] gap-1'):
                                                with ui.row().classes('items-center gap-2 flex-wrap'):
                                                    ui.label(ev['medio']).classes('font-bold text-slate-800 text-sm')
                                                
                                                    es_manual = ev.get('origen_fuente') in ['Manual', 'Gráfica', 'grafica', 'manual'] or 'manual' in str(ev.get('motivo','')).lower()

                                                    if es_sumada:
                                                        if es_manual:
                                                            ui.chip('MANUAL', color='emerald-2', text_color='emerald-9').classes('text-[10px] font-bold py-0 h-5')
                                                    elif ev.get('es_ia'):
                                                        ui.chip('IA', color='purple-2', text_color='purple-9').classes('text-[10px] font-bold py-0 h-5')
                                                        ui.label(f"Motivo: {ev['motivo']}").classes('text-xs text-purple-900 font-bold italic bg-purple-100/80 px-2 py-0.5 rounded')
                                                    else:
                                                        est_clean = str(ev['estado']).replace('EXCLUIDA_', '').replace('_', ' ')
                                                        ui.chip(est_clean, color='rose-2', text_color='rose-9').classes('text-[10px] font-bold py-0 h-5')
                                                        ui.label(f"Motivo: {ev['motivo']}").classes('text-xs text-rose-900 font-bold italic bg-rose-100/80 px-2 py-0.5 rounded')
                                                    ui.label(fecha_y_dominio_nota(ev)).classes('text-[11px] text-slate-500 font-medium')  # v5.88
                                            
                                                ui.html(f'<a href="{ev["link"]}" target="_blank" rel="noopener noreferrer" class="text-sky-600 font-semibold underline text-xs">{ev["titulo"]}</a>')
                                            
                                                if not es_sumada and ev.get('origen_fuente'):
                                                    ui.label(f"Fuente: {ev.get('origen_fuente')}").classes('text-slate-500 italic text-[11px] font-normal mt-0.5')

                                            async def toggle_nota(ev_ref=ev, s_edit=sec_editor, sec_ref=sec):
                                                scroll_pos = 0
                                                try:
                                                    scroll_pos = await ui.run_javascript('''
                                                        (function() {
                                                            let el = document.querySelector('#review-scroll-area .q-scrollarea__container');
                                                            return el ? el.scrollTop : 0;
                                                        })()
                                                    ''')
                                                except Exception:
                                                    scroll_pos = 0

                                                if ev_ref['estado'] == 'SUMADA':
                                                    ev_ref['estado'] = 'EXCLUIDA_MANUAL'
                                                    ev_ref['motivo'] = 'Quitada manualmente por el usuario en revisión'
                                                else:
                                                    ev_ref['estado'] = 'SUMADA'
                                                    ev_ref['motivo'] = 'Sumada manualmente en revisión'

                                                sumadas = [e for e in sec_ref['evaluaciones'] if e['estado'] == 'SUMADA']
                                                excluidas = [e for e in sec_ref['evaluaciones'] if e['estado'] != 'SUMADA']

                                                sumadas.sort(key=lambda e: sort_key_final(e.get('bloque_data') or {'medio': e.get('medio', '')}, s_edit['id']))  # v5.53
                                                excluidas.sort(key=lambda e: (str(e.get('estado', '')), remover_acentos(str(e.get('medio', '')).lower()), remover_acentos(str(e.get('titulo', '')).lower())))

                                                sec_ref['evaluaciones'] = sumadas + excluidas

                                                if s_edit:
                                                    s_edit['notas'] = []
                                                    cfg = CLIENTES_CONFIG[state.cliente]
                                                    sec_cfg_rev = next((sc for sc in cfg['secciones'] if sc['id'] == s_edit['id']), None)
                                                    kws_sec_rev = sec_cfg_rev.get('keywords', []) if sec_cfg_rev else []
                                                    for e_sum in sumadas:
                                                        b = e_sum.get('bloque_data')
                                                        if b:
                                                            if 'html_bloque' in b and b['html_bloque']:
                                                                insertar_nota_ordenada(s_edit['notas'], {"html_bloque": b['html_bloque'], "alcance": b.get('alcance', '?'), "tier": b.get('tier', '?'), "ad_value": b.get('ad_value', '?'), "medio": b.get('medio', ''), "tipo_medio": b.get('tipo_medio', ''), "fecha": b.get('fecha', ''), "link": b.get('link', ''), "link_destino": b.get('link_destino', '')}, s_edit['id'])
                                                            else:
                                                                if b.get('leida') is False:  # v5.52
                                                                    if state.status_chip: ui.notify('Leyendo la nota para completar el texto...')
                                                                    await run.io_bound(completar_bloque_pre, b, kws_sec_rev, s_edit['id'])
                                                                bloque_texto = construir_bloque_texto(b.get('bajada_real', ''), b.get('oracion_clave', ''), b.get('titulo', ''), kws_sec_rev, s_edit['id'], b.get('resumen_rss', ''))
                                                            
                                                                etiqueta_tipo = b.get('tipo_medio', 'Online')
                                                                if etiqueta_tipo == "Online":
                                                                    medio_eval = str(b.get('medio', '')).lower()
                                                                    link_eval = str(b.get('link', '')).lower()
                                                                    if "instagram" in medio_eval or "instagram.com" in link_eval:
                                                                        etiqueta_tipo = "IG"
                                                                    elif "facebook" in medio_eval or "facebook.com" in link_eval:
                                                                        etiqueta_tipo = "FB"
                                                                    elif "twitter" in medio_eval or "x.com" in link_eval or "twitter.com" in link_eval:
                                                                        etiqueta_tipo = "X"

                                                                tipo_html = f" <strong style='color: {cfg['color_primario']}; font-size: 14px;'>({etiqueta_tipo})</strong> " if b.get('tipo_medio') != "Gráfica" else " "
                                                                info_metricas = " -"
                                                                if s_edit['id'] == 'booking_tema_1':
                                                                    info_metricas = f" <strong style='color: {cfg['color_primario']}; font-size: 14px;'>Ad. Value: $ {b.get('ad_value', '?')}</strong> -"
                                                                elif s_edit['id'] in IDS_SINTESIS and s_edit['id'] not in IDS_SIN_METRICAS:
                                                                    info_metricas = f" <span style='color: {cfg['color_primario']}; font-size: 14px;'>(Alcance: {b.get('alcance', '?')} Tier: {b.get('tier', '?')})</span> <strong style='color: {cfg['color_primario']}; font-size: 14px;'>Ad. Value: $ {b.get('ad_value', '?')}</strong> -"
                                                            
                                                                html_indiv = f'''<p style="margin-top: 0; margin-bottom: 4px; color: #000000;"><strong style="color: {cfg['color_primario']}; font-size: 14px;">{b.get('medio', '')}</strong>{tipo_html}<strong style="color: {cfg['color_primario']}; font-size: 14px;">{b.get('fecha', '')}</strong>{info_metricas} <a href="{b.get('link', '#')}" target="_blank" rel="noopener noreferrer" style="color: {cfg['color_primario']}; text-decoration: none; font-size: 14px; font-weight: normal;">{b.get('titulo', '')}</a></p>{bloque_texto}'''
                                                                insertar_nota_ordenada(s_edit['notas'], {"html_bloque": html_indiv, "alcance": b.get('alcance', '?'), "tier": b.get('tier', '?'), "ad_value": b.get('ad_value', '?'), "medio": b.get('medio', ''), "tipo_medio": b.get('tipo_medio', ''), "fecha": b.get('fecha', ''), "link": b.get('link', ''), "link_destino": b.get('link_destino', '')}, s_edit['id'])

                                                render_lista_revision.refresh()

                                                if scroll_pos:
                                                    try:
                                                        await ui.run_javascript(f'''
                                                            (function() {{
                                                                let el = document.querySelector('#review-scroll-area .q-scrollarea__container');
                                                                if (el) el.scrollTop = {scroll_pos};
                                                            }})()
                                                        ''')
                                                    except Exception: pass

                                            if es_sumada:
                                                ui.button('❌ Quitar', on_click=toggle_nota).classes('bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold px-3 py-1.5 rounded-lg shadow-sm')
                                            else:
                                                ui.button('➕ Incluir en Reporte', on_click=toggle_nota).classes('bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold px-3 py-1.5 rounded-lg shadow-sm')

            render_lista_revision()

            def descargar_confirmado():
                dialog.close()
                fecha_hoy = datetime.datetime.now().strftime("%d-%m-%y")
                config = CLIENTES_CONFIG[state.cliente]
                
                guardar_en_historial_excel(state.cliente, data_auditoria)

                html_resultado = generar_html_editor(config["banner_principal_url"], data_editor, config["color_primario"], state.cliente)
                nombre_archivo_editor = f'Clipping {state.cliente} {fecha_hoy}.html'
                ui.download(html_resultado.encode('utf-8'), nombre_archivo_editor)
                
                html_auditoria = generar_html_auditoria(state.cliente, state.timeframe, data_auditoria, config["color_primario"])
                nombre_archivo_auditoria = f'Auditoria Clipping {state.cliente} {fecha_hoy}.html'
                ui.download(html_auditoria.encode('utf-8'), nombre_archivo_auditoria)
                
                ui.notify('🎉 Reportes finales generados, descargados e historial Excel actualizado', color='positive', position='top')

            with ui.row().classes('w-full justify-end gap-3 mt-4 border-t border-slate-200 pt-4'):
                ui.button('Cancelar', on_click=dialog.close).props('flat text-color=grey-7').classes('font-bold')
                ui.button('📥 Confirmar y Generar Reportes Finales', on_click=descargar_confirmado).classes('bg-emerald-700 hover:bg-emerald-800 text-white font-bold py-2 px-4 rounded-xl shadow-md')

    async def procesar_reporte(solo_manuales=False, solo_banners=False):
        if not state.log_box or not state.timer_label or not state.log_container or not state.status_chip:
            ui.notify('❌ Error de UI: La consola no está lista', color='negative')
            return

        state.timer_label.classes(remove='hidden')
        state.status_chip.classes(remove='hidden')
        if state.progress_label: state.progress_label.classes(remove='hidden'); state.progress_label.set_text('')
        if state.rss_label: state.rss_label.classes(remove='hidden'); state.rss_label.set_text('')
        state.status_chip.set_text("📍 Iniciando motor de búsqueda...")
        state.stop_req = False  # v5.50
        state.log_box.classes(remove='hidden')
        state.log_container.clear()
        state.log_container.push("🚀 Iniciando motor de procesamiento...")
        
        # --- NUEVO: Setup de los botones de la UI al arrancar ---
        if getattr(state, 'btn_procesar', None): state.btn_procesar.disable()
        if getattr(state, 'btn_pausa', None):
            state.is_paused = False
            state.btn_pausa.set_text('⏸️ PAUSAR')
            state.btn_pausa.classes(replace='py-4 text-lg font-bold shadow-lg rounded-xl bg-amber-500 text-white w-1/3 transition-all')
            state.btn_pausa.classes(remove='hidden')
        if getattr(state, 'btn_stop', None): state.btn_stop.classes(remove='hidden')  # v5.50
            
        registrar_actividad(app.storage.tab.get('username', 'usuario'), "Generó Reporte", f"Cliente: {state.cliente} | Manuales: {solo_manuales} | Banners: {solo_banners}")
        
        start_time = datetime.datetime.now()
        tiempo_pausado_total = 0
        
        def update_chrono():
            nonlocal tiempo_pausado_total
            if getattr(state, 'is_paused', False):
                tiempo_pausado_total += 1
                return
            
            elapsed = int((datetime.datetime.now() - start_time).total_seconds()) - tiempo_pausado_total
            mins, secs = divmod(elapsed, 60)
            if state.timer_label:
                state.timer_label.set_text(f'⏱️ Tiempo de trabajo: {mins:02d}:{secs:02d}')
            
        ui_chrono = ui.timer(1.0, update_chrono)
        
        config = CLIENTES_CONFIG[state.cliente]
        datos_links = {}
        datos_grafica = {}
        for s in config['secciones']:
            sid = s['id']
            raw_links = state.links_manuales.get(sid, "")
            datos_links[sid] = [url.strip() for url in re.split(r'[,\n\s]+', raw_links) if url.strip() and url.strip().startswith('http')]
            datos_grafica[sid] = [g for g in state.graficas.get(sid, []) if g['medio'].strip() and g['titulo'].strip()]

        busquedas_extra_validas = [e for e in state.extra_searches if e.get('q', '').strip()]

        log_queue = queue.Queue()
        def safe_logger(msg): log_queue.put(msg)
        
        cont_sec = {"nombre": "", "sumadas": 0}  # v5.45: notas sumadas en la sección en curso
        def flush_logs():
            while not log_queue.empty():
                msg = log_queue.get()
                if str(msg).startswith('§RSS|'):  # v5.73
                    if state.rss_label: state.rss_label.set_text(f"📡 RSS actual: {str(msg)[5:][:70]}")
                    continue
                if str(msg).startswith('§PROG|'):  # v5.68: indicador fuera del log
                    try:
                        _, _t, _ok, _lim = str(msg).split('|', 3)
                        if state.progress_label: state.progress_label.set_text(f"✅ {_t[:40]}: aprobadas {_ok}/{_lim}")
                    except Exception: pass
                    continue
                if state.log_container:
                    state.log_container.push(msg)
                if "🔎 ANALIZANDO SECCIÓN:" in msg:
                    cont_sec["nombre"] = msg.replace("🔎 ANALIZANDO SECCIÓN:", "").strip()
                    cont_sec["sumadas"] = 0
                elif "✓ SUMADA" in str(msg) and cont_sec["nombre"]:
                    cont_sec["sumadas"] += 1
                else:
                    continue
                if state.status_chip:
                    state.status_chip.set_text(f"📍 Sección actual: {cont_sec['nombre']}")

        ui_timer = ui.timer(0.3, flush_logs)

        try:
            data_editor, data_auditoria = await run.io_bound(
                orquestador_principal,
                datos_links,
                datos_grafica,
                config,
                state.cliente,
                safe_logger,
                state.timeframe,
                busquedas_extra_validas,
                solo_manuales,
                solo_banners
            )
            
            flush_logs()
            ui_timer.deactivate()
            ui_chrono.deactivate()

            if state.status_chip:
                state.status_chip.set_text("✅ Proceso completado exitosamente")

            if state.log_container:
                state.log_container.push("✅ PROCESO TERMINADO. Abriendo pantalla de revisión...")
                
            state.last_data_editor = data_editor
            state.last_data_auditoria = data_auditoria

            mostrar_pantalla_revision(data_editor, data_auditoria)
            
            # --- NUEVO: Resetear los botones al terminar con éxito ---
            if getattr(state, 'btn_procesar', None): state.btn_procesar.enable()
            if getattr(state, 'btn_pausa', None): state.btn_pausa.classes(add='hidden')
            if getattr(state, 'btn_stop', None): state.btn_stop.classes(add='hidden')  # v5.50
            
        except Exception as e:
            flush_logs()
            ui_timer.deactivate()
            ui_chrono.deactivate()
            if state.status_chip:
                state.status_chip.set_text("❌ Error durante la generación")
            if state.log_container:
                state.log_container.push(f"❌ Error durante el proceso: {str(e)}")
            ui.notify('❌ Error al generar. Mirá el log de pantalla.', color='negative')
            
            # --- NUEVO: Resetear los botones si falla por error ---
            if getattr(state, 'btn_procesar', None): state.btn_procesar.enable()
            if getattr(state, 'btn_pausa', None): state.btn_pausa.classes(add='hidden')
            if getattr(state, 'btn_stop', None): state.btn_stop.classes(add='hidden')  # v5.50

    @ui.refreshable
    def main_content():
        config = CLIENTES_CONFIG[state.cliente]
        color = config['color_primario']
        
        with ui.column().classes('w-full max-w-5xl mx-auto p-8'):

            with ui.card().classes('w-full mb-6 p-4 border border-gray-200 shadow-sm rounded-xl bg-white'):
                with ui.row().classes('items-center justify-between w-full'):
                    with ui.row().classes('items-center gap-3'):
                        ui.avatar('business', color=f'[{color}]', text_color='white', size='md')
                        with ui.column().classes('gap-0'):
                            ui.label('CLIENTE ACTIVO').classes('text-xs font-bold text-gray-400 tracking-wider')
                            ui.label(state.cliente).classes('text-2xl font-black').style(f'color: {color};')
                    
                    gacetilla_txt = obtener_gacetilla_cliente_cached(state.cliente)
                    with ui.column().classes('items-end gap-1 max-w-md'):
                        ui.label('📰 GACETILLA ACTIVA').classes('text-[10px] font-bold text-gray-400 tracking-wider')
                        if gacetilla_txt:
                            q_gacetilla = urllib.parse.quote(gacetilla_txt)
                            link_gacetilla_rss = f"https://news.google.com/rss/search?q=%22{q_gacetilla}%22%20when%3A{state.timeframe}%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419"
                            ui.label(f'"{gacetilla_txt}"').classes('text-xs font-semibold text-gray-700 italic text-right line-clamp-2')
                            ui.html(f'<a href="{link_gacetilla_rss}" target="_blank" rel="noopener noreferrer" class="text-xs text-sky-600 font-bold hover:underline flex items-center gap-1">🔗 Ver búsqueda en Google News ↗</a>')
                        else:
                            ui.label('Sin gacetilla activa').classes('text-xs font-semibold text-gray-400 italic')

            # v5.84: cargar links desde el Word compartido
            with ui.card().classes('w-full mb-6 p-4 border shadow-sm').style('border-radius: 12px;'):
                ui.label('📄 Links del Word compartido').classes('font-bold text-gray-700')
                with ui.row().classes('w-full items-center gap-3'):
                    inp_word = ui.input('Ruta del Word (.docx) o link de Google Docs', value=app.storage.general.get('ruta_word', '')).classes('flex-grow')
                    inp_word.on('blur', lambda e: app.storage.general.__setitem__('ruta_word', (inp_word.value or '').strip().strip('"')))
                    def cargar_word():
                        ruta = (inp_word.value or '').strip().strip('"')
                        app.storage.general['ruta_word'] = ruta
                        res, sin_sec, err = leer_links_word(ruta, state.cliente, config['secciones'])
                        if err:
                            ui.notify(err, type='negative', close_button=True); return
                        total = 0; partes = []
                        for sec_w in config['secciones']:
                            if sec_w.get('es_separador'): continue
                            nuevos = res.get(sec_w['id'], [])
                            if not nuevos: continue
                            previos = [u for u in re.split(r'[,\n\s]+', state.links_manuales.get(sec_w['id'], '')) if u.startswith('http')]
                            agregar = [u for u in nuevos if u not in previos]
                            state.links_manuales[sec_w['id']] = '\n'.join(previos + agregar)
                            total += len(agregar); partes.append(f"{sec_w['nombre']}: {len(nuevos)}")
                        msg = f"✅ {total} link(s) cargados desde el Word. " + (' | '.join(partes) if partes else 'No hay links para este cliente.')
                        ui.notify(msg, type='positive', close_button=True, multi_line=True, timeout=0)
                        if sin_sec:
                            ui.notify(f"⚠️ {len(sin_sec)} link(s) del Word están bajo el cliente pero sin una sección reconocida (no se cargaron).", type='warning', close_button=True, multi_line=True, timeout=0)
                    ui.button('Cargar links del Word', on_click=cargar_word).props('color=primary')

            for sec in config['secciones']:
                if sec.get('es_separador', False): continue
                
                with ui.card().classes('w-full mb-8 p-6 border shadow-sm').style('border-radius: 12px;'):
                    ui.html(f"<h3 style='color: {color}; margin:0; font-weight:800; font-size: 20px;'>📁 {sec['nombre_largo']}</h3>")
                    
                    ui.label("🔗 Notas Web Manuales").classes('font-bold text-gray-700 mt-4')
                    ui.textarea('Pegá los links (separados por coma o con un enter)').bind_value(state.links_manuales, sec['id']).classes('w-full bg-gray-50')
                    
                    ui.label("🗞️ Agregar Nota Gráfica").classes('font-bold text-gray-700 mt-6 mb-2')
                    for i, graf in enumerate(state.graficas[sec['id']]):
                        with ui.card().classes('w-full bg-gray-50 p-4 border border-gray-200 mb-3 shadow-none'):
                            if len(state.graficas[sec['id']]) > 1:
                                ui.label(f"Nota Gráfica {i+1}").classes('text-xs font-bold text-gray-400 mb-2')
                            with ui.row().classes('w-full gap-4'):
                                with ui.column().classes('w-[48%]'):
                                    ui.input('Nombre del Medio').bind_value(graf, 'medio').classes('w-full bg-white')
                                    ui.input('Título de la Nota').bind_value(graf, 'titulo').classes('w-full bg-white')
                                    ui.input('Fecha de la Nota').props('type=date').bind_value(graf, 'fecha').classes('w-full bg-white')
                                with ui.column().classes('w-[48%]'):
                                    ui.input('Link de Drive').bind_value(graf, 'link').classes('w-full bg-white')
                                    ui.textarea('Texto o Bajada').bind_value(graf, 'bajada').classes('w-full bg-white h-24')
                            if tipo_metricas(sec['id']) != 'none':  # v5.43: métricas manuales (opcionales)
                                with ui.row().classes('w-full gap-4'):
                                    if tipo_metricas(sec['id']) == 'full':
                                        ui.input('Alcance (opcional)').bind_value(graf, 'alcance').classes('w-[30%] bg-white')
                                        ui.input('Tier (opcional)').bind_value(graf, 'tier').classes('w-[30%] bg-white')
                                    ui.input('Ad Value (opcional)').bind_value(graf, 'ad_value').classes('w-[30%] bg-white')

                    ui.button("➕ Sumar otra nota gráfica", on_click=lambda sid=sec['id']: (state.add_grafica(sid), main_content.refresh())).props(f'outline text-color={color.strip("#")}').classes('mt-2')
            
            ui.separator().classes('my-6')
            
            state.timer_label = ui.label('⏱️ Tiempo transcurrido: 00:00').classes('font-bold text-gray-700 mb-2 hidden')
            
            with ui.row().classes('items-center gap-3 mb-3'):
                state.status_chip = ui.chip('📍 Esperando inicio...', icon='radar').props('color=dark text-color=white').classes('bg-[#0F172A] text-white font-bold shadow-md hidden')
                state.progress_label = ui.label('').classes('font-bold text-gray-700 hidden')  # v5.68: búsqueda actual + aprobadas x/límite
                state.rss_label = ui.label('').classes('font-bold text-gray-700 hidden')  # v5.73: RSS en curso (a la derecha)
            
            state.log_box = ui.column().classes('w-full hidden')
            state.log_container = MonitorConsola(state.log_box)

            # --- NUEVO: Botones de control y lógica de Pausa ---
            def entregar_parcial():  # v5.50: corta la búsqueda y entrega lo recolectado hasta ahora
                state.stop_req = True
                state.is_paused = False
                if state.status_chip: state.status_chip.set_text("🛑 Cerrando y entregando lo recolectado...")
                if state.log_container: state.log_container.push("🛑 <b>[ENTREGA PARCIAL]</b> - Se termina la nota en curso y se arma el reporte con lo que hay.")

            def toggle_pausa():
                state.is_paused = not getattr(state, 'is_paused', False)
                if state.is_paused:
                    state.btn_pausa.set_text('▶️ REANUDAR')
                    state.btn_pausa.classes(replace='py-4 text-lg font-bold shadow-lg rounded-xl bg-emerald-500 text-white w-1/3 transition-all')
                    if state.status_chip: state.status_chip.set_text("⏸️ Proceso en pausa...")
                    if state.log_container: state.log_container.push("⏸️ <b>[PROCESO PAUSADO]</b> - <i>Revisá el log y tocá 'Reanudar' cuando estés listo.</i>")
                else:
                    state.btn_pausa.set_text('⏸️ PAUSAR')
                    state.btn_pausa.classes(replace='py-4 text-lg font-bold shadow-lg rounded-xl bg-amber-500 text-white w-1/3 transition-all')
                    if state.status_chip: state.status_chip.set_text("▶️ Reanudando búsqueda...")
                    if state.log_container: state.log_container.push("▶️ <b>[PROCESO REANUDADO]</b>")

            with ui.row().classes('w-full gap-2 mt-4'):
                state.btn_procesar = ui.button('🚀 PROCESAR REPORTE', on_click=lambda: procesar_reporte()).classes('flex-grow py-4 text-lg font-bold shadow-lg rounded-xl transition-all').style(f'background-color: {color}; color: white;')
                state.btn_pausa = ui.button('⏸️ PAUSAR', on_click=toggle_pausa).classes('py-4 text-lg font-bold shadow-lg rounded-xl bg-amber-500 text-white w-1/3 hidden transition-all')
                state.btn_stop = ui.button('🛑 ENTREGAR YA', on_click=entregar_parcial).classes('py-4 text-lg font-bold shadow-lg rounded-xl bg-red-600 text-white w-1/4 hidden transition-all')

    main_content()

import multiprocessing

if __name__ in {"__main__", "__mp_main__"}:
    multiprocessing.freeze_support()
    ui.run(title="Generador Clipping", port=int(os.environ.get("PUERTO", 8080)), language="es", storage_secret=_storage_secret(), reload=False)
