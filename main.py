#!/usr/bin/env python3
"""
Парсер автошкол РФ (категория C+).

Использование:
    python main.py                        # полный прогон всех источников
    python main.py --source yandex        # только Яндекс
    python main.py --source 2gis          # только 2GIS
    python main.py --source yandex,2gis   # Яндекс + 2GIS
    python main.py --source seed          # только seed-данные
    python main.py --dry-run              # тест: seed + 5 городов
    python main.py --build-site           # пересобрать docs/index.html

Переменные окружения:
    YANDEX_API_KEY   — ключ Яндекс Геопоиска (https://developer.tech.yandex.ru/)
    TWOGIS_API_KEY   — ключ 2GIS (https://dev.2gis.ru/)
    HTTP_PROXY       — прокси для avtoshkoli.ru
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.parser_avtoshkoli import scrape_all as scrape_avtoshkoli, CITIES
from src.parser_gibdd import scrape_all_regions as scrape_gibdd
from src.parser_yandex import scrape_all_yandex, CITY_COORDS
from src.parser_2gis import scrape_all_2gis
from src.seed_data import load_seed
from src.exporter import merge_and_deduplicate, export_csv, export_json, print_stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

SITE_TEMPLATE = Path("site/index_template.html")
SITE_OUTPUT   = Path("docs/index.html")


def build_site(schools_json: Path, output: Path) -> None:
    template = SITE_TEMPLATE.read_text(encoding="utf-8")
    data = json.loads(schools_json.read_text(encoding="utf-8"))
    aggregators = ["avtoshkoli.ru", "gibdd", "radarrr.ru", "yandex.ru/maps"]
    for s in data:
        url = s.get("source_url", "")
        s["website"] = url if url and not any(a in url for a in aggregators) else ""
    js_data = json.dumps(data, ensure_ascii=False, indent=2)
    html = template.replace("__DATA_PLACEHOLDER__", js_data)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    log.info(f"Сайт собран: {output} ({len(data)} школ)")


def main():
    parser = argparse.ArgumentParser(description="Парсер автошкол РФ (категория C+)")
    parser.add_argument("--source",
        default="all",
        help="Источники через запятую: avtoshkoli,gibdd,yandex,2gis,seed,all")
    parser.add_argument("--cities", nargs="+", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--build-site", action="store_true")
    args = parser.parse_args()

    sources = [s.strip() for s in args.source.split(",")]
    use_all = "all" in sources

    output_dir = Path(args.output_dir)
    all_results = []

    # 0. Seed
    log.info("=== Источник 0: seed-данные ===")
    all_results.append(load_seed())

    # 1. avtoshkoli.ru
    if (use_all or "avtoshkoli" in sources) and not args.dry_run:
        log.info("=== Источник 1: avtoshkoli.ru ===")
        results = scrape_avtoshkoli(cities=args.cities or CITIES)
        log.info(f"avtoshkoli.ru: {len(results)} записей")
        all_results.append(results)

    # 2. гибдд.рф
    if (use_all or "gibdd" in sources) and not args.dry_run:
        log.info("=== Источник 2: гибдд.рф ===")
        results = scrape_gibdd()
        log.info(f"гибдд.рф: {len(results)} записей")
        all_results.append(results)

    # 3. Яндекс
    if use_all or "yandex" in sources:
        if not os.environ.get("YANDEX_API_KEY"):
            log.warning("YANDEX_API_KEY не задан — пропускаем Яндекс.")
        else:
            log.info("=== Источник 3: Яндекс Геопоиск ===")
            cities_dict = CITY_COORDS
            if args.dry_run:
                test = ["Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург", "Казань"]
                cities_dict = {k: v for k, v in CITY_COORDS.items() if k in test}
            results = scrape_all_yandex(cities=cities_dict)
            log.info(f"Яндекс: {len(results)} записей")
            all_results.append(results)

    # 4. 2GIS
    if use_all or "2gis" in sources:
        log.info("=== Источник 4: 2GIS ===")
        cities_list = list(CITY_COORDS.keys())
        if args.dry_run:
            cities_list = cities_list[:5]
        results = scrape_all_2gis(cities=cities_list)
        log.info(f"2GIS: {len(results)} записей")
        all_results.append(results)

    schools = merge_and_deduplicate(all_results)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "driving_schools_cat_c.json"
    export_csv(schools, output_dir / "driving_schools_cat_c.csv")
    export_json(schools, json_path)
    print_stats(schools)

    if args.build_site:
        if SITE_TEMPLATE.exists():
            build_site(json_path, SITE_OUTPUT)
        else:
            log.warning(f"Шаблон {SITE_TEMPLATE} не найден.")

    log.info("Готово!")


if __name__ == "__main__":
    main()
