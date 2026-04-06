"""
eea39_bbox.py — EEA-39 country bounding boxes for approximate point-in-Europe check.

EEA-39: EU27 + EEA/EFTA (Iceland, Liechtenstein, Norway, Switzerland)
        + UK + Western Balkans (Albania, Bosnia, Kosovo, Montenegro,
          North Macedonia, Serbia) + Turkey.

Bounding boxes are approximate — suitable for routing GLO-10 vs GLO-30.
"""

# (country_name, min_lat, max_lat, min_lon, max_lon)
EEA39_BOXES = [
    # EU 27
    ("Austria",          46.4, 49.0,  9.5, 17.2),
    ("Belgium",          49.5, 51.5,  2.5,  6.4),
    ("Bulgaria",         41.2, 44.2, 22.4, 28.6),
    ("Croatia",          42.4, 46.6, 13.5, 19.5),
    ("Cyprus",           34.6, 35.7, 32.3, 34.6),
    ("Czech Republic",   48.6, 51.1, 12.1, 18.9),
    ("Denmark",          54.6, 57.8,  8.0, 15.2),
    ("Estonia",          57.5, 59.7, 21.8, 28.2),
    ("Finland",          59.8, 70.1, 20.0, 31.6),
    ("France",           42.3, 51.1, -5.2,  8.2),
    ("Germany",          47.3, 55.1,  5.9, 15.0),
    ("Greece",           34.8, 41.7, 19.4, 26.6),
    ("Hungary",          45.7, 48.6, 16.1, 22.9),
    ("Ireland",          51.4, 55.4,-10.5, -6.0),
    ("Italy",            35.5, 47.1,  6.6, 18.5),
    ("Latvia",           55.7, 57.8, 21.0, 28.2),
    ("Lithuania",        53.9, 56.5, 21.0, 26.9),
    ("Luxembourg",       49.4, 50.2,  5.7,  6.5),
    ("Malta",            35.8, 36.1, 14.2, 14.6),
    ("Netherlands",      50.8, 53.6,  3.4,  7.2),
    ("Poland",           49.0, 54.8, 14.1, 24.2),
    ("Portugal",         36.9, 42.2, -9.5, -6.2),
    ("Romania",          43.6, 48.3, 20.3, 30.0),
    ("Slovakia",         47.7, 49.6, 16.8, 22.6),
    ("Slovenia",         45.4, 46.9, 13.4, 16.6),
    ("Spain",            36.0, 43.8, -9.3,  3.4),
    ("Sweden",           55.3, 69.1, 11.1, 24.2),
    # EEA / EFTA
    ("Iceland",          63.3, 66.6,-24.5,-13.5),
    ("Liechtenstein",    47.0, 47.3,  9.5,  9.7),
    ("Norway",           57.9, 71.2,  4.6, 31.1),
    ("Switzerland",      45.8, 47.8,  5.9, 10.5),
    # UK
    ("United Kingdom",   49.9, 61.0, -8.6,  1.8),
    # Western Balkans
    ("Albania",          39.6, 42.7, 19.3, 21.1),
    ("Bosnia",           42.6, 45.3, 15.7, 19.7),
    ("Kosovo",           41.9, 43.3, 20.0, 21.8),
    ("Montenegro",       41.9, 43.6, 18.4, 20.4),
    ("North Macedonia",  40.9, 42.4, 20.5, 23.1),
    ("Serbia",           42.2, 46.2, 18.8, 23.0),
    # Turkey
    ("Turkey",           36.0, 42.1, 26.0, 45.0),
]


def is_in_eea39(lat, lon):
    """
    Return (True, country_name) if (lat, lon) falls inside any EEA-39
    bounding box, else (False, None).
    """
    for name, min_lat, max_lat, min_lon, max_lon in EEA39_BOXES:
        if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
            return True, name
    return False, None
