# -*- coding: utf-8 -*-
import csv
import os


def load_zones(plugin_dir):
    path = os.path.join(plugin_dir, 'data', 'zone_parameters.csv')
    zones = []
    with open(path, 'r', encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            zones.append({
                'zone_number': int(row['zone_number']),
                'zone_roman': row['zone_roman'],
                'epsg': int(row['epsg']),
                'lat_0': float(row['lat_0']),
                'lon_0': float(row['lon_0']),
                'area_summary': row['area_summary'],
            })
    if len(zones) != 19:
        raise ValueError('座標系対応表は19系である必要があります。')
    return zones
