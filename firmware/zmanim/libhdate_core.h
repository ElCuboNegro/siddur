/**
 * firmware/zmanim/libhdate_core.h
 * Self-contained core Hebrew calendar and astronomical algorithms from libhdate.
 * Zero external dependencies (safe for embedded ESP32-S3, Arduino, desktop test harnesses).
 */

#ifndef SIDDUR_LIBHDATE_CORE_H
#define SIDDUR_LIBHDATE_CORE_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stdbool.h>

#define HDATE_DIASPORA 1
#define HDATE_ISRAEL   0

typedef struct {
    int hd_day;             /* 1..30 */
    int hd_mon;             /* 1..14: 1=Tishrei, 7=Nisan, 12=Adar (regular) or Adar I (leap), 13=Adar I, 14=Adar II */
    int hd_year;            /* e.g. 5786 */
    int gd_day;             /* 1..31 */
    int gd_mon;             /* 1..12 */
    int gd_year;            /* e.g. 2026 */
    int hd_dw;              /* Day of week: 1=Sunday, 7=Saturday (Shabbat) */
    int hd_size_of_year;    /* 353, 354, 355, 383, 384, 385 */
    int hd_new_year_dw;     /* Day of week of Rosh Hashanah (Tishrei 1) */
    int hd_year_type;       /* 1..14 year classification */
    int hd_jd;              /* Julian Day number */
    int hd_days;            /* Days elapsed since 1 Tishrei */
    int hd_weeks;           /* Weeks elapsed since 1 Tishrei */
} HDate;

/* Conversion and calendar functions */
void hdate_from_gdate(HDate *h, int day, int month, int year);
void hdate_from_jd(HDate *h, int jd);
int  hdate_to_jd(int day, int month, int year);
int  hdate_gdate_to_jd(int day, int month, int year);
void hdate_jd_to_gdate(int jd, int *day, int *month, int *year);
bool hdate_is_leap_year(int hebrew_year);
int  hdate_months_in_year(int hebrew_year);

/* Holidays, fasts and observances */
int  hdate_get_holiday(const HDate *h, int diaspora);
int  hdate_get_omer_day(const HDate *h);
int  hdate_get_parasha(const HDate *h, int diaspora);

/* Astronomical sun calculations */
int  hdate_day_of_year(int day, int month, int year);
void hdate_solar_times(int day, int month, int year,
                       double latitude, double longitude, double deg_below_zenith,
                       int *sunrise_utc_sec, int *sunset_utc_sec);

#ifdef __cplusplus
}
#endif

#endif /* SIDDUR_LIBHDATE_CORE_H */
