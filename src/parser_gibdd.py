"""
Парсер официального реестра автошкол ГИБДД (гибдд.рф/drivingschools).

Использует Selenium + headless Chrome — имитирует настоящий браузер,
поэтому обходит блокировку которая срабатывает на обычные HTTP-запросы.

Сайт ГИБДД рендерит таблицу через JavaScript, поэтому requests не работает —
нужен браузер который выполнит JS и покажет итоговый HTML.
"""

import re
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup
from src.parser_avtoshkoli import School

log = logging.getLogger(__name__)

GIBDD_BASE = "https://xn--90adear.xn--p1ai"  # гибдд.рф в punycode
REGION_CODES = list(range(1, 93))
TARGET_CATS = {"c", "c1", "ce", "c1e"}


def make_driver() -> webdriver.Chrome:
    """Создаём headless Chrome — невидимый браузер."""
    import os

    opts = Options()
    opts.add_argument("--headless")           # без окна
    opts.add_argument("--no-sandbox")         # нужно для GitHub Actions
    opts.add_argument("--disable-dev-shm-usage")  # нужно для GitHub Actions
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--lang=ru-RU")
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)

    # Путь к Chrome — берём из переменной окружения или ищем автоматически
    chrome_bin = os.environ.get("CHROME_BIN")
    if chrome_bin:
        opts.binary_location = chrome_bin

    # Путь к chromedriver
    chromedriver = os.environ.get("CHROMEDRIVER_PATH")
    service = Service(chromedriver) if chromedriver else Service()

    driver = webdriver.Chrome(service=service, options=opts)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


def fetch_region(driver: webdriver.Chrome, region_code: int) -> list[School]:
    """Загружает страницу автошкол региона и парсит таблицу."""
    url = f"{GIBDD_BASE}/r/{region_code}/drivingschools"
    schools = []

    try:
        driver.get(url)

        # Ждём появления таблицы или списка — максимум 15 секунд
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR,
                    "table, .school-item, .driving-school, [class*='school']"))
            )
        except TimeoutException:
            log.warning(f"Регион {region_code}: таблица не появилась за 15 сек")
            return []

        # Дополнительная пауза чтобы JS дозагрузил данные
        time.sleep(2)

        # Парсим итоговый HTML через BeautifulSoup
        soup = BeautifulSoup(driver.page_source, "lxml")
        schools = _parse_page(soup, url)
        log.info(f"  Регион {region_code}: {len(schools)} школ с кат. C+")

    except WebDriverException as e:
        log.warning(f"Регион {region_code}: ошибка браузера — {e}")

    return schools


def _parse_page(soup: BeautifulSoup, source_url: str) -> list[School]:
    """Разбирает HTML страницы и извлекает автошколы с категорией C+."""
    schools = []

    # Ищем строки таблицы
    rows = soup.select("tr")
    for row in rows:
        cells = row.find_all(["td", "th"])
        if len(cells) < 2:
            continue

        texts = [c.get_text(" ", strip=True) for c in cells]
        full_text = " ".join(texts).lower()

        # Фильтр по категориям C, C1, CE, C1E
        cats_found = []
        for cat in ["c1e", "c1", "ce", "c"]:  # порядок важен!
            pattern = rf"\b{re.escape(cat)}\b"
            if re.search(pattern, full_text):
                if cat.upper() not in cats_found:
                    cats_found.append(cat.upper())

        if not cats_found:
            continue

        name     = texts[0] if len(texts) > 0 else ""
        address  = texts[1] if len(texts) > 1 else ""
        phone    = _find_phone(full_text)

        # Пробуем вытащить юр. название (ООО, ИП и т.п.)
        legal    = _extract_legal(name)

        if not name or len(name) < 3:
            continue

        schools.append(School(
            name=name,
            city=_extract_city(address),
            address=address,
            phone=phone,
            categories=cats_found,
            legal_name=legal,
            source_url=source_url,
            source="gibdd",
        ))

    # Fallback: блоки div если таблицы нет
    if not schools:
        blocks = soup.select(
            ".school-item, .driving-school, [class*='school-list'] > div"
        )
        for block in blocks:
            text = block.get_text(" ", strip=True)
            text_lower = text.lower()

            cats_found = []
            for cat in ["c1e", "c1", "ce", "c"]:
                if re.search(rf"\b{re.escape(cat)}\b", text_lower):
                    if cat.upper() not in cats_found:
                        cats_found.append(cat.upper())

            if not cats_found:
                continue

            name_el = block.select_one("h2, h3, .name, .title, strong, b")
            name = name_el.get_text(strip=True) if name_el else text[:80]

            schools.append(School(
                name=name,
                city="",
                address=text[:200],
                phone=_find_phone(text),
                categories=cats_found,
                legal_name=_extract_legal(name),
                source_url=source_url,
                source="gibdd",
            ))

    return schools


def _find_phone(text: str) -> str:
    """Ищет номер телефона в тексте."""
    m = re.search(r"(\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}", text)
    return m.group(0).strip() if m else ""


def _extract_city(address: str) -> str:
    """Пытается вытащить город из адресной строки."""
    # Ищем «г. Москва» или «Москва,»
    m = re.search(r"г\.?\s*([А-ЯЁа-яё\-]+)", address)
    return m.group(1).strip() if m else ""


def _extract_legal(text: str) -> str:
    """Вытаскивает юридическое название (ООО, ИП, АНО и т.п.)"""
    patterns = [
        r"(ООО\s+«?[\w\s\-]+»?)",
        r"(ИП\s+[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?)",
        r"(АНО\s+(?:ДПО\s+)?«?[\w\s\-]+»?)",
        r"(НОУ\s+«?[\w\s\-]+»?)",
        r"(ЧОУДО?\s+«?[\w\s\-]+»?)",
        r"(ДОСААФ\s+[А-ЯЁа-яё\s]+)",
        r"(ГБПОУ\s+[\w\s\-]+)",
        r"(ФГБОУ\s+[\w\s\-]+)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()[:100]
    return ""


def scrape_all_regions(region_codes: list[int] = None) -> list[School]:
    """
    Собирает автошколы с категорией C+ по всем регионам через Selenium.
    """
    codes = region_codes or REGION_CODES
    all_schools: dict[str, School] = {}

    log.info("Запускаем headless Chrome...")
    try:
        driver = make_driver()
    except Exception as e:
        log.error(f"Не удалось запустить браузер: {e}")
        log.error("Убедитесь что Chrome установлен: apt-get install -y chromium-browser")
        return []

    try:
        for i, code in enumerate(codes, 1):
            log.info(f"[{i}/{len(codes)}] ГИБДД: регион {code}")
            found = fetch_region(driver, code)

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

            # Пауза между регионами — вежливо и снижает риск блокировки
            time.sleep(1.5)

    finally:
        driver.quit()
        log.info("Браузер закрыт")

    result = list(all_schools.values())
    log.info(f"ГИБДД (Selenium): итого {len(result)} уникальных школ с категорией C+")
    return result
