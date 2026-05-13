"""
Парсер автошкол через 2GIS API.

2GIS предоставляет бесплатный публичный API для поиска организаций.
Документация: https://docs.2gis.com/ru/api/search/regions/overview

Переменные окружения:
  TWOGIS_API_KEY — ключ 2GIS (получить на https://dev.2gis.ru/)
                   Без ключа используется публичный эндпоинт с лимитами.

Лимиты бесплатного тарифа: 1000 запросов/день.
"""

import os
import re
import time
import logging
import requests
from src.parser_avtoshkoli import School
from src.parser_yandex import _detect_categories, _extract_legal_name, CITY_COORDS

log = logging.getLogger(__name__)

TWOGIS_SEARCH_URL = "https://catalog.api.2gis.com/3.0/items"

# Рубрика автошкол в 2GIS
RUBRIC_ID = "164"  # «Автошколы»

SEARCH_QUERIES = [
    "автошкола категория C",
    "автошкола категория CE грузовые",
    "обучение вождению грузовик",
]


def get_api_key() -> str:
    return os.environ.get("TWOGIS_API_KEY", "")


def search_2gis(city: str, query: str, api_key: str) -> list[School]:
    """Поиск автошкол в городе через 2GIS Catalog API."""
    params = {
        "q": f"{query}",
        "locale": "ru_RU",
        "region_id": _get_region_id(city),
        "type": "branch",
        "rubric_id": RUBRIC_ID,
        "page_size": 50,
        "fields": "items.org,items.contact_groups,items.rubrics,items.description,items.point",
    }
    if api_key:
        params["key"] = api_key
    else:
        # Публичный ключ — работает с ограничениями
        params["key"] = "demo"

    all_items = []
    page = 1
    while True:
        params["page"] = page
        try:
            resp = requests.get(TWOGIS_SEARCH_URL, params=params, timeout=15)
            if resp.status_code in (401, 403):
                log.warning("2GIS: ошибка авторизации. Получите ключ на https://dev.2gis.ru/")
                return []
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            log.warning(f"2GIS API ошибка ({city}): {e}")
            break
        except ValueError:
            log.warning(f"2GIS: не удалось разобрать JSON для {city}")
            break

        result = data.get("result", {})
        items = result.get("items", [])
        if not items:
            break
        all_items.extend(items)

        total = result.get("total", 0)
        if len(all_items) >= total or page >= 5:  # не более 5 страниц
            break
        page += 1
        time.sleep(0.3)

    schools = []
    for item in all_items:
        school = _parse_2gis_item(item, city)
        if school:
            schools.append(school)

    log.info(f"  2GIS: {city} / «{query}» → {len(schools)} результатов")
    return schools


def _parse_2gis_item(item: dict, city: str) -> School | None:
    """Разбирает один элемент из ответа 2GIS."""
    name = item.get("name", "")
    if not name:
        return None

    # Фильтр — только автошколы
    name_lower = name.lower()
    rubrics = " ".join(r.get("name", "").lower() for r in item.get("rubrics", []))
    desc = item.get("description", "") or ""
    combined = name_lower + " " + rubrics + " " + desc.lower()

    if not any(kw in combined for kw in ["автошкол", "вождени", "автокурс", "досааф", "автошколы"]):
        return None

    # Адрес
    address = item.get("address_name", "") or item.get("full_address_name", "") or ""

    # Телефоны
    phones = []
    for group in item.get("contact_groups", []):
        for contact in group.get("contacts", []):
            if contact.get("type") in ("phone", "fax"):
                val = contact.get("value", "")
                if val:
                    phones.append(val)
    phone = ", ".join(phones[:3])  # не более 3 номеров

    # Сайт
    website = ""
    for group in item.get("contact_groups", []):
        for contact in group.get("contacts", []):
            if contact.get("type") == "website":
                website = contact.get("value", "")
                if website:
                    break

    # Юридическое название из поля org
    org = item.get("org", {})
    legal_name = org.get("legal_name", "") or org.get("name", "") or ""
    if not legal_name:
        legal_name = _extract_legal_name(name + " " + desc)

    # Ссылка: сайт школы или страница в 2GIS
    item_id = item.get("id", "")
    maps_url = f"https://2gis.ru/{_city_slug(city)}/firm/{item_id}" if item_id else ""
    source_link = website or maps_url

    # Категории
    cats = _detect_categories(name + " " + desc)

    return School(
        name=name,
        city=city,
        address=address,
        phone=phone,
        categories=cats if cats else ["C"],
        legal_name=legal_name,
        price="",
        rating=str(item.get("reviews", {}).get("rating_general", "")),
        reviews=str(item.get("reviews", {}).get("general_review_count", "")),
        source_url=source_link,
        source="2gis",
    )


