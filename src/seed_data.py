"""
Резервный источник: seed-данные, собранные вручную / из поисковой выдачи.
Используется когда основной сайт недоступен (403, Cloudflare и т.п.).

Для пополнения: добавьте новые школы в список SEED_SCHOOLS ниже,
либо положите файл data/seed.json с тем же форматом.
"""

import json
import logging
from pathlib import Path
from src.parser_avtoshkoli import School

log = logging.getLogger(__name__)

SEED_SCHOOLS = [
    # Москва
    {"name": "ДОСААФ (Алгоритм)", "city": "Москва", "address": "Измайловский проезд, 11, стр. 2", "phone": "", "categories": ["C", "CE"], "price": "", "rating": "", "reviews": "", "source": "seed", "source_url": "https://www.umc-algoritm.ru/"},
    {"name": "Центральная автошкола Москвы", "city": "Москва", "address": "Москва (58 учебных классов)", "phone": "+7 (495) 122-00-15", "categories": ["C", "C1", "CE"], "price": "", "rating": "", "reviews": "", "source": "seed", "source_url": "https://www.autoprava.ru/"},
    {"name": "Magic Drive", "city": "Москва", "address": "Москва", "phone": "", "categories": ["C", "C1"], "price": "от 14 000 руб.", "rating": "", "reviews": "", "source": "seed", "source_url": "https://magic-drive.ru/"},
    {"name": "Мегаполис", "city": "Москва", "address": "Москва", "phone": "", "categories": ["C", "CE"], "price": "", "rating": "", "reviews": "", "source": "seed", "source_url": "https://megapolis-car.ru/"},
    {"name": "Аргос", "city": "Москва", "address": "ул. Красноярская, д. 3 к.1", "phone": "", "categories": ["C", "CE"], "price": "", "rating": "", "reviews": "", "source": "seed", "source_url": "https://argoc.ru/"},
    {"name": "Светофор", "city": "Москва", "address": "Москва", "phone": "", "categories": ["CE"], "price": "", "rating": "", "reviews": "", "source": "seed", "source_url": "https://svetofor.ru/"},
    {"name": "iDriver", "city": "Балашиха", "address": "Балашиха / Железнодорожный", "phone": "", "categories": ["C"], "price": "50 000 руб.", "rating": "", "reviews": "", "source": "seed", "source_url": "https://idriver.ru/"},
    {"name": "Фортуна-Авто", "city": "Москва", "address": "Москва", "phone": "", "categories": ["C"], "price": "", "rating": "", "reviews": "", "source": "seed", "source_url": "https://frt-avto.ru/"},
    # Санкт-Петербург
    {"name": "Авторалли", "city": "Санкт-Петербург", "address": "13 филиалов у метро", "phone": "", "categories": ["C", "C1", "CE"], "price": "", "rating": "", "reviews": "", "source": "seed", "source_url": "https://autorally-spb.ru/"},
    {"name": "Мегаполис СПб", "city": "Санкт-Петербург", "address": "56 филиалов", "phone": "", "categories": ["C", "CE"], "price": "от 21 800 руб.", "rating": "", "reviews": "", "source": "seed", "source_url": "https://megapolis-car.ru/spb/"},
    # Екатеринбург
    {"name": "Прайм-Авто", "city": "Екатеринбург", "address": "5 филиалов", "phone": "", "categories": ["C", "C1"], "price": "39 000 руб.", "rating": "", "reviews": "", "source": "seed", "source_url": "https://primeavto.ru/"},
    {"name": "Профессионал", "city": "Екатеринбург", "address": "ул. Сибирский тракт 8Д, офис 210", "phone": "+7 (902) 446-17-35", "categories": ["CE"], "price": "", "rating": "", "reviews": "", "source": "seed", "source_url": "https://profi196.ru/"},
    # Уфа
    {"name": "БашАвтоЛига", "city": "Уфа", "address": "пр. Октября, 55", "phone": "+7 (347) 225-05-81", "categories": ["C", "CE"], "price": "11 500 руб.", "rating": "5/5", "reviews": "129", "source": "seed", "source_url": "https://avtoshkoli.ru/ufa/obuchenie-na-kategoriyu-c/"},
    {"name": "ДОСААФ Уфа", "city": "Уфа", "address": "ул. Трамвайная, 17А", "phone": "", "categories": ["C"], "price": "11 900 руб.", "rating": "", "reviews": "", "source": "seed", "source_url": "https://avtoshkoli.ru/ufa/obuchenie-na-kategoriyu-c/"},
    # Уфа (автошколы по категории C из поиска)
    {"name": "Автошкола Уфа (категория C)", "city": "Уфа", "address": "Менделеева, 137; Гафури, 54", "phone": "", "categories": ["C"], "price": "от 9 900 руб.", "rating": "", "reviews": "", "source": "seed", "source_url": "https://xn----7sbahra5aeae5abgkqcrfn1i6i.xn--p1ai/"},
    # Калининград
    {"name": "АвтоДока", "city": "Калининград", "address": "Калининград", "phone": "", "categories": ["CE"], "price": "", "rating": "", "reviews": "", "source": "seed", "source_url": "https://avtodoka39.com/"},
    # Красноярск
    {"name": "Автошкола СФУ", "city": "Красноярск", "address": "ул. Борисова, 24", "phone": "+7 (391) 249-77-35", "categories": ["C"], "price": "52 000 руб.", "rating": "5/5", "reviews": "1", "source": "seed", "source_url": "https://avtoshkoli.ru/krasnoyarsk/obuchenie-na-kategoriyu-c/"},
    {"name": "Автошкола Старт", "city": "Красноярск", "address": "ул. Ладо Кецховели, 57", "phone": "+7 (391) 252-02-21", "categories": ["C"], "price": "30 000 руб.", "rating": "4/5", "reviews": "3", "source": "seed", "source_url": "https://avtoshkoli.ru/krasnoyarsk/obuchenie-na-kategoriyu-c/"},
    {"name": "АВМ", "city": "Красноярск", "address": "ул. Академика Павлова, 49А", "phone": "+7 (391) 989-79-19", "categories": ["C"], "price": "27 000 руб.", "rating": "", "reviews": "", "source": "seed", "source_url": "https://avtoshkoli.ru/krasnoyarsk/obuchenie-na-kategoriyu-c/"},
    # Пенза
    {"name": "ДОСААФ Пенза", "city": "Пенза", "address": "ул. Восточная, 7", "phone": "+7 (8412) 55-19-23", "categories": ["C"], "price": "10 300 руб.", "rating": "5/5", "reviews": "1", "source": "seed", "source_url": "https://avtoshkoli.ru/penza/obuchenie-na-kategoriyu-c/"},
    {"name": "ТВИСПО", "city": "Пенза", "address": "ул. Суворова, 120", "phone": "+7 (8412) 99-99-79", "categories": ["C"], "price": "45 000 руб.", "rating": "4/5", "reviews": "166", "source": "seed", "source_url": "https://avtoshkoli.ru/penza/obuchenie-na-kategoriyu-c/"},
    {"name": "Вираж-58", "city": "Пенза", "address": "ул. Луначарского, 51", "phone": "+7 (8412) 53-61-11", "categories": ["C"], "price": "10 000 руб.", "rating": "5/5", "reviews": "2", "source": "seed", "source_url": "https://avtoshkoli.ru/penza/obuchenie-na-kategoriyu-c/"},
    # Нижний Новгород
    {"name": "Абсолют-НН", "city": "Нижний Новгород", "address": "Нижний Новгород", "phone": "", "categories": ["C"], "price": "23 000 руб.", "rating": "", "reviews": "", "source": "seed", "source_url": "https://avtoshkoli.ru/nizhniy-novgorod/obuchenie-na-kategoriyu-c/"},
    {"name": "Виста-НН", "city": "Нижний Новгород", "address": "ул. Чаадаева, 3Б", "phone": "+7 (831) 415-32-04", "categories": ["C"], "price": "от 25 000 руб.", "rating": "", "reviews": "", "source": "seed", "source_url": "https://avtoshkoli.ru/nizhniy-novgorod/obuchenie-na-kategoriyu-c/"},
    {"name": "Авто-Профи НН", "city": "Нижний Новгород", "address": "ул. Ефремова, 6", "phone": "+7 (831) 212-82-72", "categories": ["C"], "price": "34 500 руб.", "rating": "", "reviews": "", "source": "seed", "source_url": "https://avtoshkoli.ru/nizhniy-novgorod/obuchenie-na-kategoriyu-c/"},
    # Тюмень
    {"name": "Автостатус", "city": "Тюмень", "address": "ул. Республики, 169к1", "phone": "+7 (985) 219-62-74", "categories": ["C"], "price": "21 900 руб.", "rating": "5/5", "reviews": "7", "source": "seed", "source_url": "https://avtoshkoli.ru/tyumen/obuchenie-na-kategoriyu-c/"},
    {"name": "Тюменская автошкола ВОА", "city": "Тюмень", "address": "ул. Пермякова, 44", "phone": "+7 (3452) 33-36-26", "categories": ["C"], "price": "50 000 руб.", "rating": "", "reviews": "", "source": "seed", "source_url": "https://avtoshkoli.ru/tyumen/obuchenie-na-kategoriyu-c/"},
    # Пермь
    {"name": "Неокруг", "city": "Пермь", "address": "Пермь", "phone": "", "categories": ["C"], "price": "14 000 руб.", "rating": "", "reviews": "", "source": "seed", "source_url": "https://avtoshkoli.ru/perm/obuchenie-na-kategoriyu-c/"},
    {"name": "Авто Профи Пермь", "city": "Пермь", "address": "Пермь", "phone": "", "categories": ["C"], "price": "от 14 000 руб.", "rating": "", "reviews": "", "source": "seed", "source_url": "https://avtoshkoli.ru/perm/obuchenie-na-kategoriyu-c/"},
    {"name": "Вектор Пермь", "city": "Пермь", "address": "Пермь", "phone": "", "categories": ["C"], "price": "от 5 000 руб.", "rating": "", "reviews": "", "source": "seed", "source_url": "https://avtoshkoli.ru/perm/obuchenie-na-kategoriyu-c/"},
    # Вологда
    {"name": "Пятое колесо", "city": "Вологда", "address": "Вологда", "phone": "", "categories": ["C"], "price": "30 000 руб.", "rating": "", "reviews": "", "source": "seed", "source_url": "https://avtoshkoli.ru/vologda/obuchenie-na-kategoriyu-c/"},
    # Абакан
    {"name": "ЦППК ФАУ", "city": "Абакан", "address": "ул. Маршала Жукова, 99", "phone": "+7 (3902) 27-90-47", "categories": ["C", "CE"], "price": "40 000 руб.", "rating": "", "reviews": "", "source": "seed", "source_url": "https://avtoshkoli.ru/abakan/obuchenie-na-kategoriyu-c/"},
    # Калуга
    {"name": "ДОСААФ Калуга", "city": "Калуга", "address": "Калуга", "phone": "", "categories": ["C"], "price": "47 000 руб.", "rating": "", "reviews": "", "source": "seed", "source_url": "https://avtoshkoli.ru/kaluga/obuchenie-na-kategoriyu-c/"},
    # Ногинск
    {"name": "Орлан", "city": "Ногинск", "address": "Ногинск", "phone": "", "categories": ["C"], "price": "69 000 руб.", "rating": "", "reviews": "", "source": "seed", "source_url": "https://avtoshkoli.ru/noginsk/obuchenie-na-kategoriyu-c/"},
]


def load_seed(extra_file: str = "data/seed.json") -> list[School]:
    """
    Загружает seed-данные.
    Сначала берёт встроенный список, потом дополняет из файла data/seed.json
    (если файл существует).
    """
    schools: list[School] = []

    for item in SEED_SCHOOLS:
        schools.append(School(**item))

    # Дополнительный файл
    path = Path(extra_file)
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                extra = json.load(f)
            for item in extra:
                schools.append(School(**item))
            log.info(f"Seed: загружено {len(extra)} записей из {path}")
        except Exception as e:
            log.warning(f"Не удалось загрузить {path}: {e}")

    log.info(f"Seed: итого {len(schools)} записей")
    return schools
