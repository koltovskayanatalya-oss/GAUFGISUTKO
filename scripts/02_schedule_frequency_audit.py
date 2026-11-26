# -*- coding: utf-8 -*-
"""Диагностика частоты, статусов и периодов. Правила 12/52 не применяются."""
from collections import Counter, defaultdict
from datetime import datetime, date
from qgis.core import QgsProject, QgsFeatureRequest

LAYER_NAME = "Слияние_all"
YEAR = 2026
FIELDS = ["_Тип контейнера (бункера)", "_Вид графика вывоза отходов",
          "_Итоговое количество вывозов", "_Дата начала периода",
          "_Дата окончания периода", "Муниципальное образование",
          "Населенный пункт"]
NO_PICKUP = "Вывоз не осуществляется"

def txt(v):
    return "" if v is None else str(v).strip()

def num(v):
    if v is None or txt(v) == "":
        return None
    try:
        return float(str(v).replace(",", "."))
    except Exception:
        return None

def parse_date(v):
    if v is None:
        return None
    if hasattr(v, "toPyDate"):
        try:
            return v.toPyDate()
        except Exception:
            pass
    if isinstance(v, date):
        return v
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(txt(v), fmt).date()
        except Exception:
            pass
    return None

layers = QgsProject.instance().mapLayersByName(LAYER_NAME)
if not layers:
    raise Exception("Слой '{}' не найден.".format(LAYER_NAME))
layer = layers[0]
missing = [x for x in FIELDS if layer.fields().indexFromName(x) < 0]
if missing:
    raise Exception("Не найдены поля: {}".format(", ".join(missing)))

req = QgsFeatureRequest()
req.setSubsetOfAttributes(FIELDS, layer.fields())
req.setFlags(QgsFeatureRequest.NoGeometry)

by_stream, by_schedule = defaultdict(Counter), Counter()
conflicts, bad_dates, outside, intersects = [], [], [], []
n_null = n_zero = n_neg = n_frac = n_over52 = 0
year_start, year_end = date(YEAR, 1, 1), date(YEAR, 12, 31)
total = 0

for f in layer.getFeatures(req):
    total += 1
    stream = txt(f["_Тип контейнера (бункера)"]) or "<ПУСТО>"
    schedule = txt(f["_Вид графика вывоза отходов"]) or "<ПУСТО>"
    freq = num(f["_Итоговое количество вывозов"])
    by_schedule[schedule] += 1
    c = by_stream[stream]
    c["rows"] += 1
    if freq is None:
        n_null += 1; c["freq_null"] += 1
    else:
        if freq == 0: n_zero += 1; c["freq_zero"] += 1
        if freq < 0: n_neg += 1; c["freq_negative"] += 1
        if abs(freq - round(freq)) > 1e-9: n_frac += 1; c["freq_fractional"] += 1
        if freq > 52: n_over52 += 1; c["freq_over52"] += 1
    if schedule == NO_PICKUP and freq not in (None, 0):
        conflicts.append((f.id(), freq, txt(f["Муниципальное образование"]), txt(f["Населенный пункт"])))
    if schedule != NO_PICKUP and freq == 0:
        c["zero_other_status"] += 1
    start, end = parse_date(f["_Дата начала периода"]), parse_date(f["_Дата окончания периода"])
    if start is None or end is None or end < start:
        bad_dates.append((f.id(), txt(f["_Дата начала периода"]), txt(f["_Дата окончания периода"])))
    elif end < year_start or start > year_end:
        outside.append((f.id(), start.isoformat(), end.isoformat()))
    else:
        intersects.append(f.id())

print("\n" + "=" * 76)
print("АУДИТ ЧАСТОТ И ПЕРИОДОВ — ТОЛЬКО ЧТЕНИЕ")
print("=" * 76)
print("Строк:", total)
print("Частота: пропуски={}, ноль={}, отрицательные={}, дробные={}, >52={}".format(n_null, n_zero, n_neg, n_frac, n_over52))
print("Периоды: пересекают {} год={}, вне года={}, некорректные={}".format(YEAR, len(intersects), len(outside), len(bad_dates)))
print("\nТипы графиков:")
for k, v in by_schedule.most_common():
    print("  {}: {}".format(k, v))
print("\nПо потокам:")
for k, v in by_stream.items():
    print("  {}: {}".format(k, dict(v)))
print("\n'Вывоз не осуществляется' с ненулевой частотой:", len(conflicts))
for x in conflicts[:30]:
    print("  FID, freq, МО, НП:", x)
print("Некорректные периоды:", len(bad_dates), bad_dates[:20])
print("Примеры периодов вне {}:".format(YEAR), outside[:20])
print("\n>52 не считается автоматической ошибкой. Правила 12/52 не применяются.")
print("ДАННЫЕ НЕ ИЗМЕНЯЛИСЬ.")
