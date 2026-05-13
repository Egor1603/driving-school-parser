"""
Дедупликация и экспорт результатов в CSV + JSON.
"""

import csv
import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Sequence
from src.parser_avtoshkoli import School

log = logging.getLogger(__name__)


def merge_and_deduplicate(school_lists: list[list[School]]) -> list[School]:
    """
    Объединяет несколько списков школ (из разных источников),
    удаляет дубли по ключу (город + нормализованное имя),
    мёрджит категории и телефоны.
    """
    merged: dict[str, School] = {}

    for schools in school_lists:
        for school in schools:
            key = school.dedup_key
            if key not in merged:
                merged[key] = school
            else:
                existing = merged[key]
                # Объединяем категории
                for cat in school.categories:
                    if cat not in existing.categories:
                        existing.categories.append(cat)
                # Заполняем пустые поля из дублей
                if not existing.address and school.address:
                    existing.address = school.address
                if not existing.phone and school.phone:
                    existing.phone = school.phone
                if not existing.rating and school.rating:
                    existing.rating = school.rating
                if not existing.price and school.price:
                    existing.price = school.price

    result = sorted(merged.values(), key=lambda s: (s.city, s.name))
    log.info(f"После дедупликации: {len(result)} уникальных школ")
    return result


def export_csv(schools: Sequence[School], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "name", "city", "address", "phone",
        "categories", "price", "rating", "reviews",
        "source", "source_url",
    ]

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for school in schools:
            row = asdict(school)
            row["categories"] = ", ".join(school.categories)
            writer.writerow({k: row[k] for k in fieldnames})

    log.info(f"CSV сохранён: {path} ({len(schools)} строк)")


def export_json(schools: Sequence[School], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = []
    for school in schools:
        row = asdict(school)
        data.append(row)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    log.info(f"JSON сохранён: {path} ({len(schools)} записей)")


def print_stats(schools: Sequence[School]) -> None:
    from collections import Counter

    cities = Counter(s.city for s in schools)
    cats: Counter = Counter()
    for s in schools:
        for c in s.categories:
            cats[c] += 1

    print(f"\n{'='*50}")
    print(f"  Всего школ: {len(schools)}")
    print(f"  Городов: {len(cities)}")
    print(f"\n  Топ-15 городов по количеству школ:")
    for city, count in cities.most_common(15):
        print(f"    {city:<30} {count}")
    print(f"\n  Распределение по категориям:")
    for cat, count in cats.most_common():
        print(f"    Категория {cat:<6} {count}")
    print(f"{'='*50}\n")
