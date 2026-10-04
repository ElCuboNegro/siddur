/**
 * firmware/zmanim/HebrewCalendarEngine.h
 * High-level C++ Liturgical & Halachic Engine for embedded e-ink Siddur.
 */

#ifndef SIDDUR_HEBREW_CALENDAR_ENGINE_H
#define SIDDUR_HEBREW_CALENDAR_ENGINE_H

#include "libhdate_core.h"
#include <string>
#include <vector>

namespace siddur {

struct GeoLocation {
    double latitude;    // Decimal degrees, positive North (e.g. 31.7767 for Jerusalem, 40.7128 for New York)
    double longitude;   // Decimal degrees, positive East (e.g. 35.2345 for Jerusalem, -74.0060 for New York)
    double timeZoneOffsetHours; // e.g. +2.0 or +3.0 (DST), -5.0 for New York
    bool isIsrael;      // Controls diaspora vs Israel liturgical customs
};

struct LiturgicalInsertions {
    bool mashivHaRuach;      // Winter addition in Amidah 2nd blessing ("Mashiv HaRuach UMorid HaGeshem")
    bool moridHaTal;         // Summer addition ("Morid HaTal")
    bool talUMatar;          // Winter blessing in Amidah 9th blessing ("Barech Aleinu" with "VeTen Tal UMatar")
    bool barechAleinu;       // Same as talUMatar
    bool alHaNissimChanukah; // Addition in Amidah and Birkat HaMazon for Chanukah
    bool alHaNissimPurim;    // Addition for Purim
    bool yaalehVeYavo;       // Addition on Rosh Chodesh and Yom Tov / Chol HaMoed
    bool tachanunOmitted;    // Tachanun is skipped (Shabbat, Rosh Chodesh, holidays, festive days)
    bool aseretYemeiTeshuvah;// 10 days of repentance (special additions in Amidah)
    bool roshChodesh;        // Today is Rosh Chodesh (1st of month, or 30th of previous month)
    int  omerDay;            // Sfirat HaOmer day (1..49) or 0 if outside Omer
    std::string holidayName; // Name of the holiday/commemoration today (if any)
};

struct ZmanimDay {
    int alotHashacharSec;    // Dawn (16.1 degrees) in seconds from midnight local time
    int misheyakirSec;       // Earliest Tallit/Tefillin (10.2 degrees)
    int sunriseSec;          // Hanetz HaChama (astronomical sunrise)
    int sofZmanShemaMgaSec;  // Sof Zman Shema according to Magen Avraham (3 shaot zmaniyot MGA)
    int sofZmanShemaGraSec;  // Sof Zman Shema according to Vilna Gaon (3 shaot zmaniyot Gra)
    int sofZmanTefilahGraSec;// Sof Zman Tefilah according to Gra (4 shaot zmaniyot Gra)
    int chatzotSec;          // Midday (Solar noon / 6 shaot zmaniyot)
    int minchaGedolaSec;     // Earliest Mincha (Chatzot + 30 min)
    int minchaKetanaSec;     // 9.5 shaot zmaniyot
    int plagHaMinchaSec;     // 10.75 shaot zmaniyot
    int sunsetSec;           // Shkiat HaChama
    int tzeitHaKochavimSec;  // Nightfall (8.5 degrees / 3 medium stars)
    int candleLightingSec;   // Shabbat/Yom Tov candle lighting (normally Sunset - 18 minutes)
    double shaahZmanitSec;   // Duration of one halachic hour in seconds
};

enum class RecommendedPrayer {
    None,
    Shacharit,
    Mincha,
    Arvit,
    KiddushFridayNight,
    KiddushShabbatDay,
    Havdalah,
    BirkatHaMazon
};

class HebrewCalendarEngine {
public:
    HebrewCalendarEngine();

    // Set or update user location
    void setLocation(const GeoLocation& location);
    const GeoLocation& getLocation() const { return location_; }

    // Core date computations
    HDate computeDate(int day, int month, int year) const;

    // Liturgical determinations
    LiturgicalInsertions getInsertions(const HDate& hdate) const;

    // Astronomical Zmanim for the day
    ZmanimDay computeZmanim(int day, int month, int year) const;

    // Time-aware recommendation given current local time
    // currentSecondsSinceMidnight: e.g. 14:30:00 -> 14*3600 + 30*60 = 52200
    RecommendedPrayer recommendPrayer(const HDate& hdate, const ZmanimDay& zmanim, int currentSecondsSinceMidnight) const;

    // String formatting helpers
    static std::string formatTime(int secondsFromMidnight);
    static std::string getHebrewMonthName(int hebrewMonth, bool isLeapYear);
    static std::string getSpanishMonthName(int hebrewMonth, bool isLeapYear);

private:
    GeoLocation location_;
};

} // namespace siddur

#endif // SIDDUR_HEBREW_CALENDAR_ENGINE_H
