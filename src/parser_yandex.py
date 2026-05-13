"""
Парсер автошкол через Яндекс Бизнес API (geocoder + places search).

Яндекс предоставляет два бесплатных инструмента:
  1. Геокодер — https://geocoder.maps.yandex.ru  (1 000 запросов/день бесплатно)
  2. Places / Geosearch — https://search-maps.yandex.ru  (500 запросов/день бесплатно)

Для получения ключа: https://developer.tech.yandex.ru/
Создайте приложение и подключите «JavaScript API и HTTP Геокодер» + «Геопоиск».

Переменные окружения:
  YANDEX_API_KEY — ключ от Яндекс.Разработчика

Использование:
  YANDEX_API_KEY=ваш_ключ python main.py --source yandex
"""

import os
import time
import logging
import requests
from src.parser_avtoshkoli import School, CITIES

log = logging.getLogger(__name__)

YANDEX_SEARCH_URL = "https://search-maps.yandex.ru/v1/"

# Запросы для поиска — Яндекс лучше ищет по естественному языку
SEARCH_QUERIES = [
    "автошкола категория C грузовые",
    "автошкола категория CE",
    "обучение вождению грузовик",
]

# Города со списком: (название для запроса, координаты центра для геопоиска)
CITY_COORDS = {
    "Москва":           (55.7558, 37.6173),
    "Санкт-Петербург":  (59.9343, 30.3351),
    "Новосибирск":      (54.9833, 82.8964),
    "Екатеринбург":     (56.8389, 60.6057),
    "Казань":           (55.7963, 49.1088),
    "Нижний Новгород":  (56.2965, 43.9361),
    "Челябинск":        (55.1644, 61.4368),
    "Омск":             (54.9885, 73.3242),
    "Самара":           (53.2001, 50.1500),
    "Ростов-на-Дону":   (47.2357, 39.7015),
    "Уфа":              (54.7388, 55.9721),
    "Красноярск":       (56.0153, 92.8932),
    "Воронеж":          (51.6755, 39.2088),
    "Пермь":            (58.0105, 56.2502),
    "Волгоград":        (48.7080, 44.5133),
    "Краснодар":        (45.0355, 38.9753),
    "Саратов":          (51.5336, 46.0343),
    "Тюмень":           (57.1522, 68.0082),
    "Тольятти":         (53.5303, 49.3461),
    "Ижевск":           (56.8527, 53.2114),
    "Барнаул":          (53.3606, 83.7636),
    "Ульяновск":        (54.3282, 48.3866),
    "Иркутск":          (52.2978, 104.2964),
    "Хабаровск":        (48.4802, 135.0719),
    "Ярославль":        (57.6261, 39.8845),
    "Владивосток":      (43.1155, 131.8855),
    "Томск":            (56.4977, 84.9744),
    "Оренбург":         (51.7727, 55.0988),
    "Кемерово":         (55.3904, 86.0478),
    "Новокузнецк":      (53.7557, 87.1099),
    "Рязань":           (54.6269, 39.6916),
    "Астрахань":        (46.3479, 48.0335),
    "Набережные Челны": (55.7435, 52.4045),
    "Пенза":            (53.1959, 45.0183),
    "Липецк":           (52.6031, 39.5702),
    "Тула":             (54.1927, 37.6173),
    "Киров":            (58.6035, 49.6680),
    "Чебоксары":        (56.1439, 47.2489),
    "Калининград":      (54.7065, 20.5110),
    "Брянск":           (53.2521, 34.3717),
    "Курск":            (51.7304, 36.1927),
    "Иваново":          (57.0005, 40.9739),
    "Магнитогорск":     (53.4072, 58.9833),
    "Тверь":            (56.8587, 35.9176),
    "Ставрополь":       (45.0446, 41.9691),
    "Белгород":         (50.5997, 36.5940),
    "Сочи":             (43.5855, 39.7232),
    "Архангельск":      (64.5401, 40.5433),
    "Владимир":         (56.1291, 40.4062),
    "Смоленск":         (54.7827, 32.0453),
    "Мурманск":         (68.9585, 33.0827),
    "Сургут":           (61.2540, 73.3963),
    "Кострома":         (57.7676, 40.9270),
    "Вологда":          (59.2239, 39.8845),
    "Псков":            (57.8194, 28.3319),
    "Тамбов":           (52.7212, 41.4521),
    "Орёл":             (52.9651, 36.0785),
    "Калуга":           (54.5293, 36.2754),
    "Курган":           (55.4507, 65.3234),
    "Абакан":           (53.7210, 91.4420),
    "Петрозаводск":     (61.7849, 34.3469),
    "Сыктывкар":        (61.6688, 50.8357),
    "Нальчик":          (43.4986, 43.6165),
    "Владикавказ":      (43.0481, 44.6673),
    "Грозный":          (43.3180, 45.6988),
    "Уфа":              (54.7388, 55.9721),
    "Якутск":           (62.0355, 129.6755),
    "Улан-Удэ":         (51.8272, 107.6062),
    "Чита":             (52.0315, 113.4994),
}


def get_api_key() -> str:
    key = os.environ.get("YANDEX_API_KEY", "")
    if not key:
        raise EnvironmentError(
            "Не задан YANDEX_API_KEY.\n"
            "Получите ключ на https://developer.tech.yandex.ru/\n"
            "Затем запустите: YANDEX_API_KEY=ваш_ключ python main.py --source yandex"
        )
    return key


