# -*- coding: utf-8 -*-
"""Профиль уникальных значений расписаний для восстановления парсера. Только чтение."""
from collections import Counter
from qgis.core import QgsProject, QgsFeatureRequest

LAYER_NAME = "Слияние_all"
FIELDS = ["_Вид графика вывоза отходов", "_Периодичность вывоза",
          "_Дни вывоза отходов", "_Периодичность в рамках месяца",
          "_Сцеплённая строка", "_Дата начала вывоза отходов"]
MAX_VALUES = 200

def txt(v): return "" if v is None else str(v).strip()

layers = QgsProject.instance().mapLayersByName(LAYER_NAME)
if not layers: raise Exception("Слой '{}' не найден.".format(LAYER_NAME))
layer = layers[0]
missing = [x for x in FIELDS if layer.fields().indexFromName(x) < 0]
if missing: raise Exception("Не найдены поля: {}".format(", ".join(missing)))
req = QgsFeatureRequest()
req.setSubsetOfAttributes(FIELDS, layer.fields())
req.setFlags(QgsFeatureRequest.NoGeometry)
counters = {name: Counter() for name in FIELDS}
for f in layer.getFeatures(req):
    for name in FIELDS:
        value = txt(f[name])
        counters[name][value if value else "<ПУСТО>"] += 1
for name in FIELDS:
    c = counters[name]
    print("\n" + "=" * 88)
    print("{} | уникальных значений: {} | строк: {}".format(name, len(c), sum(c.values())))
    for value, count in c.most_common(MAX_VALUES):
        print("{:>6} | {}".format(count, value))
    if len(c) > MAX_VALUES:
        print("... пропущено значений:", len(c) - MAX_VALUES)
print("\nПРОФИЛЬ ЗАВЕРШЁН. ДАННЫЕ НЕ ИЗМЕНЯЛИСЬ.")
