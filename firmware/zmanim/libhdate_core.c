/**
 * firmware/zmanim/libhdate_core.c
 * Core Hebrew calendar math and solar equations.
 * Based on libhdate algorithms (Amos Shapir, Yaacov Zamir, Boruch Baum).
 */

#include "libhdate_core.h"
#include <math.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#define HD_HOUR 1080
#define HD_DAY  (24 * HD_HOUR)
#define HD_WEEK (7 * HD_DAY)
#define HD_M(h, p) ((h) * HD_HOUR + (p))
#define HD_MONTH (HD_DAY + HD_M(12, 793))

static int hdate_days_from_3744(int hebrew_year) {
    int years_from_3744 = hebrew_year - 3744;
    int molad_3744 = HD_M(1 + 6, 779);
    int leap_months = (years_from_3744 * 7 + 1) / 19;
    int leap_left = (years_from_3744 * 7 + 1) % 19;
    int months = years_from_3744 * 12 + leap_months;
    int parts = months * HD_MONTH + molad_3744;
    int days = months * 28 + parts / HD_DAY - 2;

    int parts_left_in_week = parts % HD_WEEK;
    int parts_left_in_day = parts % HD_DAY;
    int week_day = parts_left_in_week / HD_DAY;

    if ((leap_left < 12 && week_day == 3 && parts_left_in_day >= HD_M(9 + 6, 204)) ||
        (leap_left < 7 && week_day == 2 && parts_left_in_day >= HD_M(15 + 6, 589))) {
        days++;
        week_day++;
    }

    if (week_day == 1 || week_day == 4 || week_day == 6) {
        days++;
    }

    return days;
}

int hdate_get_size_of_hebrew_year(int hebrew_year) {
    return hdate_days_from_3744(hebrew_year + 1) - hdate_days_from_3744(hebrew_year);
}

bool hdate_is_leap_year(int hebrew_year) {
    return ((hebrew_year * 7 + 1) % 19) < 7;
}

int hdate_months_in_year(int hebrew_year) {
    return hdate_is_leap_year(hebrew_year) ? 13 : 12;
}

static int hdate_get_year_type(int size_of_year, int new_year_dw) {
    static const int year_types[24] = {
        1, 0, 0, 2, 0, 3, 4, 0, 5, 0, 6, 7,
        8, 0, 9, 10, 0, 11, 0, 0, 12, 0, 13, 14
    };
    int offset = (new_year_dw + 1) / 2;
    offset += 4 * ((size_of_year % 10 - 3) + (size_of_year / 10 - 35));
    if (offset < 1 || offset > 24) return 0;
    return year_types[offset - 1];
}

int hdate_gdate_to_jd(int day, int month, int year) {
    int a = (14 - month) / 12;
    int y = year + 4800 - a;
    int m = month + 12 * a - 3;
    return day + (153 * m + 2) / 5 + 365 * y + y / 4 - y / 100 + y / 400 - 32045;
}

void hdate_jd_to_gdate(int jd, int *d, int *m, int *y) {
    int l = jd + 68569;
    int n = (4 * l) / 146097;
    l = l - (146097 * n + 3) / 4;
    int i = (4000 * (l + 1)) / 1461001;
    l = l - (1461 * i) / 4 + 31;
    int j = (80 * l) / 2447;
    *d = l - (2447 * j) / 80;
    l = j / 11;
    *m = j + 2 - (12 * l);
    *y = 100 * (n - 49) + i + l;
}

int hdate_to_jd(int day, int month, int year) {
    if (month == 13) month = 6;
    if (month == 14) {
        month = 6;
        day += 30;
    }
    int days_from_3744 = hdate_days_from_3744(year);
    day = days_from_3744 + (59 * (month - 1) + 1) / 2 + day;
    int length_of_year = hdate_days_from_3744(year + 1) - days_from_3744;

    if (length_of_year % 10 > 4 && month > 2) day++;
    if (length_of_year % 10 < 4 && month > 3) day--;
    if (length_of_year > 365 && month > 6) day += 30;

    return day + 1715118;
}

