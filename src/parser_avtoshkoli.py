"""
Парсер avtoshkoli.ru — автошколы с категориями C, C1, CE, C1E по всей России.
"""

import os
import re
import time
import logging
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, field, asdict
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

BASE_URL = "https://avtoshkoli.ru"

CATEGORIES = [
    "obuchenie-na-kategoriyu-c",
    "obuchenie-na-kategoriyu-ce",
]

# Слаги городов на avtoshkoli.ru (все крупные + средние города РФ)
CITIES = [
    "moskva", "sankt-peterburg", "novosibirsk", "ekaterinburg", "kazan",
    "nizhniy-novgorod", "chelyabinsk", "omsk", "samara", "rostov-na-donu",
    "ufa", "krasnoyarsk", "voronezh", "perm", "volgograd", "krasnodar",
    "saratov", "tyumen", "tolyatti", "izhevsk", "barnaul", "ulyanovsk",
    "irkutsk", "habarovsk", "yaroslavl", "vladivostok", "makhachkala",
    "tomsk", "orenburg", "kemerovo", "novokuznetsk", "ryazan", "astrakhan",
    "naberezhnye-chelny", "penza", "lipetsk", "tula", "kirov", "cheboksary",
    "kaliningrad", "bryansk", "kursk", "ivanovo", "magnitogorsk", "tver",
    "stavropol", "belgorod", "sochi", "nizhny-tagil", "arkhangelsk",
    "vladimir", "chita", "yakutsk", "smolensk", "murmansk", "surgut",
    "kostroma", "vologda", "novorossiysk", "taganrog", "yoshkar-ola",
    "saransk", "ulan-ude", "pskov", "tambov", "balashikha", "mytishchi",
    "khimki", "orel", "kaluga", "kurgan", "abakan", "maykop", "elista",
    "petrozavodsk", "syktyvkar", "naltchik", "vladikavkaz", "grozny",
    "noginsk", "serpukhov", "podolsk", "korolev", "lyubertsy", "odintsovo",
]

# Полный набор заголовков, имитирующих браузер
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.google.ru/",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "cross-site",
    "Cache-Control": "max-age=0",
}

# Прокси из переменной окружения (опционально)
# Формат: HTTP_PROXY=http://user:pass@host:port
PROXIES = {}
if os.environ.get("HTTP_PROXY"):
    PROXIES = {"http": os.environ["HTTP_PROXY"], "https": os.environ["HTTP_PROXY"]}

# Сессия переиспользуется между запросами (хранит cookies)
_session: Optional[requests.Session] = None


def get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update(HEADERS)
        if PROXIES:
            _session.proxies.update(PROXIES)
        # Прогреваем сессию — получаем главную страницу для cookies
        try:
            _session.get(BASE_URL, timeout=10)
            time.sleep(1)
        except Exception:
            pass
    return _session


@dataclass
class School:
    name: str
    city: str
    address: str
    phone: str
    categories: list[str] = field(default_factory=list)
    legal_name: str = ""   # Юридическое название (ООО, ИП и т.п.)
    price: str = ""
    rating: str = ""
    reviews: str = ""
    source_url: str = ""
    source: str = "avtoshkoli.ru"

    @property
    def dedup_key(self) -> str:
        """Ключ для дедупликации: нормализованное имя + город."""
        name_norm = re.sub(r"\s+", " ", self.name.lower().strip())
        city_norm = self.city.lower().strip()
        return f"{city_norm}|{name_norm}"


def fetch(url: str, retries: int = 3, delay: float = 2.0) -> Optional[BeautifulSoup]:
    session = get_session()
    for attempt in range(retries):
        try:
            resp = session.get(url, timeout=15)
            if resp.status_code == 200:
                return BeautifulSoup(resp.text, "lxml")
            elif resp.status_code == 404:
                return None
            elif resp.status_code == 403:
                log.warning(f"403 Forbidden (попытка {attempt+1}/{retries}) → {url}")
                log.info("  Совет: запустите с переменной HTTP_PROXY для обхода блокировки")
            else:
                log.warning(f"HTTP {resp.status_code} → {url}")
        except requests.RequestException as e:
            log.warning(f"Попытка {attempt+1}/{retries} упала: {e}")
        time.sleep(delay * (attempt + 1))
    return None


def parse_city_category(city_slug: str, category_slug: str) -> list[School]:
    url = f"{BASE_URL}/{city_slug}/{category_slug}/"
    soup = fetch(url)
    if soup is None:
        return []

    # Определяем человекочитаемое название города из <title> или <h1>
    h1 = soup.find("h1")
    city_name = city_slug.replace("-", " ").title()
    if h1:
        # «Обучение на категорию «C» в автошколах Москвы» → берём последнее слово
        match = re.search(r"в автошколах\s+(.+?)$", h1.get_text(), re.I)
        if match:
            city_name = match.group(1).strip()

    # Определяем категорию из слага
    cat_label = _slug_to_category(category_slug)

    schools: list[School] = []
    cards = soup.select("div.school-item, article.school-card, div[class*='school']")

    # Fallback: ищем по структуре — блоки с именем и адресом
    if not cards:
        cards = soup.select("div.item, li.school, div.school-block")

    for card in cards:
        name = _text(card, [
            "a.school-name", ".name a", "h2 a", "h3 a",
            ".school-title", "a[href*='/school/']",
        ])
        if not name:
            continue

        address = _text(card, [".address", ".addr", "[class*='address']"])
        phone = _text(card, [".phone", ".tel", "[class*='phone']", "a[href^='tel:']"])
        price = _text(card, [".price", "[class*='price']", ".cost"])
        rating_el = card.select_one("[class*='rating'], .stars, .rate")
        rating = rating_el.get_text(strip=True) if rating_el else ""
        reviews_el = card.select_one("[class*='review'], .reviews-count")
        reviews = reviews_el.get_text(strip=True) if reviews_el else ""

        schools.append(School(
            name=name,
            city=city_name,
            address=address,
            phone=phone,
            categories=[cat_label],
            price=price,
            rating=rating,
            reviews=reviews,
            source_url=url,
        ))

    log.info(f"  {city_slug}/{category_slug}: {len(schools)} школ")
    return schools


def _slug_to_category(slug: str) -> str:
    mapping = {
        "obuchenie-na-kategoriyu-c": "C",
        "obuchenie-na-kategoriyu-ce": "CE",
        "pereподготовка-b-c": "B→C",
        "obuchenie-na-kategoriyu-c1": "C1",
        "obuchenie-na-kategoriyu-c1e": "C1E",
    }
    return mapping.get(slug, slug)


def _text(tag, selectors: list[str]) -> str:
    for sel in selectors:
        el = tag.select_one(sel)
        if el:
            return el.get_text(strip=True)
    return ""


def scrape_all(cities: list[str] = None, categories: list[str] = None) -> list[School]:
    cities = cities or CITIES
    categories = categories or ["obuchenie-na-kategoriyu-c", "obuchenie-na-kategoriyu-ce"]

    all_schools: dict[str, School] = {}  # dedup_key → School

    total = len(cities) * len(categories)
    done = 0

    for city in cities:
        for cat in categories:
            done += 1
            log.info(f"[{done}/{total}] Парсим {city} / {cat}")
            found = parse_city_category(city, cat)

            for school in found:
                key = school.dedup_key
                if key in all_schools:
                    # Добавляем категорию, если ещё нет
                    existing = all_schools[key]
                    for c in school.categories:
                        if c not in existing.categories:
                            existing.categories.append(c)
                else:
                    all_schools[key] = school

            time.sleep(0.8)  # вежливая пауза между запросами

    return list(all_schools.values())
