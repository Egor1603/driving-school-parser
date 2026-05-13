"""
Парсер официального реестра автошкол ГИБДД (гибдд.рф/drivingschools).

ГИБДД публикует список школ с заключениями. Сайт рендерится через JS,
поэтому используем requests + парсинг JSON из встроенного скрипта,
либо fallback на HTML-таблицу.
"""

import re
import time
import logging
import requests
from bs4 import BeautifulSoup
from typing import Optional
from src.parser_avtoshkoli import School, HEADERS

log = logging.getLogger(__name__)

# Коды регионов РФ (01–92, без нулей там, где их нет)
REGION_CODES = list(range(1, 93))

GIBDD_BASE = "https://xn--90adear.xn--p1ai"  # гибдд.рф в punycode

# Категории, которые нас интересуют
TARGET_CATS = {"c", "c1", "ce", "c1e"}


def fetch_region(region_code: int) -> list[School]:
    """Пытается получить список автошкол региона через HTML."""
    url = f"{GIBDD_BASE}/r/{region_code}/drivingschools"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
    except requests.RequestException as e:
        log.warning(f"Регион {region_code}: {e}")
        return []

    if resp.status_code != 200:
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    return _parse_gibdd_page(soup, url)


def _parse_gibdd_page(soup: BeautifulSoup, source_url: str) -> list[School]:
    schools = []

    # ГИБДД рендерит таблицу или список — ищем строки с данными
    rows = soup.select("tr.school-row, tr[data-id], .school-list-item")
    if not rows:
        # Fallback: любые <tr> в таблицах
        rows = soup.select("table tr")[1:]  # пропускаем header

    for row in rows:
        cells = row.find_all(["td", "th"])
        if len(cells) < 3:
            continue

        texts = [c.get_text(strip=True) for c in cells]

        # Пытаемся найти категории в строке
        full_text = " ".join(texts).lower()
        cats_found = []
        for cat in TARGET_CATS:
            pattern = rf"\b{re.escape(cat)}\b"
            if re.search(pattern, full_text):
                cats_found.append(cat.upper())

        if not cats_found:
            continue

        name = texts[0] if texts else ""
        city = texts[1] if len(texts) > 1 else ""
        address = texts[2] if len(texts) > 2 else ""
        phone = texts[3] if len(texts) > 3 else ""

        if not name:
            continue

        schools.append(School(
            name=name,
            city=city,
            address=address,
            phone=phone,
            categories=cats_found,
            source_url=source_url,
            source="гибдд.рф",
        ))

    return schools


def scrape_all_regions() -> list[School]:
    """Собирает школы категории C+ по всем регионам."""
    all_schools: dict[str, School] = {}

    for code in REGION_CODES:
        log.info(f"ГИБДД: регион {code}")
        found = fetch_region(code)

        for school in found:
            key = school.dedup_key
            if key in all_schools:
                existing = all_schools[key]
                for c in school.categories:
                    if c not in existing.categories:
                        existing.categories.append(c)
            else:
                all_schools[key] = school

        time.sleep(1.0)

    log.info(f"ГИБДД: итого {len(all_schools)} уникальных школ с категорией C+")
    return list(all_schools.values())