# Маппинг города → region_id в 2GIS
# Получен из https://catalog.api.2gis.com/3.0/regions?key=demo
CITY_REGION_IDS = {
    "Москва": "1",
    "Санкт-Петербург": "2",
    "Новосибирск": "4",
    "Екатеринбург": "3",
    "Казань": "11",
    "Нижний Новгород": "14",
    "Челябинск": "9",
    "Омск": "5",
    "Самара": "16",
    "Ростов-на-Дону": "10",
    "Уфа": "12",
    "Красноярск": "6",
    "Воронеж": "20",
    "Пермь": "15",
    "Волгоград": "18",
    "Краснодар": "35",
    "Саратов": "19",
    "Тюмень": "17",
    "Тольятти": "16",
    "Ижевск": "23",
    "Барнаул": "22",
    "Ульяновск": "25",
    "Иркутск": "7",
    "Хабаровск": "8",
    "Ярославль": "28",
    "Владивосток": "13",
    "Томск": "24",
    "Оренбург": "26",
    "Кемерово": "30",
    "Новокузнецк": "30",
    "Рязань": "29",
    "Астрахань": "32",
    "Набережные Челны": "11",
    "Пенза": "33",
    "Липецк": "36",
    "Тула": "37",
    "Киров": "34",
    "Чебоксары": "38",
    "Калининград": "39",
    "Брянск": "40",
    "Курск": "41",
    "Иваново": "42",
    "Тверь": "43",
    "Ставрополь": "44",
    "Белгород": "45",
    "Сочи": "46",
    "Архангельск": "47",
    "Владимир": "48",
    "Смоленск": "49",
    "Мурманск": "50",
    "Сургут": "51",
    "Кострома": "52",
    "Вологда": "53",
    "Псков": "54",
    "Тамбов": "55",
    "Орёл": "56",
    "Калуга": "57",
    "Курган": "58",
    "Абакан": "59",
    "Петрозаводск": "60",
    "Сыктывкар": "61",
    "Нальчик": "62",
    "Владикавказ": "63",
    "Грозный": "64",
    "Якутск": "65",
    "Улан-Удэ": "66",
    "Чита": "67",
}

CITY_SLUGS = {
    "Москва": "moscow",
    "Санкт-Петербург": "spb",
    "Новосибирск": "novosibirsk",
    "Екатеринбург": "ekaterinburg",
    "Казань": "kazan",
    "Нижний Новгород": "n_novgorod",
    "Челябинск": "chelyabinsk",
    "Омск": "omsk",
    "Самара": "samara",
    "Ростов-на-Дону": "rostov_na_donu",
    "Уфа": "ufa",
    "Красноярск": "krasnoyarsk",
    "Воронеж": "voronezh",
    "Пермь": "perm",
    "Волгоград": "volgograd",
    "Краснодар": "krasnodar",
}


def _get_region_id(city: str) -> str:
    return CITY_REGION_IDS.get(city, "1")


def _city_slug(city: str) -> str:
    return CITY_SLUGS.get(city, city.lower().replace(" ", "_").replace("-", "_"))


def scrape_all_2gis(cities: list[str] = None) -> list[School]:
    """Собирает автошколы категории C+ по всем городам через 2GIS."""
    api_key = get_api_key()
    if not api_key:
        log.warning("TWOGIS_API_KEY не задан — используется demo-ключ с лимитами.")
        log.warning("Получите бесплатный ключ на https://dev.2gis.ru/")

    cities = cities or list(CITY_COORDS.keys())
    all_schools: dict[str, School] = {}
    total = len(cities) * len(SEARCH_QUERIES)
    done = 0

    for city in cities:
        for query in SEARCH_QUERIES:
            done += 1
            log.info(f"[{done}/{total}] 2GIS: {city} / «{query}»")
            found = search_2gis(city, query, api_key)

            for school in found:
                key = school.dedup_key
                if key in all_schools:
                    existing = all_schools[key]
                    for c in school.categories:
                        if c not in existing.categories:
                            existing.categories.append(c)
                    if not existing.phone and school.phone:
                        existing.phone = school.phone
                    if not existing.legal_name and school.legal_name:
                        existing.legal_name = school.legal_name
                else:
                    all_schools[key] = school

            time.sleep(0.5)

    result = list(all_schools.values())
    log.info(f"2GIS: итого {len(result)} уникальных школ")
    return result
