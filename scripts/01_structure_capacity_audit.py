# -*- coding: utf-8 -*-
"""Структура, ключи, количество контейнеров и Capacity_m3. Только чтение."""
from collections import defaultdict
from qgis.core import QgsProject, QgsFeatureRequest

LAYER_NAME = "Слияние_all"
FIELDS = ["Идентификатор", "Реестровый номер",
          "Номер места площадки накопления ТКО",
          "_Тип контейнера (бункера)", "CTKO_KOL", "КГО_KOL",
          "PTKO_KOL", "Capacity_m3"]
STREAMS = {
    "Для совместного накопления ТКО": ("СТКО", "CTKO_KOL"),
    "Для крупногабаритных отходов": ("КГО", "КГО_KOL"),
    "Для раздельного накопления ТКО": ("РТКО", "PTKO_KOL"),
}

def txt(v):
    return "" if v is None else str(v).strip()

def num(v):
    if v is None or txt(v) == "":
        return None
    try:
        return float(str(v).replace(",", "."))
    except Exception:
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

pairs = defaultdict(int)
id_registry, id_site = defaultdict(set), defaultdict(set)
stats = defaultdict(lambda: {"rows": 0, "containers": 0, "missing_count": 0,
                             "bad_count": 0, "missing_capacity": 0,
                             "bad_capacity": 0, "capacity_sum": 0.0})
unknown = defaultdict(int)
empty_id = total = 0

for f in layer.getFeatures(req):
    total += 1
    uid, reg, site = txt(f["Идентификатор"]), txt(f["Реестровый номер"]), txt(f["Номер места площадки накопления ТКО"])
    stream = txt(f["_Тип контейнера (бункера)"])
    if not uid:
        empty_id += 1
    pairs[(uid, stream)] += 1
    id_registry[uid].add(reg)
    id_site[uid].add(site)
    if stream not in STREAMS:
        unknown[stream or "<ПУСТО>"] += 1
        continue
    label, count_field = STREAMS[stream]
    s = stats[label]
    s["rows"] += 1
    n = num(f[count_field])
    if n is None:
        s["missing_count"] += 1
    elif n <= 0 or int(n) != n:
        s["bad_count"] += 1
    else:
        s["containers"] += int(n)
    cap = num(f["Capacity_m3"])
    if cap is None:
        s["missing_capacity"] += 1
    elif cap <= 0:
        s["bad_capacity"] += 1
    else:
        s["capacity_sum"] += cap

duplicates = [(k, v) for k, v in pairs.items() if v > 1]
multi_reg = [k for k, v in id_registry.items() if len(v) > 1]
multi_site = [k for k, v in id_site.items() if len(v) > 1]

print("\n" + "=" * 72)
print("АУДИТ СТРУКТУРЫ И ВМЕСТИМОСТИ — ТОЛЬКО ЧТЕНИЕ")
print("=" * 72)
print("Слой:", layer.name(), "| строк:", total)
print("Пустых Идентификаторов:", empty_id)
print("Уникальных пар ID + поток:", len(pairs), "| повторов:", len(duplicates))
print("ID с несколькими реестровыми номерами:", len(multi_reg))
print("ID с несколькими номерами площадки:", len(multi_site))
print("Неизвестные потоки:", dict(unknown) if unknown else 0)
for label in ("СТКО", "КГО", "РТКО"):
    s = stats[label]
    print("\n{}: строки={}, контейнеры={}, пропуски количества={}, некорректные количества={}, пропуски Capacity={}, неположительная Capacity={}, сумма Capacity={:.3f}".format(
        label, s["rows"], s["containers"], s["missing_count"], s["bad_count"],
        s["missing_capacity"], s["bad_capacity"], s["capacity_sum"]))
if duplicates:
    print("Примеры повторов:", duplicates[:20])
if multi_reg:
    print("Примеры ID с разными реестровыми номерами:", multi_reg[:20])
if multi_site:
    print("Примеры ID с разными номерами площадки:", multi_site[:20])
print("\nДАННЫЕ НЕ ИЗМЕНЯЛИСЬ.")
