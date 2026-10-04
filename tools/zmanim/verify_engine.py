#!/usr/bin/env python3
"""
tools/zmanim/verify_engine.py
Verification suite for Hebrew calendar and Zmanim calculations in Python.
Matches the logic implemented in firmware/zmanim/libhdate_core.c and HebrewCalendarEngine.cpp.
"""

import sys
import math

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def hdate_days_from_3744(hebrew_year: int) -> int:
    years_from_3744 = hebrew_year - 3744
    molad_3744 = (1 + 6) * 1080 + 779
    leap_months = (years_from_3744 * 7 + 1) // 19
    leap_left = (years_from_3744 * 7 + 1) % 19
    months = years_from_3744 * 12 + leap_months
    month_parts = 24 * 1080 + 12 * 1080 + 793
    day_parts = 24 * 1080
    week_parts = 7 * day_parts

    parts = months * month_parts + molad_3744
    days = months * 28 + parts // day_parts - 2

    parts_left_in_week = parts % week_parts
    parts_left_in_day = parts % day_parts
    week_day = parts_left_in_week // day_parts

    m_9_6_204 = (9 + 6) * 1080 + 204
    m_15_6_589 = (15 + 6) * 1080 + 589

    if (leap_left < 12 and week_day == 3 and parts_left_in_day >= m_9_6_204) or \
       (leap_left < 7 and week_day == 2 and parts_left_in_day >= m_15_6_589):
        days += 1
        week_day += 1

    if week_day in (1, 4, 6):
        days += 1

    return days

def hdate_gdate_to_jd(day: int, month: int, year: int) -> int:
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    return day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045

def hdate_jd_to_gdate(jd: int):
    l = jd + 68569
    n = (4 * l) // 146097
    l = l - (146097 * n + 3) // 4
    i = (4000 * (l + 1)) // 1461001
    l = l - (1461 * i) // 4 + 31
    j = (80 * l) // 2447
    d = l - (2447 * j) // 80
    l = j // 11
    m = j + 2 - (12 * l)
    y = 100 * (n - 49) + i + l
    return d, m, y

def hdate_from_jd(jd: int):
    g_d, g_m, g_y = hdate_jd_to_gdate(jd)
    h_y = g_y + 3760

    t1 = hdate_days_from_3744(h_y) + 1715119
    t1_next = hdate_days_from_3744(h_y + 1) + 1715119

    if t1_next <= jd:
        h_y += 1
        t1 = t1_next
        t1_next = hdate_days_from_3744(h_y + 1) + 1715119

    size_of_year = t1_next - t1
    days = jd - t1

    if days >= (size_of_year - 236):
        days -= (size_of_year - 236)
        h_m = days * 2 // 59
        h_d = days - (h_m * 59 + 1) // 2 + 1
        h_m += 5
        if size_of_year > 355 and h_m <= 6:
            h_m += 8
    else:
        if size_of_year % 10 > 4 and days == 59:
            h_m = 1
            h_d = 30
        elif size_of_year % 10 > 4 and days > 59:
            h_m = (days - 1) * 2 // 59
            h_d = days - (h_m * 59 + 1) // 2
        elif size_of_year % 10 < 4 and days > 87:
            h_m = (days + 1) * 2 // 59
            h_d = days - (h_m * 59 + 1) // 2 + 2
        else:
            h_m = days * 2 // 59
            h_d = days - (h_m * 59 + 1) // 2 + 1
        h_m += 1

    dw = (jd + 1) % 7 + 1
    return {
        "hd_day": h_d,
        "hd_mon": h_m,
        "hd_year": h_y,
        "gd_day": g_d,
        "gd_mon": g_m,
        "gd_year": g_y,
        "hd_dw": dw,
        "size_of_year": size_of_year
    }

def hdate_solar_times(day: int, month: int, year: int, lat: float, lon: float, zenith_deg: float):
    jd = hdate_gdate_to_jd(day, month, year)
    jd_jan1 = hdate_gdate_to_jd(1, 1, year)
    doy = jd - jd_jan1 + 1

    gamma = 2.0 * math.pi * ((doy - 1) / 365.0)

    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(gamma) - 0.032077 * math.sin(gamma) -
                       0.014615 * math.cos(2.0 * gamma) - 0.040849 * math.sin(2.0 * gamma))

    decl = 0.006918 - 0.399912 * math.cos(gamma) + 0.070257 * math.sin(gamma) - \
           0.006758 * math.cos(2.0 * gamma) + 0.000907 * math.sin(2.0 * gamma) - \
           0.002697 * math.cos(3.0 * gamma) + 0.00148 * math.sin(3.0 * gamma)

    zenith_rad = math.pi * zenith_deg / 180.0
    lat_rad = math.pi * lat / 180.0

    cos_ha = (math.cos(zenith_rad) / (math.cos(lat_rad) * math.cos(decl))) - (math.tan(lat_rad) * math.tan(decl))

    if cos_ha > 1.0 or cos_ha < -1.0:
        return None, None

    ha_deg = math.acos(cos_ha) * 180.0 / math.pi
    sr_utc_min = 720.0 - 4.0 * lon - ha_deg * 4.0 - eqtime
    ss_utc_min = 720.0 - 4.0 * lon + ha_deg * 4.0 - eqtime

    return int(sr_utc_min * 60), int(ss_utc_min * 60)

def sec_to_str(s: int) -> str:
    if s is None:
        return "--:--"
    s = s % 86400
    h = s // 3600
    m = (s % 3600) // 60
    return f"{h:02d}:{m:02d}"

