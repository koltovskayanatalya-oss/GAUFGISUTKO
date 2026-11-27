# -*- coding: utf-8 -*-
"""Сверка сохранённой массы с M = Capacity * Frequency * Kfill * Density. Только чтение."""
from collections import defaultdict
from qgis.core import QgsProject, QgsFeatureRequest

LAYER_NAME = "Слияние_all"
TYPE_FIELD, CAP_FIELD = "_Тип контейнера (бункера)", "Capacity_m3"
FREQ_FIELD, MASS_FIELD = "_Итоговое количество вывозов", "mno_mass_calculation"
PARAMS = {
    "Для совместного накопления ТКО": ("СТКО", 0.75, 0.22),
    "Для раздельного накопления ТКО": ("РТКО", 0.75, 0.22),
    "Для крупногабаритных отходов": ("КГО", 0.60, 0.15),
}
TOL = 0.00001

def txt(v): return "" if v is None else str(v).strip()
def val(v):
    if v is None or txt(v) == "": return None
    try: return float(str(v).replace(",", "."))
    except Exception: return None

layers = QgsProject.instance().mapLayersByName(LAYER_NAME)
if not layers: raise Exception("Слой '{}' не найден.".format(LAYER_NAME))
layer = layers[0]
fields = [TYPE_FIELD, CAP_FIELD, FREQ_FIELD, MASS_FIELD]
missing = [x for x in fields if layer.fields().indexFromName(x) < 0]
if missing: raise Exception("Не найдены поля: {}".format(", ".join(missing)))
req = QgsFeatureRequest()
req.setSubsetOfAttributes(fields, layer.fields())
req.setFlags(QgsFeatureRequest.NoGeometry)

stats = defaultdict(lambda: {"rows": 0, "missing": 0, "mismatch": 0, "expected": 0.0, "stored": 0.0})
examples, unknown = [], 0
for f in layer.getFeatures(req):
    stream = txt(f[TYPE_FIELD])
    if stream not in PARAMS:
        unknown += 1
        continue
    label, kfill, density = PARAMS[stream]
    s = stats[label]; s["rows"] += 1
    cap, freq, stored = val(f[CAP_FIELD]), val(f[FREQ_FIELD]), val(f[MASS_FIELD])
    if cap is None or freq is None or stored is None:
        s["missing"] += 1
        continue
    expected = cap * freq * kfill * density
    s["expected"] += expected; s["stored"] += stored
    diff = stored - expected
    if abs(diff) > TOL:
        s["mismatch"] += 1
        if len(examples) < 100:
            examples.append((f.id(), label, cap, freq, stored, expected, diff))

print("\n" + "=" * 86)
print("АУДИТ ФОРМУЛЫ МАССЫ — ТОЛЬКО ЧТЕНИЕ")
print("Параметры: СТКО/РТКО 0.75 × 0.22; КГО 0.60 × 0.15")
print("=" * 86)
for label in ("СТКО", "КГО", "РТКО"):
    s = stats[label]
    print("\n{}: строк={}, пропусков входов={}, несовпадений={}, по формуле={:.6f}, в поле={:.6f}".format(
        label, s["rows"], s["missing"], s["mismatch"], s["expected"], s["stored"]))
print("\nНеизвестных потоков:", unknown)
print("Примеры расхождений (FID, поток, Capacity, Freq, сохранено, ожидалось, разница):")
for x in examples[:30]: print(" ", x)
print("\nЗапускать только после утверждения частоты за 2026 год и повторного расчёта mno_mass_calculation с Kзап=0.60 для КГО. Старое сохранённое поле содержит прежний сценарий и до пересчёта ожидаемо не совпадёт.")
print("Поле mno_mass_calculation НЕ изменялось.")