static void hdate_jd_to_hdate_internal(int jd, int *day, int *month, int *year, int *jd_t1, int *jd_t1_next) {
    int g_d, g_m, g_y;
    hdate_jd_to_gdate(jd, &g_d, &g_m, &g_y);
    *year = g_y + 3760;

    int t1 = hdate_days_from_3744(*year) + 1715119;
    int t1_next = hdate_days_from_3744(*year + 1) + 1715119;

    if (t1_next <= jd) {
        (*year)++;
        t1 = t1_next;
        t1_next = hdate_days_from_3744(*year + 1) + 1715119;
    }

    int size_of_year = t1_next - t1;
    int days = jd - t1;

    if (days >= (size_of_year - 236)) {
        days -= (size_of_year - 236);
        *month = days * 2 / 59;
        *day = days - (*month * 59 + 1) / 2 + 1;
        *month += 5;
        if (size_of_year > 355 && *month <= 6) {
            *month += 8;
        }
    } else {
        if (size_of_year % 10 > 4 && days == 59) {
            *month = 1;
            *day = 30;
        } else if (size_of_year % 10 > 4 && days > 59) {
            *month = (days - 1) * 2 / 59;
            *day = days - (*month * 59 + 1) / 2;
        } else if (size_of_year % 10 < 4 && days > 87) {
            *month = (days + 1) * 2 / 59;
            *day = days - (*month * 59 + 1) / 2 + 2;
        } else {
            *month = days * 2 / 59;
            *day = days - (*month * 59 + 1) / 2 + 1;
        }
        (*month)++;
    }

    if (jd_t1) *jd_t1 = t1;
    if (jd_t1_next) *jd_t1_next = t1_next;
}

void hdate_from_jd(HDate *h, int jd) {
    int jd_t1 = 0, jd_t1_next = 0;
    hdate_jd_to_gdate(jd, &(h->gd_day), &(h->gd_mon), &(h->gd_year));
    hdate_jd_to_hdate_internal(jd, &(h->hd_day), &(h->hd_mon), &(h->hd_year), &jd_t1, &jd_t1_next);

    h->hd_dw = (jd + 1) % 7 + 1;
    h->hd_size_of_year = jd_t1_next - jd_t1;
    h->hd_new_year_dw = (jd_t1 + 1) % 7 + 1;
    h->hd_year_type = hdate_get_year_type(h->hd_size_of_year, h->hd_new_year_dw);
    h->hd_jd = jd;
    h->hd_days = jd - jd_t1 + 1;
    h->hd_weeks = ((h->hd_days - 1) + (h->hd_new_year_dw - 1)) / 7 + 1;
}

void hdate_from_gdate(HDate *h, int day, int month, int year) {
    int jd = hdate_gdate_to_jd(day, month, year);
    hdate_from_jd(h, jd);
}

int hdate_get_holiday(const HDate *h, int diaspora) {
    static const int halachic_days_table[14][30] = {
        { 1, 2, 3, 3, 0, 0, 0, 0, 37, 4, 0, 0, 0, 39, 5, 31, 6, 6, 6, 6, 7, 27, 8, 0, 0, 0, 0, 0, 0, 0 }, /* Tishrei */
        { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 },       /* Cheshvan */
        { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 9, 9, 9, 9, 9, 9 },       /* Kislev */
        { 9, 9, 9, 0, 0, 0, 0, 0, 0, 10, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 },      /* Tevet */
        { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 },      /* Shevat */
        { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 12, 13, 14, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 },   /* Adar */
        { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 38, 15, 32, 16, 16, 16, 16, 28, 29, 0, 0, 0, 0, 0, 0, 0, 0 }, /* Nisan */
        { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 18, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 },      /* Iyar */
        { 0, 0, 0, 0, 19, 20, 30, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 },      /* Sivan */
        { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 21, 21, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 },      /* Tammuz */
        { 0, 0, 0, 0, 0, 0, 0, 0, 22, 22, 0, 0, 0, 0, 23, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 },   /* Av */
        { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 },       /* Elul */
        { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 },       /* Adar I */
        { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12, 0, 12, 13, 14, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 }    /* Adar II */
    };

    if (h->hd_mon < 1 || h->hd_mon > 14 || h->hd_day < 1 || h->hd_day > 30) return 0;
    int day_code = halachic_days_table[h->hd_mon - 1][h->hd_day - 1];

    /* Fast of Gedaliah moved if Shabbat */
    if (day_code == 3) {
        if ((h->hd_day == 3 && h->hd_dw == 7) || (h->hd_day == 4 && h->hd_dw != 1)) {
            day_code = 0;
        }
    }
    /* 17 Tammuz and 9 Av moved if Shabbat */
    if (day_code == 21 || day_code == 22) {
        if ((h->hd_day == 17 && h->hd_dw == 7) || (h->hd_day == 18 && h->hd_dw != 1) ||
            (h->hd_day == 9 && h->hd_dw == 7) || (h->hd_day == 10 && h->hd_dw != 1)) {
            day_code = 0;
        }
    }

    /* Fast of Esther moved to Thursday if 13 Adar is Shabbat */
    if (day_code == 12) {
        if ((h->hd_day == 13 && h->hd_dw == 7) || (h->hd_day == 11 && h->hd_dw != 5)) {
            day_code = 0;
        }
    }

    /* Diaspora vs Israel Yom Tov days */
    if (!diaspora) {
        if (day_code == 31 || day_code == 32) day_code = 6;  /* Sukkot/Pesach 2nd day is Chol HaMoed in Israel */
        if (day_code == 27) day_code = 8;                     /* Simchat Torah merged with Shemini Atzeret */
        if (day_code == 29 || day_code == 30) day_code = 0;   /* 8th day Pesach / 2nd day Shavuot is weekday in Israel */
    }

    return day_code;
}