def main():
    print("=== Validating Hebrew Calendar & Zmanim Calculations ===")
    
    # 1. Test Rosh Hashanah 5785: 2024-10-03 -> 1 Tishrei 5785
    jd_rh = hdate_gdate_to_jd(3, 10, 2024)
    h_rh = hdate_from_jd(jd_rh)
    print(f"2024-10-03 -> Hebrew: {h_rh['hd_day']}/{h_rh['hd_mon']}/{h_rh['hd_year']} (DOW: {h_rh['hd_dw']})")
    assert h_rh["hd_day"] == 1 and h_rh["hd_mon"] == 1 and h_rh["hd_year"] == 5785

    # 2. Test Pesach 5785: 2025-04-13 -> 15 Nisan 5785
    jd_pesach = hdate_gdate_to_jd(13, 4, 2025)
    h_pesach = hdate_from_jd(jd_pesach)
    print(f"2025-04-13 -> Hebrew: {h_pesach['hd_day']}/{h_pesach['hd_mon']}/{h_pesach['hd_year']}")
    assert h_pesach["hd_day"] == 15 and h_pesach["hd_mon"] == 7 and h_pesach["hd_year"] == 5785

    # 3. Test Solar calculations for Jerusalem (lat 31.7767, lon 35.2345, UTC+2)
    lat, lon, tz = 31.7767, 35.2345, 2.0
    sr_utc, ss_utc = hdate_solar_times(4, 10, 2026, lat, lon, 90.8333)
    sr_loc = (sr_utc + int(tz * 3600)) % 86400
    ss_loc = (ss_utc + int(tz * 3600)) % 86400

    alot_utc, _ = hdate_solar_times(4, 10, 2026, lat, lon, 106.1)
    alot_loc = (alot_utc + int(tz * 3600)) % 86400

    _, tzeit_utc = hdate_solar_times(4, 10, 2026, lat, lon, 98.5)
    tzeit_loc = (tzeit_utc + int(tz * 3600)) % 86400

    day_len = ss_loc - sr_loc
    shaah = day_len / 12.0
    shema_gra = sr_loc + int(3.0 * shaah)
    tefilah_gra = sr_loc + int(4.0 * shaah)
    chatzot = sr_loc + int(6.0 * shaah)

    print(f"Jerusalem 2026-10-04:")
    print(f"  Alot HaShachar:     {sec_to_str(alot_loc)}")
    print(f"  Sunrise (Hanetz):   {sec_to_str(sr_loc)}")
    print(f"  Sof Zman Shema Gra: {sec_to_str(shema_gra)}")
    print(f"  Sof Zman Tefilah:   {sec_to_str(tefilah_gra)}")
    print(f"  Chatzot:            {sec_to_str(chatzot)}")
    print(f"  Sunset (Shkia):     {sec_to_str(ss_loc)}")
    print(f"  Tzeit HaKochavim:   {sec_to_str(tzeit_loc)}")
    print(f"  Shaah Zmanit (min): {shaah / 60:.2f}")

    assert alot_loc < sr_loc < shema_gra < tefilah_gra < chatzot < ss_loc < tzeit_loc

    # 4. Test Solar calculations for Bogotá, Colombia (lat 4.7110, lon -74.0721, UTC-5)
    lat_bog, lon_bog, tz_bog = 4.7110, -74.0721, -5.0
    sr_bog_utc, ss_bog_utc = hdate_solar_times(4, 10, 2026, lat_bog, lon_bog, 90.8333)
    sr_bog_loc = (sr_bog_utc + int(tz_bog * 3600)) % 86400
    ss_bog_loc = (ss_bog_utc + int(tz_bog * 3600)) % 86400

    alot_bog_utc, _ = hdate_solar_times(4, 10, 2026, lat_bog, lon_bog, 106.1)
    alot_bog_loc = (alot_bog_utc + int(tz_bog * 3600)) % 86400

    _, tzeit_bog_utc = hdate_solar_times(4, 10, 2026, lat_bog, lon_bog, 98.5)
    tzeit_bog_loc = (tzeit_bog_utc + int(tz_bog * 3600)) % 86400

    day_len_bog = ss_bog_loc - sr_bog_loc
    shaah_bog = day_len_bog / 12.0
    shema_gra_bog = sr_bog_loc + int(3.0 * shaah_bog)
    tefilah_gra_bog = sr_bog_loc + int(4.0 * shaah_bog)
    chatzot_bog = sr_bog_loc + int(6.0 * shaah_bog)

    print(f"Bogotá, Colombia 2026-10-04 (User Locale):")
    print(f"  Alot HaShachar:     {sec_to_str(alot_bog_loc)}")
    print(f"  Sunrise (Hanetz):   {sec_to_str(sr_bog_loc)}")
    print(f"  Sof Zman Shema Gra: {sec_to_str(shema_gra_bog)}")
    print(f"  Sof Zman Tefilah:   {sec_to_str(tefilah_gra_bog)}")
    print(f"  Chatzot:            {sec_to_str(chatzot_bog)}")
    print(f"  Sunset (Shkia):     {sec_to_str(ss_bog_loc)}")
    print(f"  Tzeit HaKochavim:   {sec_to_str(tzeit_bog_loc)}")
    print(f"  Shaah Zmanit (min): {shaah_bog / 60:.2f}")

    assert alot_bog_loc < sr_bog_loc < shema_gra_bog < tefilah_gra_bog < chatzot_bog < ss_bog_loc < tzeit_bog_loc
    print("[OK] All calendar, Jerusalem and Bogotá solar time assertions passed successfully!")

if __name__ == "__main__":
    main()
