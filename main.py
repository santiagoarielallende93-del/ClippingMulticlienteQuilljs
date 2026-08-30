import sys
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
import base64
import json
import os
import io
import csv
import queue
import requests

# ====================================================================
# CONFIGURACIÓN Y VERSIÓN
# ====================================================================
APP_VERSION = "2.6"
URL_VERSION_GITHUB = "https://raw.githubusercontent.com/santiagoarielallende93-del/ClippingMulticlienteQuilljs/main/version.txt"
URL_MAIN_PYTHON_GITHUB = "https://raw.githubusercontent.com/santiagoarielallende93-del/ClippingMulticlienteQuilljs/main/main.py"
GROQ_API_KEY = "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" 
LINK_EXCEL_DRIVE = "https://docs.google.com/spreadsheets/d/1ZntitgSKrfkaL5rpG45ajwbr0yPVvfAp/edit?usp=sharing&ouid=110785507732300006515&rtpof=true&sd=true"

CREDENCIALES = {
    "admin": "admin123",
    "usuario": "clipping2026"
}

# ====================================================================
# AUDITORÍA DE REGISTRO
# ====================================================================
def registrar_actividad(usuario, accion, detalles):
    archivo_log = "registro_uso.csv"
    archivo_existe = os.path.isfile(archivo_log)
    fecha_hora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    with open(archivo_log, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not archivo_existe: 
            writer.writerow(["Fecha y Hora", "Usuario", "Acción", "Detalles"])
        writer.writerow([fecha_hora, usuario, accion, detalles])

# ====================================================================
# DICCIONARIO MAESTRO DE CLIENTES
# ====================================================================
CLIENTES_CONFIG = {
    "MSD Salud Animal": {
        "color_primario": "#006E74",
        "hoja_excel": "MSD",
        "banner_principal_local": "banners/principal.jpg",
        "banner_principal_url": "https://drive.google.com/file/d/1uT1al-u7cCEG-Q6oiay52GIdwnj2OKM5/view",
        "secciones": [
            {
                "id": "exclusivas", "nombre": "Exclusivas", "nombre_largo": "Exclusivas (MSD Salud Animal)",
                "img_local": "banners/exclusivas.jpg", "img_url": "https://drive.google.com/file/d/1cUyr83JrnQIo0XqMFltpoQkbuskaN41C/view", 
                "rss": ["https://news.google.com/rss/search?q=%22MSD%20Salud%20Animal%22%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419",
                "https://news.google.com/rss/search?q=%22Walter%20Comas%22%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419",
                "https://news.google.com/rss/search?q=%22Clara%20Fern%C3%A1ndez%20Boglione%22%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419"], 
                "keywords": ["MSD Salud Animal", "MSD", "Walter Comas", "Clara Fernández Boglione", "Pablo Nervi", "Emiliano Segurado"], "exclusiones": [], "limite": 20
            },
            {
                "id": "ceo", "nombre": "CEO", "nombre_largo": "CEO",
                "img_local": "banners/ceo.jpg", "img_url": "https://drive.google.com/file/d/1IH8MranbZnd_R--Nz5JZFbxbg3kDTfBB/view", 
                "rss": ["https://news.google.com/rss/search?q=CEO%20empresa%20-futbol%20-deportes%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419"], 
                "keywords": ["ceo", "CEO", "entrevista", "Entrevista", "ENTREVISTA", "Chief Ejecutive Officer", "Director Ejecutivo", "en dialogo"], "exclusiones": ["fútbol", "futbol", "partido", "dt ", "boca", "river", "racing", "independiente", "san lorenzo", "champions", "tenis", "nba", "rugby", "goles", "gol ", "estadio", "scaloni", "actor", "actriz", "película", "pelicula", "cine", "teatro", "recital", "cantante", "música", "musica", "farándula", "gran hermano", "reality", "asesinato", "crimen"], "limite": 10
            },
            {
                "id": "salud", "nombre": "Salud Animal", "nombre_largo": "Salud Animal",
                "img_local": "banners/salud.jpg", "img_url": "https://drive.google.com/file/d/1Uc5WOsfk6kPBTncXsb6b7qOQlX3guYhz/view", 
                "rss": ["https://news.google.com/rss/search?q=zoonosis%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419",
                "https://news.google.com/rss/search?q=hantavirus%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419",
                "https://news.google.com/rss/search?q=triquinosis%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419",
                "https://news.google.com/rss/search?q=%22bienestar%20animal%22%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419",
                "https://news.google.com/rss/search?q=%22salud%20animal%22%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419"], 
                "keywords": ["zoonosis", "hantavirus", "triquinosis", "veterinaria", "salud animal", "humano", "humanos", "Biogénesis Bagó"], "exclusiones": ["pediatría", "hospital municipal", "paro médico", "prepaga", "ioma", "pami", "estética humana"], "limite": 10
            },
            {
                "id": "mascotas", "nombre": "Animales de Compañía", "nombre_largo": "Animales de Compañía / Mascotas",
                "img_local": "banners/mascotas.jpg", "img_url": "https://drive.google.com/file/d/1-zviGD1bM6e5493pKhUntxGXVQTquj5z/view", 
                "rss": ["https://news.google.com/rss/search?q=mascotas%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=perros%20veterinaria%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=gatos%20veterinaria%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=%22animales%20de%20compa%C3%B1%C3%ADa%22%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419"], 
                "keywords": ["Mascotas", "Perros", "Perro", "Gato", "Gatos", "Animales de compañía", "canino", "felino"], "exclusiones": ["ballena", "delfín", "tiburón", "fauna silvestre", "zoológico", "zoo ", "matt damon", "actor", "actriz", "película", "pelicula", "cine", "hollywood", "famosos", "farándula", "gran hermano", "reality", "hugo sigman", "insud", "diputado", "senador"], "limite": 15
            },
            {
                "id": "aves", "nombre": "Aves", "nombre_largo": "Aves",
                "img_local": "banners/aves.jpg", "img_url": "https://drive.google.com/file/d/1xxWwhur4zqeiH5OyH11LtVa-nqH-Bvfp/view", 
                "rss": ["https://news.google.com/rss/search?q=avicultura%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=%22granjas%20av%C3%ADcolas%22%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=produccion%20avicola%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=gallinas%20huevos%20produccion%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419"], 
                "keywords": ["Aves", "Avicultura", "Avícola", "avícolas", "huevo", "huevos", "gallina", "gallinas", "granjas avícolas"], "exclusiones": ["dinosaurio", "fósil", "cóndor", "fauna silvestre", "avión", "aerolíneas", "vuelo"], "limite": 10
            },
            {
                "id": "cerdos", "nombre": "Cerdos", "nombre_largo": "Cerdos",
                "img_local": "banners/cerdos.jpg", "img_url": "https://drive.google.com/file/d/1vvV1SK4Vf0Y6Zijn_9pOIfQbZV11Gw-v/view", 
                "rss": ["https://news.google.com/rss/search?q=cerdos%20produccion%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=porcino%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=porcina%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419"], 
                "keywords": ["Cerdos", "Porcino", "Porcina"], "exclusiones": ["actor", "actriz", "farándula", "película", "cine"], "limite": 10
            },
            {
                "id": "ganaderia", "nombre": "Ganadería", "nombre_largo": "Ganadería",
                "img_local": "banners/ganaderia.jpg", "img_url": "https://drive.google.com/file/d/1JglW_UjMe-Lzqc7nxA1Ws776gVqXPI08/view", 
                "rss": ["https://news.google.com/rss/search?q=ganaderia%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=Tecnovax%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=bovino%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=feedlot%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=vacas%20ganado%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419"], 
                "keywords": ["Ganadería", "Ganadero", "Bovino", "Ganado", "vacas", "vaca", "feedlot", "feedlots", "tecnovax", "lechería", "leche", "brucelosis", "tuberculosis", "aftosa",], "exclusiones": ["actor", "actriz", "farándula", "película", "cine", "fútbol", "Vaca Muerta"], "limite": 20
            },
            {
                "id": "innovacion", "nombre": "Innovación en Salud Animal", "nombre_largo": "Innovación en Salud Animal",
                "img_local": "banners/innovacion.jpg", "img_url": "https://drive.google.com/file/d/1A6JsKrwszGa5UQaxtE-fOda1gleA9jP9/view", 
                "rss": ["https://news.google.com/rss/search?q=%22innovacion%20animal%22%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=%22tecnologia%20veterinaria%22%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=%22biotecnologia%20animal%22%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419"], 
                "keywords": ["Innovación", "tecnología veterinaria", "biotecnología animal"], "exclusiones": ["actor", "farándula", "cine"], "limite": 5
            }
        ]
    },
    "Mars": {
        "color_primario": "#0000FF", "hoja_excel": "Mars", "banner_principal_local": "banners/mars_principal.jpg", "banner_principal_url": "https://drive.google.com/file/d/1pi3-8vZ-xr9p0AVR8tZmLaknj2kuhY7W/view",
        "secciones": [
            { "id": "mars_exclusivas", "nombre": "Exclusivas", "nombre_largo": "Banner Separador Exclusivas", "img_local": "banners/mars_exclusivas.jpg", "img_url": "https://drive.google.com/file/d/1tOcO3nn8Dsa55rldjciutv5cFr0h_VNP/view", "es_separador": True, "rss": [], "keywords": [], "exclusiones": [], "limite": 0 },
            { "id": "mars_tema_1", "nombre": "Corporativo", "nombre_largo": "Corporativo", "img_local": "banners/mars_corporativo.jpg", "img_url": "https://drive.google.com/file/d/1Vb7xaz32_V2lphPsAdJELhzPqeSERLJY/view", "rss": ["https://news.google.com/rss/search?q=Mars%20South%20Latam%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=Romina%20Ferreyra%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=Mattia%20Iannone%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=Whiskas%20when%3A7d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], 
            "keywords": ["Mars", "South", "Latam", "Mars South Latam", "Romina Ferreyra", "Mattia Iannone", "Whiskas", "Pedigree"], "exclusiones": ["marte", "veronica mars", "bruno mars", "Jared Leto", "30 seconds to mars"], "limite": 20 },
            { "id": "mars_tema_2", "nombre": "Pet Nutrition", "nombre_largo": "Pet Nutrition", "img_local": "banners/mars_petnutrition.jpg", "img_url": "https://drive.google.com/file/d/1gayVCjqbhHsrPvm6XqO4jWFifqixT0gh/view", "rss": ["https://news.google.com/rss/search?q=Mars%20Pet%20Nutrition%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["Pedigree", "Whiskas", "Mars Pet Nutrition", "Guadalupe Perez Torelli", "Mars Petcare"], "exclusiones": ["marte", "veronica mars", "bruno mars", "Jared Leto", "30 seconds to mars"], "limite": 20 },
            { "id": "mars_tema_3", "nombre": "Snacking", "nombre_largo": "Snacking", "img_local": "banners/mars_snacking.jpg", "img_url": "https://drive.google.com/file/d/1ji-Jx3hf4XKQbxl013c84Hhaezri3Wj-/view", "rss": ["https://news.google.com/rss/search?q=Mars%20Snacking%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["Mars", "Snacking", "Mars Snacking"], "exclusiones": ["marte", "veronica mars", "bruno mars", "Jared Leto", "30 seconds to mars"], "limite": 20 },
            { "id": "mars_competencia", "nombre": "Competencia", "nombre_largo": "Competencia", "img_local": "banners/mars_competencia.jpg", "img_url": "https://drive.google.com/file/d/1xTP21p0Xd8fbr9sSqZ8I1ON8FBy2Qovz/view", "rss": ["https://news.google.com/rss/search?q=Nestl%C3%A9%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=Alican%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=Royal%20Canin%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=Eukanuba%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=Purina%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=Vitalcan%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=Metrive%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=Sieger%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=Agroindustrias%20Baires%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["Nestlé", "Alican", "Bacan", "Purina", "Mon Ami", "Metrive", "Eukanuba", "Royal Canin", "Vitalcan", "Sieger", "Agroindustrias Baires"], "exclusiones": [], "limite": 20 },
            { "id": "mars_interes", "nombre": "Noticias de Interés", "nombre_largo": "Noticias de interés", "img_local": "banners/mars_interes.jpg", "img_url": "https://drive.google.com/file/d/1U6reL2Cj2o6XhbHB8nmssoLqYNyIJulK/view", "rss": ["https://news.google.com/rss/search?q=consumo%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["consumo", "consumo masivo", "industria alimenticia", "supermercados", "inflación", "pobreza", "alimentos", "mascotas", "perro", "perros", "gato", "gatos", ], "exclusiones": ["PBI", "drogas", "cocaína", "marihuana", "alcohol", "carne", "vacuna", "vacuno", "porcino", "aviar"], "limite": 20 }
        ]
    },
    "BMS": {
        "color_primario": "#1A4FB5", "hoja_excel": "BMS", "banner_principal_local": "banners/bms_principal.jpg", "banner_principal_url": "https://drive.google.com/file/d/1ruuvwWkVLVgu-ZJJ6wwEPF8S6snh5mUX/view",
        "secciones": [
            { "id": "bms_tema_1", "nombre": "Exclusivas", "nombre_largo": "Exclusivas", "img_local": "banners/bms_exclusivas.jpg", "img_url": "https://drive.google.com/file/d/1ZYHx7jQfemxr2S4g5crIpaGdDgJtXQds/view", "rss": ["https://news.google.com/rss/search?q=Bristol%20Myers%20Squibb%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=ARG%20Bristol%20Myers%20Squibb%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419",
            "https://news.google.com/rss/search?q=Bristol%20Myers%20Squibb%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], 
            "keywords": ["Bristol Myers Squibb", "Bristol-Myers Squibb", "BMS"], "exclusiones": [], "limite": 20 },
            { "id": "bms_tema_2", "nombre": "Noticias del Sector", "nombre_largo": "Noticias del Sector", "img_local": "banners/bms_noticiasdelsector.jpg", "img_url": "https://drive.google.com/file/d/1FhuuaWsEr2ywBp_QzKGuvwZOm1W6gekK/view", "rss": ["https://news.google.com/rss/search?q=Salud%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=medicamentos%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=%22Ministro%20de%20Salud%22%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=%22obras%20sociales%22%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=%22investigaci%C3%B3n%20cl%C3%ADnica%22%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["Salud", "medicamentos", "Ministro de Salud", "obras sociales", "investigación clínica"], "exclusiones": [], "limite": 20 },
            { "id": "bms_tema_3", "nombre": "Propiedad Intelectual / Biosimilares", "nombre_largo": "Propiedad Intelectual / Biosmilares", "img_local": "banners/bms_propiedadintelectualbiosimilares.jpg", "img_url": "https://drive.google.com/file/d/12A4oDRQ7BlmY_zop1a0ThahV1JOFQ8vk/view", "rss": [], "keywords": [], "exclusiones": [], "limite": 10 },
            { "id": "bms_tema_4", "nombre": "Competencia", "nombre_largo": "Competencia", "img_local": "banners/bms_competencia.jpg", "img_url": "https://drive.google.com/file/d/1rZfcOHZGfwsk40-L8Ti0fIlp6z6spM9G/view", "rss": ["https://news.google.com/rss/search?q=Pfizer%20OR%20Astrazeneca%20OR%20Richmond%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=Abbot%20OR%20Abbvie%20OR%20AMgen%20OR%20Boehringer%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=Elanco%20OR%20%22Johnson%20%26%20Johnson%22%20OR%20%22Kimberly%20Clarck%22%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=mAbxience%20OR%20Lilly%20OR%20MERCK%20OR%20Novartis%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=%22Novo%20Nordick%22%20OR%20Roche%20OR%20Sanofi%20OR%20Takeda%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=Zoetis%20OR%20%22Thermo%20Fisher%22%20OR%20Eczane%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["Pfizer", "Richmond", "Astrazeneca", "Abbot", "Abbvie", "Amgen", "Boehringer", "Elanco", "Johnson & Johnson", "Kimberly Clarck", "mAbxience", "Lilly", "Merck", "Novartis", "Novo Nordick", "Roche", "Sanofi", "Takeda", "Zoetis", "Thermo Fisher", "Eczane"], "exclusiones": [], "limite": 20 },
            { "id": "bms_tema_5", "nombre": "Areas Terapeuticas", "nombre_largo": "Áreas Terapéuticas", "img_local": "banners/bms_areasterapeuticas.jpg", "img_url": "https://drive.google.com/file/d/1HXv0m__Xixd0NgE607eAWrVXFT73Xdy2/view", "es_separador": True, "rss": [], "keywords": [], "exclusiones": [], "limite": 0 },
            { "id": "bms_tema_6", "nombre": "Onco-Hematologia", "nombre_largo": "Onco-Hematologia", "img_local": "banners/bms_oncohematologia.jpg", "img_url": "https://drive.google.com/file/d/1o8SGZMYZSZSsxqcYCZKPEhwWAh9T8sVx/view", "rss": ["https://news.google.com/rss/search?q=c%C3%A1ncer%20OR%20metastasis%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=tumores%20OR%20melanoma%20OR%20linfoma%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["cáncer", "cancer", "metástasis", "metastasis", "tumores", "tumor", "melanoma", "linfoma"], "exclusiones": [], "limite": 10 },
            { "id": "bms_tema_7", "nombre": "CAR-T", "nombre_largo": "CAR-T", "img_local": "banners/bms_cart.jpg", "img_url": "https://drive.google.com/file/d/1B6Rt1GJRhH2opmm9vnmTaLrRu8vVS0dW/view", "rss": ["https://news.google.com/rss/search?q=CAR-T%20OR%20%22terapia%20g%C3%A9nica%22%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=inmunoterapia%20linfocitos%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["CAR-T", "CAR T", "inmunoterapia", "terapia génica", "linfocitos T", "células cancerosas"], "exclusiones": [], "limite": 10 },
            { "id": "bms_tema_8", "nombre": "Cardiología", "nombre_largo": "Cardiología", "img_local": "banners/bms_cardiologia.jpg", "img_url": "https://drive.google.com/file/d/1JtpFFXjYVcr-4nCyE_XaxLtfmobCp2_M/view", "rss": ["https://news.google.com/rss/search?q=ACV%20OR%20cardiolog%C3%ADa%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=cardiovascular%20OR%20%22presi%C3%B3n%20arterial%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["ACV", "cardiología", "cardiologia", "cardiovascular", "presión arterial", "presion arterial", "cardíaco", "cardiaco", "infarto"], "exclusiones": [], "limite": 10 },
            { "id": "bms_tema_9", "nombre": "Artritis", "nombre_largo": "Artritis", "img_local": "banners/bms_artritis.jpg", "img_url": "https://drive.google.com/file/d/1qaHdfmIDmmgnDRj9VhJsU5qYuKw6B_ug/view", "rss": ["https://news.google.com/rss/search?q=artritis%20OR%20articulaciones%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=%22enfermedades%20reumaticas%22%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["artritis", "articulaciones", "enfermedades reumáticas", "enfermedad reumática", "reuma"], "exclusiones": [], "limite": 10 },
            { "id": "bms_tema_10", "nombre": "Psoriasis", "nombre_largo": "Psoriasis", "img_local": "banners/bms_psoriasis.jpg", "img_url": "https://drive.google.com/file/d/1VEZeFSymEKe5vHrNKLD08419502G_nqH/view", "rss": ["https://news.google.com/rss/search?q=psoriasis%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["psoriasis"], "exclusiones": [], "limite": 10 },
            { "id": "bms_tema_11", "nombre": "Trasplante", "nombre_largo": "Trasplante", "img_local": "banners/bms_trasplante.jpg", "img_url": "https://drive.google.com/file/d/1pHzriblnIvQl44uQrooGJXI4qGIE_YLU/view", "rss": ["https://news.google.com/rss/search?q=trasplante%20OR%20trasplantes%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["trasplante", "trasplantes", "donación de órganos", "donacion de organos"], "exclusiones": [], "limite": 10 }
        ]
    },
    "Arredo": {
        "color_primario": "#0000FF", "hoja_excel": "Arredo", "banner_principal_local": "banners/arredo_principal.jpg", "banner_principal_url": "https://drive.google.com/file/d/1MESH-P0uDrBHX83uNEstihGcH2eEC6UU/view",
        "secciones": [
            { "id": "arredo_tema_1", "nombre": "Exclusivas", "nombre_largo": "Exclusivas", "img_local": "banners/arredo_exclusivas.jpg", "img_url": "https://drive.google.com/file/d/18HsLa3b-kNOtgaR5YYxMlaUo6UvHpxJH/view", "rss": ["https://news.google.com/rss/search?q=Arredo%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["Arredo"], "exclusiones": [], "limite": 20 },
            { "id": "arredo_tema_2", "nombre": "Mención", "nombre_largo": "Menciones", "img_local": "banners/arredo_menciones.jpg", "img_url": "https://drive.google.com/file/d/19U90rGK_pWlKGssHxlYX9Zu-cQGoA4Ce/view", "rss": [], "keywords": ["Arredo"], "exclusiones": [], "limite": 20 },
            { "id": "arredo_tema_3", "nombre": "Recursos Humanos", "nombre_largo": "Recursos Humanos", "img_local": "banners/arredo_recursoshumanos.jpg", "img_url": "https://drive.google.com/file/d/1zXnXWvMT-CKfFEgB2dbjqNZWtOvOCisQ/view", "rss": [], "keywords": ["inclusión laboral", "informalidad", "becas", "pasantías", "mejores empresas", "mejor empresa", "trabajar", "empleo", "derechos laborales", "mercado laboral", "liderazgo"], "exclusiones": [], "limite": 20 },
            { "id": "arredo_tema_4", "nombre": "Diversidad y Género", "nombre_largo": "Diversidad y Género", "img_local": "banners/arredo_diversidadygenero.jpg", "img_url": "https://drive.google.com/file/d/17P15vUG1zciLz_-j3sFKUax-nIpqAcsO/view", "rss": [], "keywords": ["mujeres", "inclusión", "mujeres", "mujeres emprendedoras", "mujeres profesionales", "violencia de género", "brecha salarial", "primer empleo", "empleo joven"], "exclusiones": [], "limite": 20 },
            { "id": "arredo_tema_5", "nombre": "Sustentabilidad", "nombre_largo": "Sustentabilidad", "img_local": "banners/arredo_sustentabilidad.jpg", "img_url": "https://drive.google.com/file/d/1WSuNM_EBYjj45-K2T-qtFtONuseJ7TCU/view", "rss": [], "keywords": ["Empresa B", "sustentabilidad", "energía renovable", "reciclar", "reciclado", "economía circular"], "exclusiones": [], "limite": 10 },
            { "id": "arredo_tema_6", "nombre": "Competencia", "nombre_largo": "Competencia", "img_local": "banners/arredo_competencia.jpg", "img_url": "https://drive.google.com/file/d/1VxLJRHbvfqtOgLBWeVqGquFxnNX0-swx/view", "rss": [], "keywords": ["Home Collection", "Duvet Home", "Kavanagh", "Landmark", "Indian", "Casablanca", "Jean Cartier", "Ad Home", "Egger", "H&G Home", "AltoRancho", "Franco Valente"], "exclusiones": [], "limite": 10 },
            { "id": "arredo_tema_7", "nombre": "Noticias de Interes", "nombre_largo": "Noticias de Interes", "img_local": "banners/arredo_noticiasdeinteres.jpg", "img_url": "https://drive.google.com/file/d/1rVjjNmlVdhJU2Ed7wJVV4wwhkqeF70rH/view", "rss": ["https://news.google.com/rss/search?q=industria%20textil%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=inflaci%C3%B3n%20when%3A1d%20ARG&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["textil", "industria", "industria textil", "fabrica", "fabricas", "inflación", "pymes", "consumo", "pobreza", "dormir", "decoración", "ropa de cama", "hábitos de sueño", "ecommerce"], "exclusiones": [], "limite": 20 }
        ]
    },
    "Amanco Wavin": {
        "color_primario": "#000099", "hoja_excel": "Amanco", "banner_principal_local": "banners/amanco_principal.jpg", "banner_principal_url": "https://drive.google.com/file/d/1gFQAqAPm3xiGlDKM72Plr5fT19IF-5Z4/view",
        "secciones": [
            { "id": "amanco_tema_1", "nombre": "Exclusivas", "nombre_largo": "Exclusivas", "img_local": "banners/amanco_exclusivas.jpg", "img_url": "https://drive.google.com/file/d/1_vg5keIN7jMt7FCOFjGxgVNbXGxGnjOW/view", "rss": ["https://news.google.com/rss/search?q=Amanco%20Wavin%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["Amanco Wavin"], "exclusiones": [], "limite": 20 },
            { "id": "amanco_tema_2", "nombre": "Competencia", "nombre_largo": "Competencia", "img_local": "banners/amanco_competencia.jpg", "img_url": "https://drive.google.com/file/d/1nQos7Azcml2O5DRZCD4Hfrs-xe5Mao8W/view", "rss": [], "keywords": ["FV", "Ferrum", "Rotoplas", "DEMA", "Duke", "Aqualaf", "AWADUCT", "Roca"], "exclusiones": [], "limite": 10 },
            { "id": "amanco_tema_3", "nombre": "Industria e Infraestructura", "nombre_largo": "Industria e Infraestructura", "img_local": "banners/amanco_industriaeinfraestructura.jpg", "img_url": "https://drive.google.com/file/d/1-6eOexICM6t-Iiro5dIUfP1WDSLxz7U6/view", "rss": ["https://news.google.com/rss/search?q=infraestructura%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=construcci%C3%B3n%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=prefabricada%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=ducha%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=Aysa%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=ARG%20alba%C3%B1il%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["vivienda", "obra pública", "Infraestructura", "rutas", "construcción", "construir", "albañil", "inflación", "obras", "agua", "riego", "plomero", "plomería", "baño", "baños", "hídricos", "materiales", "Loma Negra", "prefabricada", "casa", "casas", "Aysa", "AySa"], "exclusiones": ["rural", "sanitaria"], "limite": 10 },
            { "id": "amanco_tema_4", "nombre": "Sustentabilidad", "nombre_largo": "Sustentabilidad", "img_local": "banners/amanco_sustentabilidad.jpg", "img_url": "https://drive.google.com/file/d/1ILvTnUcm-FF7lbWStCXUqYsRe8pyhxHB/view", "rss": ["https://news.google.com/search?q=Sustentabilidad%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["sustentable", "sustentabilidad", "Empresa B"], "exclusiones": [], "limite": 10 }
        ]
    },
    "Booking": {
        "color_primario": "#0000FF", "hoja_excel": "Booking", "banner_principal_local": "banners/booking_principal.jpg", "banner_principal_url": "https://drive.google.com/file/d/1TKf_eTU4sWBk_9pYG5iBI4r6CKA52Fz4/view",
        "secciones": [
            { "id": "booking_tema_1", "nombre": "Exclusivas", "nombre_largo": "Exclusivas", "img_local": "banners/booking_exclusivas.jpg", "img_url": "https://drive.google.com/file/d/1IkOGzUtBEw_TWkf5AgdWK4-5yXmCk5gf/view", "rss": ["https://news.google.com/rss/search?q=Booking%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["Booking", "Booking.com", "Booking Argentina", "Booking Holding"], "exclusiones": ["Bavaro", "ArchDaily"], "limite": 20 },
            { "id": "booking_tema_2", "nombre": "Competencia", "nombre_largo": "Competencia", "img_local": "banners/booking_competencia.jpg", "img_url": "https://drive.google.com/file/d/1SD6Qf6FxN8lvIuwqiywS8hCThh5IGH4B/view", "rss": ["https://news.google.com/rss/search?q=Airbnb%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=%22Almundo%22%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=Turismocity%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=Tripadvisor%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=Expedia%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["Airbnb", "Turismocity", "Almundo", "Tripadvisor", "Expedia"], "exclusiones": [], "limite": 20 },
            { "id": "booking_tema_3", "nombre": "Turismo", "nombre_largo": "Turismo", "img_local": "banners/booking_turismo.jpg", "img_url": "https://drive.google.com/file/d/1PVMiBHJuTBdm7YQn6OF1c9F31gvyckZR/view", "rss": ["https://news.google.com/rss/search?q=ARG%20%22Turismo%22%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=ARG%20%22Vacaciones%22%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419", "https://news.google.com/rss/search?q=ARG%20%22viajes%22%20when%3A1d&hl=es-419&gl=AR&ceid=AR%3Aes-419"], "keywords": ["turismo", "viajes", "viajar", "vacaciones", "pasajes", "vuelos", "hoteles", "hospedaje"], "exclusiones": ["jugadores", "jugador", "Lionel Scaloni", "futbol", "futbolista", "Messi", "selección", "famosos", "actor", "actriz", "romance", "novio", "novia", "farándula", "gran hermano", "teatro", "separación", "escándalo", "modelo", "cantante"], "limite": 30 }
        ]
    }
}

IDS_SINTESIS = ["exclusivas", "mars_tema_1", "bms_tema_1", "arredo_tema_1", "arredo_tema_2", "amanco_tema_1", "booking_tema_1", "mars_competencia", "bms_tema_4", "arredo_tema_6", "amanco_tema_2", "booking_tema_2"]

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
        self.log_container = None
        self.timer_label = None
        self.init_secciones()

    def init_secciones(self):
        config = CLIENTES_CONFIG[self.cliente]
        self.links_manuales = {sec['id']: "" for sec in config["secciones"] if not sec.get('es_separador')}
        self.graficas = {sec['id']: [{"medio": "", "titulo": "", "fecha": datetime.datetime.now().strftime("%Y-%m-%d"), "link": "", "bajada": ""}] for sec in config["secciones"] if not sec.get('es_separador')}
        
    def add_grafica(self, sec_id):
        self.graficas[sec_id].append({"medio": "", "titulo": "", "fecha": datetime.datetime.now().strftime("%Y-%m-%d"), "link": "", "bajada": ""})
        
    def add_extra_search(self):
        self.extra_searches.append({"q": "", "sec": ""})

state = AppState()

# ====================================================================
# CARGA Y SINCRONIZACIÓN DE EXCEL (MÉTRICAS)
# ====================================================================
def sincronizar_base_medios(cliente_nombre, logger):
    logger("📁 Sincronizando Base de Medios desde Google Drive...")
    df_medios = None
    df_feeds = None
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
                
            logger("✅ Base de Medios sincronizada correctamente.")
    except Exception as e:
        logger(f"⚠️ No se pudo descargar la Base de Medios: {e}")
    return df_medios, df_feeds

# ====================================================================
# MOTOR DE SCRAPING Y EXTRACCIÓN DE METADATA
# ====================================================================
def formatear_fecha(texto_fecha):
    try:
        if not texto_fecha: return ""
        dt = email.utils.parsedate_to_datetime(texto_fecha)
        return dt.strftime("%d/%m/%Y")
    except: return ""

def remover_acentos(texto): 
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def es_bloqueo_waf(texto):
    firmas = ["performing security verification", "attention required! | cloudflare", "403 forbidden", "access denied", "just a moment...", "error 1020"]
    return any(f in (texto or "").lower() for f in firmas)

def corregir_mojibake(texto):
    reemplazos = {'Ã¡': 'á', 'Ã©': 'é', 'Ã-': 'í', 'Ã³': 'ó', 'Ãº': 'ú', 'Ã±': 'ñ', 'Ã': 'Á', 'Ã‰': 'É', 'Ã': 'Í', 'Ã“': 'Ó', 'Ãš': 'Ú', 'Ã‘': 'Ñ'}
    for mal, bien in reemplazos.items(): texto = (texto or "").replace(mal, bien)
    return texto

def limpiar_nombre_medio(medio):
    if not medio: return "Portal Argentino"
    texto = str(medio).strip()
    texto = re.sub(r'\.(com|net|org|info|gob|edu|tv)(\.[a-z]{2})?$', '', texto, flags=re.IGNORECASE)
    texto = re.sub(r'\.(ar|es|mx|cl|co)$', '', texto, flags=re.IGNORECASE)
    return texto.title()

def limpiar_basura_periodistica(texto):
    texto = texto or ""
    texto = re.sub(r'(http[s]?://\S+|www\.\S+)', '', texto, flags=re.IGNORECASE)
    for p in [r'Añadir .*? a tus preferidos en Google', r'Seguinos en .*', r'PUBLICIDAD', r'\d{1,2}/\d{1,2}/\d{2,4}\s*\|\s*\d{1,2}:\d{2}']:
        texto = re.sub(p, '', texto, flags=re.IGNORECASE)
    return " ".join(texto.split())

def contiene_palabra_clave(texto, palabras_clave):
    if not palabras_clave: return True
    texto_limpio = re.sub(r'(http[s]?://\S+|www\.\S+)', '', (texto or ""), flags=re.IGNORECASE)
    t_norm = remover_acentos(texto_limpio.lower())
    return any(re.search(r'\b' + re.escape(remover_acentos(k.lower())) + r'\b', t_norm, re.IGNORECASE) for k in palabras_clave)

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
        if 15 <= len(oracion.strip()) <= 2000 and contiene_palabra_clave(oracion, palabras_clave):
            if patron:
                return re.sub(f"({patron})", r"<strong>\1</strong>", oracion.strip(), flags=re.IGNORECASE)
            return oracion.strip()
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

def obtener_fecha_metadata(page):
    try:
        selectors = [
            'meta[property="article:published_time"]',
            'meta[name="pubdate"]',
            'meta[name="date"]',
            'meta[name="dc.date.issued"]',
            'time[datetime]'
        ]
        for sel in selectors:
            loc = page.locator(sel).first
            if loc.count() > 0:
                val = loc.get_attribute("content") or loc.get_attribute("datetime")
                if val:
                    match = re.search(r'(\d{4})[-/](\d{2})[-/](\d{2})', val)
                    if match: return f"{match.group(3)}/{match.group(2)}/{match.group(1)}"
    except: pass
    return ""

def construir_bloque_texto(resumen_meta, oracion, titulo, palabras_clave="", sec_id="", resumen_rss=""):
    secciones_destacadas = ['exclusivas', 'mars_tema_1', 'bms_tema_1', 'arredo_tema_1', 'arredo_tema_2', 'amanco_tema_1', 'booking_tema_1', 'mars_competencia', 'bms_tema_4', 'arredo_tema_6', 'amanco_tema_2', 'booking_tema_2']
    
    resumen_meta_limpio = limpiar_basura_periodistica(corregir_mojibake(resumen_meta)).replace("<em>", "").replace("</em>", "")
    titulo_limpio = limpiar_basura_periodistica(corregir_mojibake(titulo))
    
    tit_n = remover_acentos(titulo_limpio.lower()).strip()
    tit_compact = re.sub(r'[^a-z0-9]', '', tit_n)
    
    if resumen_meta_limpio and tit_compact:
        meta_n = remover_acentos(resumen_meta_limpio.lower()).strip()
        meta_compact = re.sub(r'[^a-z0-9]', '', meta_n)
        if len(tit_compact) > 10 and (tit_compact in meta_compact or meta_compact in tit_compact):
            resumen_meta_limpio = ""

    html = ""
    
    if sec_id in secciones_destacadas:
        if resumen_meta_limpio:
            html += f"<p style='font-size: 12px; font-family: Tahoma, sans-serif; line-height: 1.5; color: #000000; margin-top: 0; margin-bottom: 6px;'>{resumen_meta_limpio}</p>"
        
        oracion_final = ""
        if oracion and not oracion.startswith("[Nota inaccesible"):
            oracion_final = oracion
        elif resumen_rss:
            r_rss = limpiar_basura_periodistica(corregir_mojibake(resumen_rss))
            o_rss = extraer_oracion_clave(re.sub(r'<[^>]+>', '', r_rss), palabras_clave, sec_id) if r_rss else ""
            if o_rss: oracion_final = o_rss
            
        if oracion_final and tit_compact:
            texto_oracion_limpio = re.sub(r'<[^>]+>', '', oracion_final).strip()
            oracion_n = remover_acentos(texto_oracion_limpio.lower()).strip()
            oracion_compact = re.sub(r'[^a-z0-9]', '', oracion_n)
            if len(tit_compact) > 10 and (tit_compact in oracion_compact or oracion_compact in tit_compact):
                oracion_final = ""
                
        if oracion_final:
            texto_oracion_limpio = re.sub(r'<[^>]+>', '', oracion_final).strip()
            if not resumen_meta_limpio or texto_oracion_limpio not in resumen_meta_limpio:
                html += f"<p style='font-size: 12px; font-family: Tahoma, sans-serif; line-height: 1.5; color: #000000; margin-top: 0; margin-bottom: 6px;'>{oracion_final}</p>"
        else:
            html += f"<p style='font-size: 12px; font-family: Tahoma, sans-serif; line-height: 1.5; color: #888888; font-style: italic; margin-top: 0; margin-bottom: 6px;'>[Mención no detectada automáticamente en el texto visible]</p>"
    else:
        meta_tiene_kw = contiene_palabra_clave(resumen_meta_limpio, palabras_clave)
        if resumen_meta_limpio and meta_tiene_kw:
            html += f"<p style='font-size: 12px; font-family: Tahoma, sans-serif; line-height: 1.5; color: #000000; margin-top: 0; margin-bottom: 6px;'>{resumen_meta_limpio}</p>"
        elif oracion:
            if resumen_meta_limpio:
                html += f"<p style='font-size: 12px; font-family: Tahoma, sans-serif; line-height: 1.5; color: #000000; margin-top: 0; margin-bottom: 6px;'>{resumen_meta_limpio}</p>"
            html += f"<p style='font-size: 12px; font-family: Tahoma, sans-serif; line-height: 1.5; color: #000000; margin-top: 0; margin-bottom: 6px;'>{oracion}</p>"
        elif resumen_meta_limpio:
            html += f"<p style='font-size: 12px; font-family: Tahoma, sans-serif; line-height: 1.5; color: #000000; margin-top: 0; margin-bottom: 6px;'>{resumen_meta_limpio}</p>"
        else:
            html += "<p style='font-size: 12px; font-family: Tahoma, sans-serif; line-height: 1.5; color: #888888; font-style: italic; margin-top: 0; margin-bottom: 6px;'>Sin resumen disponible.</p>"
            
    return html

def buscar_metricas_medio(df_medios, url, medio_nombre):
    alcance, tier, ad_value = "?", "?", "?"
    if df_medios is None or df_medios.empty:
        return alcance, tier, ad_value

    netloc_clean = urlparse(url).netloc.replace("www.", "").split('.')[0].lower()
    medio_norm = limpiar_nombre_medio(medio_nombre).lower()
    
    medios_col = df_medios['medios'].astype(str).str.strip().str.lower()
    fila = df_medios[(medios_col == netloc_clean) | (medios_col == medio_norm)]
    
    if not fila.empty:
        alcance = str(fila['alcance'].iloc[0])
        tier = str(fila['tier'].iloc[0])
        ad_value = str(fila['advalue'].iloc[0])
        
    return alcance, tier, ad_value

def sort_key_final(n, sec_id):
    es_grafica = 0 if n['tipo_medio'] == 'Gráfica' else 1
    medio_lower = str(n['medio']).lower()
    
    if sec_id in IDS_SINTESIS:
        redes = ['instagram', 'facebook', 'threads', 'x.com', 'twitter', 'tiktok', 'linkedin']
        is_social = any(sm in medio_lower for sm in redes)
        
        tier_val = 99
        try:
            t_str = str(n['tier']).lower().strip()
            if t_str not in ['?', 'nan', '', 'null', 'none']:
                tier_val = int(float(t_str))
        except: pass
            
        alcance_val = 0.0
        try:
            a_str = str(n['alcance']).lower().strip().replace('.', '').replace(',', '')
            if a_str not in ['?', 'nan', '', 'null', 'none']:
                alcance_val = float(a_str)
        except: pass
            
        tiene_metricas = tier_val in [1, 2, 3]

        if es_grafica == 0: cat = 0
        elif tiene_metricas and not is_social: cat = 1
        elif is_social: cat = 2
        else: cat = 3
            
        return (cat, tier_val, -alcance_val, medio_lower)
    else:
        return (es_grafica, medio_lower)

def procesar_seccion(context, sec_id, nombre_seccion, lista_rss, links_manuales, notas_graficas_sec, palabras_clave, color_tema, limite_notas, logger, cliente_nombre, df_medios, solo_manuales=False):
    items = []
    secciones_destacadas = ['exclusivas', 'mars_tema_1', 'bms_tema_1', 'arredo_tema_1', 'arredo_tema_2', 'amanco_tema_1', 'booking_tema_1', 'mars_competencia', 'bms_tema_4', 'arredo_tema_6', 'amanco_tema_2', 'booking_tema_2']

    if links_manuales:
        logger(f"  ➜ Procesando {len(links_manuales)} link(s) manuales...")
        for url_manual in reversed(links_manuales):
            items.append((ObjetoManual(url_manual, "Nota Manual", ""), 'manual'))

    if lista_rss and not solo_manuales:
        logger(f"  ➜ Buscando en Google News...")
        for url_busqueda in lista_rss:
            try:
                req = urllib.request.urlopen(urllib.request.Request(url_busqueda, headers={'User-Agent': 'Mozilla/5.0'}))
                for it in BeautifulSoup(req.read(), "xml").find_all('item')[:30]: 
                    items.append((it, 'rss_google'))
            except: pass

    noticias_procesadas = []

    for ng in notas_graficas_sec:
        m_limpio = limpiar_nombre_medio(ng['medio'])
        fecha_format = datetime.datetime.strptime(ng['fecha'], "%Y-%m-%d").strftime("%d/%m/%Y") if ng.get('fecha') else datetime.datetime.now().strftime("%d/%m/%Y")
        alcance, tier, ad_value = buscar_metricas_medio(df_medios, ng['link'], m_limpio)

        noticias_procesadas.append({
            "medio": m_limpio, "tipo_medio": "Gráfica", "fecha": fecha_format,
            "alcance": alcance, "tier": tier, "ad_value": ad_value, "titulo": ng['titulo'], "link": ng['link'],
            "bajada_real": ng['bajada'], "oracion_clave": ng['bajada'], "origen": "grafica"
        })
        logger(f"    ✓ SUMADA [Gráfica]: {m_limpio[:20]} - {ng['titulo'][:30]}...")

    organicas_ok = 0

    for item, origen in items:
        if origen != 'manual' and organicas_ok >= limite_notas:
            continue

        link_orig = item.link.text
        titulo_bruto = item.title.text if item.title else "Sin Título"
        fecha_rss = formatear_fecha(item.pubDate.text if hasattr(item, 'pubDate') and item.pubDate else "")

        if origen != 'manual':
            titulo = re.sub(r'\s+[-|]\s+[^-|]+$', '', titulo_bruto).strip()
        else:
            titulo = titulo_bruto

        medio = item.source.text if hasattr(item, 'source') and item.source and item.source.text != "Manual" else urlparse(link_orig).netloc.replace("www.", "").split('.')[0].capitalize()
        
        origen_str = "Manual" if origen == 'manual' else "Online"
        logger(f"    🔎 Revisando [{origen_str}]: {link_orig[:40]}...")
        
        page = context.new_page()
        bajada, oracion, fecha_web = "", "", ""
        
        try:
            page.goto(link_orig, timeout=15000, wait_until="domcontentloaded")
            page.wait_for_timeout(1500)
            
            try:
                page.evaluate('''
                    document.querySelectorAll('aside, footer, nav, .sidebar, .widget, [class*="sidebar"], [id*="sidebar"], [class*="related"], [class*="popular"], [class*="trending"], [class*="most-read"], [class*="recomendado"]').forEach(el => el.remove());
                ''')
            except: pass

            t_web = page.title()
            if titulo in ["Manual", "Nota Manual"]: 
                titulo = re.sub(r'\s+[-|]\s+[^-|]+$', '', t_web).strip() if t_web else "Nota Manual"
            if medio == "Manual": 
                medio = urlparse(page.url).netloc.replace("www.", "").split('.')[0].capitalize()
            
            bajada = obtener_resumen_metadata(page)
            fecha_web = obtener_fecha_metadata(page)
            
            bajada_tiene_kw = contiene_palabra_clave(bajada, palabras_clave)
            if (sec_id in secciones_destacadas) or (not bajada_tiene_kw):
                try:
                    loc_p = page.locator("p")
                    count_p = loc_p.count()
                    textos_p = []
                    for i in range(min(count_p, 30)):
                        textos_p.append(loc_p.nth(i).inner_text())
                    t_cand_p = " ".join(textos_p)
                    if len(t_cand_p.strip()) > 50:
                        oracion = extraer_oracion_clave(t_cand_p, palabras_clave, sec_id)
                except: pass
                
                if not oracion:
                    for sel in ["article", "main", ".content", "body"]:
                        if page.locator(sel).first.count() > 0:
                            t_cand = page.locator(sel).first.inner_text(timeout=1500)
                            if len(t_cand.strip()) > 100:
                                oracion = extraer_oracion_clave(t_cand, palabras_clave, sec_id)
                                if oracion: break
                                
                if not oracion and origen in ['manual', 'nicho']: 
                    oracion = extraer_oracion_clave(bajada, palabras_clave, sec_id)
                
        except Exception as e:
            if origen != 'manual': 
                try: page.close() 
                except: pass
                continue
            logger(f"    ⚠️ Forzada [{origen_str}]: {titulo[:30]}")
            
        try: page.close()
        except: pass

        if origen != 'manual' and not contiene_palabra_clave(f"{titulo} {bajada} {oracion}", palabras_clave):
            continue

        alcance, tier, ad_value = buscar_metricas_medio(df_medios, page.url if 'page' in locals() and page else link_orig, medio)
        fecha_final = fecha_web if fecha_web else (fecha_rss if fecha_rss else datetime.datetime.now().strftime("%d/%m/%Y"))

        noticias_procesadas.append({
            "medio": limpiar_nombre_medio(medio), "tipo_medio": "Online", "fecha": fecha_final,
            "alcance": alcance, "tier": tier, "ad_value": ad_value, "titulo": titulo, "link": link_orig,
            "bajada_real": bajada, "oracion_clave": oracion, "resumen_rss": item.description.text if hasattr(item, 'description') and item.description else "", "origen": origen
        })
        logger(f"    ✓ SUMADA [{origen_str}]: {medio[:20]} - {titulo[:30]}...")
        
        if origen != 'manual': 
            organicas_ok += 1

    notas_manuales = [n for n in noticias_procesadas if n['origen'] in ['manual', 'grafica']]
    notas_google = [n for n in noticias_procesadas if n['origen'] not in ['manual', 'grafica']]

    notas_manuales = sorted(notas_manuales, key=lambda n: sort_key_final(n, sec_id))
    notas_google = sorted(notas_google, key=lambda n: sort_key_final(n, sec_id))

    noticias_finales = notas_manuales + notas_google

    for noti in noticias_finales:
        bloque_texto = construir_bloque_texto(noti['bajada_real'], noti['oracion_clave'], noti['titulo'], palabras_clave, sec_id, noti.get('resumen_rss', ''))
        
        tipo_html = f" <strong style='color: {color_tema}; font-size: 14px; font-family: Tahoma, sans-serif;'>({noti['tipo_medio']})</strong> " if noti['tipo_medio'] != "Gráfica" else " "
        
        if sec_id == 'booking_tema_1':
            info_metricas = f" <strong style='color: {color_tema}; font-size: 14px; font-family: Tahoma, sans-serif;'>Ad. Value: $ {noti['ad_value']}</strong> -"
        elif sec_id in IDS_SINTESIS:
            info_metricas = f" <span style='color: {color_tema}; font-size: 14px; font-family: Tahoma, sans-serif;'>(Alcance: {noti['alcance']} Tier: {noti['tier']})</span> <strong style='color: {color_tema}; font-size: 14px; font-family: Tahoma, sans-serif;'>Ad. Value: $ {noti['ad_value']}</strong> -"
        else:
            info_metricas = " -"
            
        html_indiv = f'''<p style="font-size: 14px; font-family: Tahoma, sans-serif; line-height: 1.5; margin-top: 0; margin-bottom: 4px; color: #000000;"><strong style="color: {color_tema}; font-size: 14px; font-family: Tahoma, sans-serif;">{noti['medio']}</strong>{tipo_html}<strong style="color: {color_tema}; font-size: 14px; font-family: Tahoma, sans-serif;">{noti['fecha']}</strong>{info_metricas} <a href="{noti['link']}" target="_blank" style="color: {color_tema}; text-decoration: none; font-size: 14px; font-weight: normal; font-family: Tahoma, sans-serif;">{noti['titulo']}</a></p>{bloque_texto}'''
        
        noti['html_bloque'] = html_indiv

    return noticias_finales

def orquestador_principal(links_manuales, notas_graficas, configuracion_cliente, cliente_nombre, logger, timeframe_google, solo_manuales=False, solo_banners=False):
    color = configuracion_cliente["color_primario"]
    estructura = configuracion_cliente["secciones"]
    data_editor = []

    if solo_banners:
        logger("⚡ Modo Dios: Prueba Rápida activada (Generando únicamente banners vacíos)...")
        for sec in estructura:
            if sec.get('es_separador', False): continue
            img_url = transformar_link_drive(sec.get('img_url', ''))
            data_editor.append({
                "id": sec['id'], "nombre": sec['nombre'], "img": img_url,
                "incluir_en_sintesis": sec['id'] in IDS_SINTESIS, "resumen_ia": "", "notas": []
            })
        return data_editor

    df_medios, df_feeds = sincronizar_base_medios(cliente_nombre, logger)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled", "--no-sandbox"])
        context = browser.new_context(viewport={"width": 1920, "height": 1080}, user_agent="Mozilla/5.0")
        
        for sec in estructura:
            logger(f"\n🔎 ANALIZANDO SECCIÓN: {sec['nombre_largo']}")
            if sec.get('es_separador', False): continue
            
            rss_ajustado = [enlace.replace("when:1d", f"when:{timeframe_google}").replace("when%3A1d", f"when%3A{timeframe_google}") for enlace in sec['rss']]
            
            notas_seccion = procesar_seccion(
                context, sec['id'], sec['nombre'], rss_ajustado, 
                links_manuales.get(sec['id'], []), notas_graficas.get(sec['id'], []),
                sec['keywords'], color, sec['limite'], logger, cliente_nombre, df_medios, solo_manuales=solo_manuales
            )

            img_url = transformar_link_drive(sec.get('img_url', ''))

            data_editor.append({
                "id": sec['id'], 
                "nombre": sec['nombre'], 
                "img": img_url,
                "incluir_en_sintesis": sec['id'] in IDS_SINTESIS,
                "resumen_ia": "",
                "notas": [{"html_bloque": n.get('html_bloque', '')} for n in notas_seccion]
            })

        context.close()
        browser.close()
    
    return data_editor

# ====================================================================
# GENERADOR HTML QUILL.JS CON HERRAMIENTA NATIVA DE HIPERVÍNCULOS
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
        .bloque-tools { display: flex; gap: 4px; background: #f8fafc; padding: 6px 10px; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 10px; flex-wrap: wrap; align-items: center; }
        
        .drag-handle { cursor: grab; color: #94a3b8; font-size: 18px; padding: 0 6px; user-select: none; }
        .drag-handle:active { cursor: grabbing; }

        .ql-container.ql-snow { border: none !important; font-family: 'Tahoma', sans-serif !important; }
        .ql-editor { font-family: 'Tahoma', sans-serif !important; padding: 4px 0 !important; line-height: 1.5 !important; }
        .ql-editor p { font-family: 'Tahoma', sans-serif !important; line-height: 1.5 !important; margin: 0 0 6px 0 !important; }
        
        .ql-toolbar.ql-snow { 
            border: none !important; 
            border-bottom: 1px solid #e2e8f0 !important; 
            background: #ffffff; 
            border-radius: 6px; 
            padding: 6px 10px !important; 
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
        .ql-toolbar.ql-snow button, .ql-toolbar.ql-snow .ql-picker-label {
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            float: none !important;
            height: 26px !important;
            width: 26px !important;
            padding: 2px !important;
        }
        
        .modal-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.5); align-items: center; justify-content: center; z-index: 100; }
        .modal-frame { background: white; width: 80%; height: 80%; border-radius: 12px; display: flex; flex-direction: column; overflow:hidden;}
        #iframe-preview { flex: 1; border: none; width: 100%; }
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
        <button class="btn btn-side" onclick="previewMailFinal()" style="background:#eef; color:#333;">
            <span class="btn-icon-symbol">👁️</span>
            <span class="sidebar-text">Vista Previa</span>
        </button>
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
        const GROQ_API_KEY = "__GROQ_API_KEY__";
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
                tempDiv.innerHTML = n.html_bloque;
                let enlace = tempDiv.querySelector('a');
                if (enlace) enlace.remove();
                let textContent = tempDiv.textContent || tempDiv.innerText || "";
                textContent = textContent.replace(/Ad\. Value: \$ [\d\.]+\s*-?/gi, '')
                                         .replace(/\(Online\)/gi, '')
                                         .replace(/\(Gráfica\)/gi, '')
                                         .replace(/\(Alcance:.*?\)/gi, '')
                                         .replace(/\[Mención no detectada.*?\]/gi, '')
                                         .replace(/Sin resumen disponible\./gi, '')
                                         .replace(/\d{2}\/\d{2}\/\d{4}/g, '');
                return textContent.replace(/\s+/g, ' ').trim().substring(0, 300);
            }).filter(t => t.length > 10);

            let texto_completo = textos_notas.join("\n").substring(0, 2500);
            
            let prompt = `Redacta un resumen de los siguientes textos en un único párrafo fluido de máximo 2 oraciones.\n\nReglas estrictas obligatorias:\n1. NO menciones ningún sitio web, portal ni medio de comunicación.\n2. NO copies ni menciones títulos de noticias.\n3. Escribe un párrafo de lectura natural (no uses listas, ni viñetas, ni guiones).\n4. Responde ÚNICAMENTE con el texto del resumen final, sin introducciones ni comentarios extra.\n\nTextos a resumir:\n${texto_completo}`;

            btnElement.innerHTML = '⏳ Generando...';
            btnElement.disabled = true;

            try {
                const response = await fetch('https://api.groq.com/openai/v1/chat/completions', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${GROQ_API_KEY}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        model: "openai/gpt-oss-20b",
                        messages: [{role: "user", content: prompt}],
                        temperature: 0.3,
                        max_tokens: 1024
                    })
                });

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
            estado.forEach(sec => total += sec.notas.length);
            document.getElementById('contador-total').innerHTML = 'Total notas: <strong>' + total + '</strong>';
        }

        function render() {
            const cont = document.getElementById('contenedor-secciones'); 
            cont.innerHTML = '';
            
            const secsSintesis = estado.filter(s => s.incluir_en_sintesis && s.notas && s.notas.length > 0);
            if (secsSintesis.length > 0) {
                const sinDiv = document.createElement('div');
                sinDiv.className = 'seccion';
                sinDiv.style.borderLeft = '5px solid var(--tema_color)';
                sinDiv.style.background = '#f8fafc';

                const sHeader = document.createElement('div');
                sHeader.style.padding = '14px 20px';
                sHeader.style.fontWeight = 'bold';
                sHeader.style.fontStyle = 'italic';
                sHeader.style.color = 'var(--tema_color)';
                sHeader.style.fontSize = '15px';
                sHeader.innerHTML = 'SÍNTESIS DEL DÍA · RESUMEN IA';
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

                        const tools = document.createElement('div'); 
                        tools.className = 'bloque-tools';
                        tools.innerHTML = `
                            <span class="drag-handle" title="Arrastrar y soltar">☰</span>
                            <button class="btn btn-icon" onclick="moverNota(${secIdx}, ${notaIdx}, -1)">↑ Subir</button>
                            <button class="btn btn-icon" onclick="moverNota(${secIdx}, ${notaIdx}, 1)">↓ Bajar</button>
                            <button class="btn btn-icon" onclick="duplicarNota(${secIdx}, ${notaIdx})">⧉ Duplicar</button>
                            <button class="btn btn-icon" onclick="editarLinkNota(${secIdx}, ${notaIdx})">🔗 Link</button>
                            <button class="btn btn-icon danger" onclick="borrarNota(${secIdx}, ${notaIdx})">🗑 Borrar</button>
                            <select class="btn btn-icon" onchange="moverASeccion(${secIdx}, ${notaIdx}, this.value)">
                                <option disabled selected>⇋ Mover a...</option>
                                ${estado.map((s, idx) => idx !== secIdx ? `<option value="${idx}">${s.nombre}</option>` : '').join('')}
                            </select>
                        `;

                        const editorContainer = document.createElement('div');
                        const editorDivId = `quill-${secIdx}-${notaIdx}`;
                        editorContainer.id = editorDivId;
                        editorContainer.innerHTML = nota.html_bloque;
                        
                        bloque.appendChild(tools);
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

            const secsSintesis = estado.filter(s => s.incluir_en_sintesis && s.notas && s.notas.length > 0);
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

            estado.forEach((sec, secIdx) => {
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
                    }
                });
            });
        }

        function editarLinkNota(secIdx, notaIdx) {
            let q = quillInstances[`quill-${secIdx}-${notaIdx}`];
            let currentHtml = q ? q.root.innerHTML : estado[secIdx].notas[notaIdx].html_bloque;

            let temp = document.createElement('div');
            temp.innerHTML = currentHtml;

            let aTag = temp.querySelector('a');

            if (aTag) {
                let urlActual = aTag.getAttribute('href') || '';
                let nuevaUrl = prompt('Ingresá la URL para hipervincular la nota:', urlActual);
                if (nuevaUrl !== null && nuevaUrl.trim() !== '') {
                    aTag.setAttribute('href', nuevaUrl.trim());
                    aTag.setAttribute('target', '_blank');
                    aTag.style.color = '__COLOR_CLIENTE__';
                    aTag.style.textDecoration = 'none';
                    aTag.style.fontWeight = 'normal';
                    aTag.style.fontSize = '14px';
                    aTag.style.fontFamily = 'Tahoma, sans-serif';

                    let nuevoHtml = temp.innerHTML;
                    estado[secIdx].notas[notaIdx].html_bloque = nuevoHtml;
                    if (q) q.root.innerHTML = nuevoHtml;
                    guardarBorrador();
                }
            } else {
                let pTag = temp.querySelector('p') || temp;
                let nuevaUrl = prompt('La nota no tiene link. Ingresá la URL para hipervincular el título:', 'https://');
                if (nuevaUrl !== null && nuevaUrl.trim() !== '') {
                    let textHtml = pTag.innerHTML;
                    if (textHtml.includes('-')) {
                        let parts = textHtml.split('-');
                        let header = parts[0];
                        let rest = parts.slice(1).join('-');
                        let cleanRest = rest.replace(/<[^>]+>/g, '').trim() || 'Ver Nota';
                        pTag.innerHTML = `${header}- <a href="${nuevaUrl.trim()}" target="_blank" style="color: __COLOR_CLIENTE__; text-decoration: none; font-size: 14px; font-weight: normal; font-family: Tahoma, sans-serif;">${cleanRest}</a>`;
                    } else {
                        let cleanText = pTag.innerText.trim() || 'Ver Nota';
                        pTag.innerHTML = `<a href="${nuevaUrl.trim()}" target="_blank" style="color: __COLOR_CLIENTE__; text-decoration: none; font-size: 14px; font-weight: normal; font-family: Tahoma, sans-serif;">${cleanText}</a>`;
                    }

                    let nuevoHtml = temp.innerHTML;
                    estado[secIdx].notas[notaIdx].html_bloque = nuevoHtml;
                    if (q) q.root.innerHTML = nuevoHtml;
                    guardarBorrador();
                }
            }
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

        function moverASeccion(s, n, targetSec) {
            const target = parseInt(targetSec);
            const nota = estado[s].notas.splice(n, 1)[0];
            estado[target].notas.push(nota);
            render();
            guardarBorrador();
        }

        function generarHtmlFinal(){
            let html = '<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">';
            html += '<style>body, table, td, p, div, span, a { font-family: Tahoma, sans-serif !important; } p { margin: 0 0 6px 0 !important; line-height: 1.5 !important; } a { text-decoration: none; }</style>';
            html += '</head><body style="margin: 0; padding: 0; background-color: #f4f4f9; font-family: Tahoma, sans-serif;">';
            html += '<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f4f4f9; padding: 20px 0;"><tr><td align="center"><table width="600" cellpadding="0" cellspacing="0" border="0" style="background-color: #ffffff; border: 1px solid #cccccc;">';
            
            html += `<tr><td align="center" style="padding: 0;"><img src="${BANNER_PRINCIPAL}" alt="Banner Principal" width="600" style="display: block; max-width: 600px; height: auto; border: 0;"></td></tr>`;
            
            const secsExc = estado.filter(s => s.incluir_en_sintesis && s.notas && s.notas.length > 0);
            if(secsExc.length > 0){ 
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
                            items.push('<li style="margin-bottom: 4px;"><strong>' + medioReal + ':</strong> <a href="' + linkUrl + '" target="_blank" style="color: __COLOR_CLIENTE__; text-decoration: none; font-size: 12px;">' + tituloReal + '</a></li>');
                        });
                        html_sintesis += '<ul style="margin: 0 0 10px 0; padding-left: 18px; font-family: Tahoma, sans-serif; font-size: 12px; line-height: 1.5; color: #333333;">' + items.join('\n') + '</ul>';
                    }
                });

                html_sintesis += '</td></tr></table></td></tr>';
                html += html_sintesis;
            }

            estado.forEach((sec, index) => {
                if(index !== 0 || secsExc.length > 0) {
                    html += '<tr><td style="font-size: 0px; line-height: 0px; height: 20px;">&nbsp;</td></tr>';
                }
                
                if(sec.img) {
                    html += `<tr><td align="center" style="padding: 0;"><img src="${sec.img}" alt="Banner Seccion" width="600" style="display: block; max-width: 600px; height: auto; border: 0;"></td></tr>`;
                }

                if(sec.notas.length === 0) {
                    html += `<tr><td style="padding: 20px;"><p style="font-family: Tahoma, sans-serif; font-size: 12px; color: __COLOR_CLIENTE__; font-weight: bold; margin: 0;"><strong style="color: __COLOR_CLIENTE__;">No se produjeron menciones</strong></p></td></tr>`;
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
            a.download = 'Reporte_Clipping.html';
            a.click();
        }
        
        function previewMailFinal(){
            document.getElementById('iframe-preview').srcdoc = generarHtmlFinal();
            document.getElementById('modal-preview').style.display = 'flex';
        }

        // RENDERIZADO INMEDIATO
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
    plantilla = plantilla.replace("__GROQ_API_KEY__", GROQ_API_KEY)
    plantilla = plantilla.replace("__REPORT_ID__", report_id)
    return plantilla

# ====================================================================
# INTERFAZ NICEGUI
# ====================================================================

@ui.page('/')
async def index():
    ui.add_head_html('''
    <style>
        body {
            background-color: #f2f4f7 !important;
            background-image: 
                radial-gradient(circle at 15% 15%, rgba(0, 110, 116, 0.08) 0%, transparent 45%),
                radial-gradient(circle at 85% 85%, rgba(0, 110, 116, 0.06) 0%, transparent 45%),
                radial-gradient(rgba(0, 110, 116, 0.07) 1px, transparent 1px) !important;
            background-size: 100% 100%, 100% 100%, 24px 24px !important;
            background-attachment: fixed !important;
        }
    </style>
    ''')

    await ui.context.client.connected()

    if not app.storage.tab.get('authenticated', False):
        with ui.card().classes('absolute-center items-center p-8 shadow-xl rounded-2xl w-96'):
            ui.label('🔒 Acceso Restringido').classes('text-2xl font-bold text-[#006E74] mb-2')
            ui.label('Ingresá tus credenciales').classes('text-gray-500 mb-6')
            
            user_input = ui.input('👤 Usuario').classes('w-full mb-2')
            pass_input = ui.input('🔑 Contraseña').props('type=password').classes('w-full mb-6')
            
            def attempt_login():
                usr = user_input.value
                pwd = pass_input.value
                if usr in CREDENCIALES and CREDENCIALES[usr] == pwd:
                    app.storage.tab['authenticated'] = True
                    app.storage.tab['username'] = usr
                    registrar_actividad(usr, "Inicio de sesión", "Acceso exitoso al sistema")
                    ui.navigate.reload()
                else:
                    ui.notify('❌ Usuario o contraseña incorrectos', color='negative')

            ui.button('Ingresar al Sistema', on_click=attempt_login).classes('w-full bg-[#006E74] text-white font-bold rounded-lg')
        return

    @ui.refreshable
    def header_title():
        ui.label(f'📰 Editor de: {state.cliente}').classes('text-xl font-bold tracking-wide')

    with ui.header().classes('justify-between items-center bg-[#006E74] shadow-md px-6 py-3'):
        header_title()
        def logout():
            registrar_actividad(app.storage.tab.get('username', 'usuario'), "Cierre de sesión", "Salió del sistema")
            app.storage.tab['authenticated'] = False
            ui.navigate.reload()
        with ui.row().classes('items-center gap-4'):
            ui.label(f'v{APP_VERSION}').classes('text-white italic text-sm')
            ui.button('🚪 Cerrar Sesión', on_click=logout).props('flat text-color=white').classes('font-bold')

    with ui.left_drawer(value=True).classes('bg-[#f8f9fa] border-r border-gray-200 p-6'):
        
        if app.storage.tab.get('username') == 'admin':
            with ui.card().classes('w-full p-4 mb-6 border border-amber-300 bg-amber-50 shadow-sm rounded-xl'):
                ui.label('🛠️ MODO DIOS (Admin)').classes('text-xs font-bold text-amber-800 tracking-wider mb-2')
                
                ui.button('📝 Reporte SOLO MANUALES', on_click=lambda: procesar_reporte(solo_manuales=True)).props('dense outline text-color=amber-9').classes('w-full mb-2 font-bold')
                ui.button('⚡ Prueba Rápida (Solo Banners)', on_click=lambda: procesar_reporte(solo_banners=True)).props('dense color=amber-8').classes('w-full font-bold text-white')
                
                with ui.expansion('🕵️‍♂️ Ver Log Actividad').classes('w-full mt-2 text-xs font-bold'):
                    if os.path.exists("registro_uso.csv"):
                        with open("registro_uso.csv", "r", encoding="utf-8") as f:
                            contenido_log = f.read()
                        ui.textarea(value=contenido_log).props('readonly').classes('w-full text-xs font-mono')
                    else:
                        ui.label('Aún no hay actividad registrada.').classes('text-xs text-gray-500')

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

    async def procesar_reporte(solo_manuales=False, solo_banners=False):
        if not state.log_container or not state.timer_label:
            ui.notify('❌ Error de UI: La consola no está lista', color='negative')
            return

        state.timer_label.classes(remove='hidden')
        state.log_container.classes(remove='hidden')
        state.log_container.push("🚀 Iniciando motor de procesamiento...")
        
        registrar_actividad(app.storage.tab.get('username', 'usuario'), "Generó Reporte", f"Cliente: {state.cliente} | Manuales: {solo_manuales} | Banners: {solo_banners}")
        
        start_time = datetime.datetime.now()
        def update_chrono():
            elapsed = int((datetime.datetime.now() - start_time).total_seconds())
            mins, secs = divmod(elapsed, 60)
            if state.timer_label:
                state.timer_label.set_text(f'⏱️ Tiempo transcurrido: {mins:02d}:{secs:02d}')
            
        ui_chrono = ui.timer(1.0, update_chrono)
        
        config = CLIENTES_CONFIG[state.cliente]
        datos_links = {}
        datos_grafica = {}
        for s in config['secciones']:
            sid = s['id']
            raw_links = state.links_manuales.get(sid, "")
            datos_links[sid] = [url.strip() for url in re.split(r'[,\n\s]+', raw_links) if url.strip() and url.strip().startswith('http')]
            datos_grafica[sid] = [g for g in state.graficas.get(sid, []) if g['medio'].strip() and g['titulo'].strip()]

        log_queue = queue.Queue()
        def safe_logger(msg): log_queue.put(msg)
        
        def flush_logs():
            while not log_queue.empty():
                if state.log_container:
                    state.log_container.push(log_queue.get())

        ui_timer = ui.timer(0.5, flush_logs)

        try:
            data_editor = await run.io_bound(
                orquestador_principal,
                datos_links,
                datos_grafica,
                config,
                state.cliente,
                safe_logger,
                state.timeframe,
                solo_manuales,
                solo_banners
            )
            
            flush_logs()
            ui_timer.deactivate()
            ui_chrono.deactivate()

            if state.log_container:
                state.log_container.push("✅ PROCESO TERMINADO. Generando editor...")
            html_resultado = generar_html_editor(config["banner_principal_url"], data_editor, config["color_primario"], state.cliente)
            
            fecha_hoy = datetime.datetime.now().strftime("%d-%m-%y")
            nombre_archivo = f'Clipping {state.cliente} {fecha_hoy}.html'
            
            ui.download(html_resultado.encode('utf-8'), nombre_archivo)
            ui.notify('🎉 Reporte procesado y descargado exitosamente', color='positive', position='top')
        except Exception as e:
            flush_logs()
            ui_timer.deactivate()
            ui_chrono.deactivate()
            if state.log_container:
                state.log_container.push(f"❌ Error durante el proceso: {str(e)}")
            ui.notify('❌ Error al generar. Mirá el log de pantalla.', color='negative')

    @ui.refreshable
    def main_content():
        config = CLIENTES_CONFIG[state.cliente]
        color = config['color_primario']
        
        with ui.column().classes('w-full max-w-5xl mx-auto p-8'):
            
            try:
                url_cb = f"{URL_VERSION_GITHUB}?t={int(time.time())}"
                resp = requests.get(url_cb, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
                if resp.status_code == 200:
                    v_git = resp.text.strip().replace('"', '').replace("'", "")
                    v_git_clean = re.sub(r'[^0-9.]', '', v_git)
                    app_v_clean = re.sub(r'[^0-9.]', '', APP_VERSION)
                    if v_git_clean and v_git_clean != app_v_clean:
                        async def auto_actualizar():
                            try:
                                ui.notify('⏳ Descargando actualización desde GitHub...', type='info', position='top-right')
                                url_code_cb = f"{URL_MAIN_PYTHON_GITHUB}?t={int(time.time())}"
                                r_code = requests.get(url_code_cb, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
                                if r_code.status_code == 200 and len(r_code.text) > 500:
                                    ruta_script = os.path.abspath(sys.argv[0])
                                    with open(ruta_script, "w", encoding="utf-8") as f:
                                        f.write(r_code.text)
                                    ui.notify('✅ ¡Actualización instalada correctamente! Reiniciando...', type='positive', position='top-right')
                                    await asyncio.sleep(1.5)
                                    os.execv(sys.executable, [sys.executable] + sys.argv)
                                else:
                                    ui.notify('❌ No se pudo descargar el código de actualización.', type='negative', position='top-right')
                            except Exception as err:
                                ui.notify(f'❌ Error al actualizar: {str(err)}', type='negative', position='top-right')

                        with ui.card().classes('w-full bg-amber-500 text-white font-bold p-3 mb-4 shadow-md rounded-xl'):
                            with ui.row().classes('items-center justify-between w-full px-2'):
                                ui.label(f'🚀 ¡Nueva versión ({v_git}) disponible!')
                                ui.button('⚡ Actualizar y Reiniciar', on_click=auto_actualizar).props('flat text-color=white bg-black').classes('rounded-lg')
            except Exception as e:
                print(f"Error en chequeo de versión: {e}")

            with ui.card().classes('w-full mb-6 p-4 border border-gray-200 shadow-sm rounded-xl bg-white'):
                with ui.row().classes('items-center justify-between w-full'):
                    with ui.row().classes('items-center gap-3'):
                        ui.avatar('business', color=f'[{color}]', text_color='white', size='md')
                        with ui.column().classes('gap-0'):
                            ui.label('CLIENTE ACTIVO').classes('text-xs font-bold text-gray-400 tracking-wider')
                            ui.label(state.cliente).classes('text-2xl font-black').style(f'color: {color};')
                    ui.chip(f'Rango: {state.timeframe}', color='grey-2', text_color='grey-8').classes('font-bold')

            for sec in config['secciones']:
                if sec.get('es_separador', False): continue
                
                with ui.card().classes('w-full mb-8 p-6 border shadow-sm').style('border-radius: 12px;'):
                    ui.html(f"<h3 style='color: {color}; margin:0; font-weight:800; font-size: 20px;'>📁 {sec['nombre_largo']}</h3>")
                    
                    ui.label("🔗 Notas Web Manuales").classes('font-bold text-gray-700 mt-4')
                    ui.textarea('Pegá los links (separados por coma o con un enter)').bind_value(state.links_manuales, sec['id']).classes('w-full bg-gray-50')
                    
                    ui.label("🗞️ Agregar Nota Gráfica / PDF").classes('font-bold text-gray-700 mt-6 mb-2')
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

                    ui.button("➕ Sumar otra nota gráfica", on_click=lambda sid=sec['id']: (state.add_grafica(sid), main_content.refresh())).props(f'outline text-color={color.strip("#")}').classes('mt-2')
            
            ui.separator().classes('my-6')
            
            state.timer_label = ui.label('⏱️ Tiempo transcurrido: 00:00').classes('font-bold text-gray-700 mb-2 hidden')
            state.log_container = ui.log(max_lines=30).classes('w-full h-48 bg-gray-900 text-green-400 p-4 rounded-lg font-mono text-sm hidden')

            ui.button('🚀 PROCESAR REPORTE', on_click=lambda: procesar_reporte()).classes('w-full py-4 text-lg font-bold shadow-lg rounded-xl mt-4').style(f'background-color: {color}; color: white;')

    main_content()

ui.run(title="Generador Clipping", port=8080, language="es", storage_secret="clipping2026_secret_key")