def search_schools_in_city(city: str, coords: tuple, query: str, api_key: str) -> list[School]:
    """Один запрос к Яндекс Геопоиску — возвращает список школ."""
    lat, lon = coords
    params = {
        "apikey": api_key,
        "text": f"{query} {city}",
        "lang": "ru_RU",
        "ll": f"{lon},{lat}",
        "spn": "0.5,0.5",       # радиус поиска ~50 км
        "type": "biz",
        "results": 50,
    }
    try:
        resp = requests.get(YANDEX_SEARCH_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        log.warning(f"Яндекс API ошибка ({city}): {e}")
        return []
    except ValueError:
        log.warning(f"Яндекс API: не удалось разобрать JSON для {city}")
        return []

    schools = []
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        name = props.get("name", "")
        if not name:
            continue

        # Фильтруем — берём только те, что похожи на автошколу
        name_lower = name.lower()
        desc_lower = props.get("description", "").lower()
        combined = name_lower + " " + desc_lower
        if not any(kw in combined for kw in ["автошкол", "вождени", "автокурс", "досааф"]):
            continue

        # Координаты
        geo = feature.get("geometry", {}).get("coordinates", [None, None])

        # Адрес
        address = props.get("description", "")

        # Телефоны
        phones = []
        for contact in props.get("CompanyMetaData", {}).get("Phones", []):
            ph = contact.get("formatted", "")
            if ph:
                phones.append(ph)
        phone = ", ".join(phones)

        # Сайт
        website = ""
        for url in props.get("CompanyMetaData", {}).get("Links", []):
            href = url.get("href", "")
            if href:
                website = href
                break

        # Юридическое название — Яндекс иногда возвращает в поле CompanyMetaData
        legal_name = ""
        meta = props.get("CompanyMetaData", {})
        # Пробуем разные поля где может быть юр. лицо
        for field_name in ("LegalName", "legal_name", "FullName"):
            if meta.get(field_name):
                legal_name = meta[field_name]
                break
        # Если не нашли — пытаемся вытащить ООО/ИП из description или name
        if not legal_name:
            legal_name = _extract_legal_name(name + " " + props.get("description", ""))

        # Ссылка: предпочитаем сайт школы, иначе Яндекс.Карты
        maps_url = ""
        company_id = meta.get("id", "")
        if company_id:
            maps_url = f"https://yandex.ru/maps/org/{company_id}"
        source_link = website or maps_url or f"https://yandex.ru/maps/?text={requests.utils.quote(name+' '+city)}"

        # Категории — пытаемся определить по описанию
        cats = _detect_categories(name + " " + props.get("description", ""))

        schools.append(School(
            name=name,
            city=city,
            address=address,
            phone=phone,
            categories=cats if cats else ["C"],
            legal_name=legal_name,
            price="",
            rating="",
            reviews="",
            source_url=source_link,
            source="yandex",
        ))

    log.info(f"  Яндекс: {city} / «{query}» → {len(schools)} результатов")
    return schools


def _extract_legal_name(text: str) -> str:
    """Пытается вытащить юридическое название (ООО, ИП, АНО и т.п.) из текста."""
    import re
    patterns = [
        r'(ООО\s+[«"]?[\w\s\-]+[»"]?)',
        r'(ИП\s+[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?)',
        r'(АНО\s+[«"]?[\w\s\-]+[»"]?)',
        r'(НОУ\s+[«"]?[\w\s\-]+[»"]?)',
        r'(ЧОУДО\s+[«"]?[\w\s\-]+[»"]?)',
        r'(ДОСААФ\s+[А-ЯЁа-яё\s]+)',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return ""


def _detect_categories(text: str) -> list[str]:
    """Пытается определить категории по тексту описания."""
    text = text.upper()
    cats = []
    # Порядок важен: C1E перед CE перед C1 перед C
    if "C1E" in text or "С1Е" in text:
        cats.append("C1E")
    if "CE" in text or "СЕ" in text:
        if "CE" not in cats:
            cats.append("CE")
    if "C1" in text or "С1" in text:
        if "C1" not in cats:
            cats.append("C1")
    if any(x in text for x in ["КАТ. C", "КАТ.C", "КАТЕГОРИ C", "КАТЕГОРИЮ C",
                                 "КАТЕГОРИЯ C", " C,", " C ", "(C)"]):
        if "C" not in cats:
            cats.append("C")
    # Если ничего не нашли, но явно про грузовые
    if not cats and any(x in text for x in ["ГРУЗОВ", "ГРУЗОВИК", "ТЯГАЧ"]):
        cats.append("C")
    return cats


def scrape_all_yandex(cities: dict = None) -> list[School]:
    """
    Собирает автошколы по всем городам через Яндекс Геопоиск.
    cities — словарь {название: (lat, lon)}, по умолчанию CITY_COORDS.
    """
    try:
        api_key = get_api_key()
    except EnvironmentError as e:
        log.error(str(e))
        return []

    cities = cities or CITY_COORDS
    all_schools: dict[str, School] = {}
    total = len(cities) * len(SEARCH_QUERIES)
    done = 0

    for city, coords in cities.items():
        for query in SEARCH_QUERIES:
            done += 1
            log.info(f"[{done}/{total}] Яндекс: {city} / «{query}»")
            found = search_schools_in_city(city, coords, query, api_key)

            for school in found:
                key = school.dedup_key
                if key in all_schools:
                    existing = all_schools[key]
                    for c in school.categories:
                        if c not in existing.categories:
                            existing.categories.append(c)
                    if not existing.phone and school.phone:
                        existing.phone = school.phone
                    if not existing.address and school.address:
                        existing.address = school.address
                else:
                    all_schools[key] = school

            time.sleep(0.5)  # не превышаем лимит 500 запросов/день

    result = list(all_schools.values())
    log.info(f"Яндекс: итого {len(result)} уникальных школ")
    return result
