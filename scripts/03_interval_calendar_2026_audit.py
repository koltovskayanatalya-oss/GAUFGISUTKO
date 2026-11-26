# -*- coding: utf-8 -*-
"""Календарный аудит интервальных графиков. Гипотеза n активных дней + m дней перерыва."""
from datetime import datetime, date, timedelta
from qgis.core import QgsProject, QgsFeatureRequest

LAYER_NAME = "Слияние_all"
SCHEDULE_VALUE = "Каждые n через m дней"
YEAR_START, YEAR_END = date(2026, 1, 1), date(2026, 12, 31)
FIELDS = ["_Вид графика вывоза отходов", "_Каждые n дней", "_Через m дней",
          "_Дата начала вывоза отходов", "_Дата начала периода",
          "_Дата окончания периода", "_Итоговое количество вывозов",
          "_Тип контейнера (бункера)", "Муниципальное образование", "Населенный пункт"]

def txt(v):
    return "" if v is None else str(v).strip()

def integer(v):
    try:
        return int(float(txt(v).replace(",", ".")))
    except Exception:
        return None

def parse_date(v):
    if v is None:
        return None
    if hasattr(v, "toPyDate"):
        try: return v.toPyDate()
        except Exception: pass
    if isinstance(v, date): return v
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y"):
        try: return datetime.strptime(txt(v), fmt).date()
        except Exception: pass
    return None

def count_cycle(first, n, m, lower, upper):
    cycle = n + m
    if n <= 0 or m < 0 or cycle <= 0:
        return None
    count, day = 0, lower
    while day <= upper:
        offset = (day - first).days
        if offset >= 0 and offset % cycle < n:
            count += 1
        day += timedelta(days=1)
    return count

layers = QgsProject.instance().mapLayersByName(LAYER_NAME)
if not layers: raise Exception("Слой '{}' не найден.".format(LAYER_NAME))
layer = layers[0]
missing = [x for x in FIELDS if layer.fields().indexFromName(x) < 0]
if missing: raise Exception("Не найдены поля: {}".format(", ".join(missing)))
req = QgsFeatureRequest()
req.setSubsetOfAttributes(FIELDS, layer.fields())
req.setFlags(QgsFeatureRequest.NoGeometry)

print("\n" + "=" * 100)
print("ИНТЕРВАЛЬНЫЕ ГРАФИКИ — КАЛЕНДАРНЫЙ АУДИТ 2026")
print("Гипотеза: n дней вывоза подряд, затем m дней перерыва; цикл n+m.")
print("=" * 100)
processed = 0
for f in layer.getFeatures(req):
    if txt(f["_Вид графика вывоза отходов"]) != SCHEDULE_VALUE:
        continue
    processed += 1
    n, m = integer(f["_Каждые n дней"]), integer(f["_Через m дней"])
    first = parse_date(f["_Дата начала вывоза отходов"])
    pstart, pend = parse_date(f["_Дата начала периода"]), parse_date(f["_Дата окончания периода"])
    stored = integer(f["_Итоговое количество вывозов"])
    print("\nFID:", f.id(), "| поток:", txt(f["_Тип контейнера (бункера)"]),
          "| МО:", txt(f["Муниципальное образование"]), "| НП:", txt(f["Населенный пункт"]))
    print("n={}, m={}, первый вывоз={}, период={}..{}, частота в поле={}".format(n, m, first, pstart, pend, stored))
    if None in (n, m, first, pstart, pend) or pend < pstart:
        print("СТАТУС: недостаточно/некорректно заполнены параметры.")
        continue
    lo, hi = max(YEAR_START, pstart), min(YEAR_END, pend)
    if lo > hi or first > hi:
        calculated = 0
    else:
        calculated = count_cycle(first, n, m, lo, hi)
    print("Календарное число вывозов по гипотезе:", calculated)
    print("Разница (календарное - поле):", None if stored is None else calculated - stored)
    print("Это проверка гипотезы, а не подтверждение первичным фактом.")
print("\nОбработано интервальных строк:", processed)
print("ДАННЫЕ НЕ ИЗМЕНЯЛИСЬ.")