int hdate_get_omer_day(const HDate *h) {
    if (h->hd_mon == 7) {
        /* Nisan */
        if (h->hd_day >= 16) return h->hd_day - 15;
    } else if (h->hd_mon == 8) {
        /* Iyar */
        return 15 + h->hd_day;
    } else if (h->hd_mon == 9) {
        /* Sivan */
        if (h->hd_day <= 5) return 44 + h->hd_day;
    }
    return 0;
}

int hdate_day_of_year(int day, int month, int year) {
    int jd = hdate_gdate_to_jd(day, month, year);
    int jd_jan1 = hdate_gdate_to_jd(1, 1, year);
    return jd - jd_jan1 + 1;
}

void hdate_solar_times(int day, int month, int year,
                       double latitude, double longitude, double deg_below_zenith,
                       int *sunrise_utc_sec, int *sunset_utc_sec) {
    int doy = hdate_day_of_year(day, month, year);
    double gamma = 2.0 * M_PI * ((double)(doy - 1) / 365.0);

    /* Equation of time in minutes */
    double eqtime = 229.18 * (0.000075 + 0.001868 * cos(gamma) - 0.032077 * sin(gamma) -
                             0.014615 * cos(2.0 * gamma) - 0.040849 * sin(2.0 * gamma));

    /* Solar declination angle in radians */
    double decl = 0.006918 - 0.399912 * cos(gamma) + 0.070257 * sin(gamma) -
                  0.006758 * cos(2.0 * gamma) + 0.000907 * sin(2.0 * gamma) -
                  0.002697 * cos(3.0 * gamma) + 0.00148 * sin(3.0 * gamma);

    double zenith_rad = M_PI * deg_below_zenith / 180.0;
    double lat_rad = M_PI * latitude / 180.0;

    double cos_ha = (cos(zenith_rad) / (cos(lat_rad) * cos(decl))) - (tan(lat_rad) * tan(decl));

    if (cos_ha > 1.0) {
        /* Sun never rises */
        *sunrise_utc_sec = -1;
        *sunset_utc_sec = -1;
        return;
    }
    if (cos_ha < -1.0) {
        /* Sun never sets */
        *sunrise_utc_sec = 0;
        *sunset_utc_sec = 86400;
        return;
    }

    double ha_rad = acos(cos_ha);
    double ha_deg = ha_rad * 180.0 / M_PI;

    double time_utc_min_sr = 720.0 - 4.0 * longitude - ha_deg * 4.0 - eqtime;
    double time_utc_min_ss = 720.0 - 4.0 * longitude + ha_deg * 4.0 - eqtime;

    *sunrise_utc_sec = (int)(time_utc_min_sr * 60.0);
    *sunset_utc_sec = (int)(time_utc_min_ss * 60.0);
}
