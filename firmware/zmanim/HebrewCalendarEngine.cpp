/**
 * firmware/zmanim/HebrewCalendarEngine.cpp
 * Implementation of HebrewCalendarEngine.
 */

#include "HebrewCalendarEngine.h"
#include <cstdio>
#include <cmath>

namespace siddur {

HebrewCalendarEngine::HebrewCalendarEngine() {
    // Default location: Jerusalem, Israel
    location_.latitude = 31.7767;
    location_.longitude = 35.2345;
    location_.timeZoneOffsetHours = 2.0;
    location_.isIsrael = true;
}

void HebrewCalendarEngine::setLocation(const GeoLocation& location) {
    location_ = location;
}

HDate HebrewCalendarEngine::computeDate(int day, int month, int year) const {
    HDate h;
    hdate_from_gdate(&h, day, month, year);
    return h;
}

LiturgicalInsertions HebrewCalendarEngine::getInsertions(const HDate& hdate) const {
    LiturgicalInsertions ins = {};

    // 1. Rosh Chodesh
    // Day 1 of any month, or Day 30 of previous month
    ins.roshChodesh = (hdate.hd_day == 1 || hdate.hd_day == 30);

    // 2. Mashiv HaRuach vs Morid HaTal
    // Starts at Musaf of Shemini Atzeret (Tishrei 22) through Musaf of 1st day Pesach (Nisan 15)
    bool isWinterRain = false;
    if (hdate.hd_mon == 1) { // Tishrei
        if (hdate.hd_day >= 22) isWinterRain = true;
    } else if (hdate.hd_mon == 2 || hdate.hd_mon == 3 || hdate.hd_mon == 4 || 
               hdate.hd_mon == 5 || hdate.hd_mon == 6 || hdate.hd_mon == 13 || hdate.hd_mon == 14) {
        // Cheshvan, Kislev, Tevet, Shevat, Adar (or Adar I/II)
        isWinterRain = true;
    } else if (hdate.hd_mon == 7) { // Nisan
        if (hdate.hd_day < 15) isWinterRain = true;
    }
    ins.mashivHaRuach = isWinterRain;
    ins.moridHaTal = !isWinterRain;

    // 3. Tal UMatar / Barech Aleinu
    if (location_.isIsrael) {
        // In Israel: from 7 Cheshvan until Pesach (15 Nisan)
        if (hdate.hd_mon == 2 && hdate.hd_day >= 7) {
            ins.talUMatar = true;
        } else if (hdate.hd_mon >= 3 && hdate.hd_mon <= 6) {
            ins.talUMatar = true;
        } else if (hdate.hd_mon >= 13 && hdate.hd_mon <= 14) { // Adar I/II
            ins.talUMatar = true;
        } else if (hdate.hd_mon == 7 && hdate.hd_day < 15) {
            ins.talUMatar = true;
        }
    } else {
        // Diaspora: from approx Dec 4 (or Dec 5 before leap year) until Pesach
        // Simplified check using Gregorian calendar:
        bool afterDec4 = (hdate.gd_mon == 12 && hdate.gd_day >= 4);
        bool beforePesach = (hdate.hd_mon < 7 || (hdate.hd_mon == 7 && hdate.hd_day < 15));
        if (afterDec4 || (hdate.gd_mon >= 1 && beforePesach)) {
            ins.talUMatar = true;
        }
    }
    ins.barechAleinu = ins.talUMatar;

    // 4. Chanukah: 25 Kislev for 8 days
    if (hdate.hd_mon == 3 && hdate.hd_day >= 25) {
        ins.alHaNissimChanukah = true;
        ins.holidayName = "Jánuca";
    } else if (hdate.hd_mon == 4) { // Tevet
        int kislevLen = (hdate.hd_size_of_year % 10 >= 4) ? 30 : 29;
        int chanukahEndInTevet = (kislevLen == 30) ? 2 : 3;
        if (hdate.hd_day <= chanukahEndInTevet) {
            ins.alHaNissimChanukah = true;
            ins.holidayName = "Jánuca";
        }
    }

    // 5. Purim: 14 Adar (or 14 Adar II in leap year), Shushan Purim on 15
    bool isLeap = hdate_is_leap_year(hdate.hd_year);
    int purimMonth = isLeap ? 14 : 6;
    if (hdate.hd_mon == purimMonth && (hdate.hd_day == 14 || hdate.hd_day == 15)) {
        ins.alHaNissimPurim = true;
        ins.holidayName = (hdate.hd_day == 14) ? "Purim" : "Shushán Purim";
    }

    // 6. Yaaleh VeYavo: Rosh Chodesh, Shalosh Regalim, Rosh Hashanah, Yom Kippur
    if (ins.roshChodesh) {
        ins.yaalehVeYavo = true;
        if (ins.holidayName.empty()) ins.holidayName = "Rosh Jódesh";
    }
    if (hdate.hd_mon == 1) { // Tishrei
        if (hdate.hd_day == 1 || hdate.hd_day == 2) {
            ins.yaalehVeYavo = true;
            ins.holidayName = "Rosh Hashaná";
        } else if (hdate.hd_day == 10) {
            ins.yaalehVeYavo = true;
            ins.holidayName = "Yom Kipur";
        } else if (hdate.hd_day >= 15 && hdate.hd_day <= 21) {
            ins.yaalehVeYavo = true;
            ins.holidayName = (hdate.hd_day == 15) ? "Sucot" : "Jol HaMoed Sucot";
        } else if (hdate.hd_day == 22 || (!location_.isIsrael && hdate.hd_day == 23)) {
            ins.yaalehVeYavo = true;
            ins.holidayName = "Sheminí Atzéret / Simjat Torá";
        }
    } else if (hdate.hd_mon == 7) { // Nisan
        if (hdate.hd_day >= 15 && hdate.hd_day <= (location_.isIsrael ? 21 : 22)) {
            ins.yaalehVeYavo = true;
            ins.holidayName = (hdate.hd_day == 15 || hdate.hd_day == 21 || (!location_.isIsrael && (hdate.hd_day == 16 || hdate.hd_day == 22))) ? "Pésaj" : "Jol HaMoed Pésaj";
        }
    } else if (hdate.hd_mon == 9) { // Sivan
        if (hdate.hd_day == 6 || (!location_.isIsrael && hdate.hd_day == 7)) {
            ins.yaalehVeYavo = true;
            ins.holidayName = "Shavuot";
        }
    }

    // 7. Aseret Yemei Teshuvah: 1 to 10 Tishrei
    if (hdate.hd_mon == 1 && hdate.hd_day <= 10) {
        ins.aseretYemeiTeshuvah = true;
    }

    // 8. Tachanun Omissions
    if (hdate.hd_dw == 7) { // Shabbat
        ins.tachanunOmitted = true;
    } else if (ins.roshChodesh || ins.alHaNissimChanukah || ins.alHaNissimPurim || ins.yaalehVeYavo) {
        ins.tachanunOmitted = true;
    } else if (hdate.hd_mon == 7) { // Entire month of Nisan
        ins.tachanunOmitted = true;
    } else if (hdate.hd_mon == 8 && hdate.hd_day == 18) { // Lag BaOmer
        ins.tachanunOmitted = true;
        ins.holidayName = "Lag BaÓmer";
    } else if (hdate.hd_mon == 9 && hdate.hd_day <= 12) { // Sivan until Isru Chag
        ins.tachanunOmitted = true;
    } else if (hdate.hd_mon == 11 && (hdate.hd_day == 9 || hdate.hd_day == 15)) { // 9 Av & 15 Av
        ins.tachanunOmitted = true;
    } else if (hdate.hd_mon == 12 && hdate.hd_day == 29) { // Erev Rosh Hashanah
        ins.tachanunOmitted = true;
    } else if (hdate.hd_mon == 1 && hdate.hd_day == 9) { // Erev Yom Kippur
        ins.tachanunOmitted = true;
    } else if (hdate.hd_mon == 1 && hdate.hd_day >= 11) { // 11 Tishrei until end of Tishrei
        ins.tachanunOmitted = true;
    } else if (hdate.hd_mon == 5 && hdate.hd_day == 15) { // Tu B'Shvat
        ins.tachanunOmitted = true;
        ins.holidayName = "Tu Bishvat";
    }

    // 9. Sfirat HaOmer
    ins.omerDay = hdate_get_omer_day(&hdate);

    return ins;
}

static int toLocalSeconds(int utcSeconds, double tzHours) {
    if (utcSeconds < 0) return -1;
    int tzSec = (int)(tzHours * 3600.0);
    int local = (utcSeconds + tzSec) % 86400;
    if (local < 0) local += 86400;
    return local;
}

ZmanimDay HebrewCalendarEngine::computeZmanim(int day, int month, int year) const {
    ZmanimDay z = {};

    int srUtc = 0, ssUtc = 0;
    int alotUtc = 0, alotSsUtc = 0;
    int mishUtc = 0, mishSsUtc = 0;
    int tzeitUtc = 0, tzeitSsUtc = 0;

    // Sunrise / Sunset: 90.8333 degrees (accounting for 34 arcmin refraction + 16 arcmin semi-diameter)
    hdate_solar_times(day, month, year, location_.latitude, location_.longitude, 90.8333, &srUtc, &ssUtc);

    // Alot HaShachar (Dawn): 16.1 degrees below horizon = 106.1 degrees zenith
    hdate_solar_times(day, month, year, location_.latitude, location_.longitude, 106.1, &alotUtc, &alotSsUtc);

    // Misheyakir: 10.2 degrees below horizon = 100.2 degrees zenith
    hdate_solar_times(day, month, year, location_.latitude, location_.longitude, 100.2, &mishUtc, &mishSsUtc);

    // Tzeit HaKochavim (Nightfall): 8.5 degrees below horizon = 98.5 degrees zenith
    hdate_solar_times(day, month, year, location_.latitude, location_.longitude, 98.5, &tzeitUtc, &tzeitSsUtc);

    z.sunriseSec = toLocalSeconds(srUtc, location_.timeZoneOffsetHours);
    z.sunsetSec = toLocalSeconds(ssUtc, location_.timeZoneOffsetHours);
    z.alotHashacharSec = toLocalSeconds(alotUtc, location_.timeZoneOffsetHours);
    z.misheyakirSec = toLocalSeconds(mishUtc, location_.timeZoneOffsetHours);
    z.tzeitHaKochavimSec = toLocalSeconds(tzeitSsUtc, location_.timeZoneOffsetHours);

    // Halachic hours (Shaot Zmaniyot)
    int dayLength = z.sunsetSec - z.sunriseSec;
    if (dayLength < 0) dayLength += 86400;
    z.shaahZmanitSec = dayLength / 12.0;

    // Sof Zman Shema Gra: Sunrise + 3 shaot zmaniyot
    z.sofZmanShemaGraSec = z.sunriseSec + (int)(3.0 * z.shaahZmanitSec);

    // Sof Zman Shema MGA: (Alot to Tzeit / 12) * 3
    int mgaLength = z.tzeitHaKochavimSec - z.alotHashacharSec;
    if (mgaLength < 0) mgaLength += 86400;
    double shaahMga = mgaLength / 12.0;
    z.sofZmanShemaMgaSec = z.alotHashacharSec + (int)(3.0 * shaahMga);

    // Sof Zman Tefilah Gra: Sunrise + 4 shaot zmaniyot
    z.sofZmanTefilahGraSec = z.sunriseSec + (int)(4.0 * z.shaahZmanitSec);

    // Chatzot Hayom: Sunrise + 6 shaot zmaniyot
    z.chatzotSec = z.sunriseSec + (int)(6.0 * z.shaahZmanitSec);

    // Mincha Gedola: Chatzot + 30 minutes
    z.minchaGedolaSec = z.chatzotSec + 1800;

    // Mincha Ketana: Sunrise + 9.5 shaot zmaniyot
    z.minchaKetanaSec = z.sunriseSec + (int)(9.5 * z.shaahZmanitSec);

    // Plag HaMincha: Sunrise + 10.75 shaot zmaniyot
    z.plagHaMinchaSec = z.sunriseSec + (int)(10.75 * z.shaahZmanitSec);

    // Candle lighting: Sunset - 18 minutes
    z.candleLightingSec = z.sunsetSec - (18 * 60);

    return z;
}

RecommendedPrayer HebrewCalendarEngine::recommendPrayer(const HDate& hdate, const ZmanimDay& zmanim, int currentSeconds) const {
    // Friday Night
    if (hdate.hd_dw == 6) { // Friday
        if (currentSeconds >= zmanim.candleLightingSec) {
            return RecommendedPrayer::KiddushFridayNight;
        }
    }

    // Shabbat Day
    if (hdate.hd_dw == 7) { // Saturday / Shabbat
        if (currentSeconds < zmanim.sofZmanTefilahGraSec + 3600) {
            return RecommendedPrayer::Shacharit;
        }
        if (currentSeconds >= zmanim.chatzotSec && currentSeconds < zmanim.minchaGedolaSec + 1800) {
            return RecommendedPrayer::KiddushShabbatDay;
        }
        if (currentSeconds >= zmanim.minchaGedolaSec && currentSeconds < zmanim.sunsetSec) {
            return RecommendedPrayer::Mincha;
        }
        if (currentSeconds >= zmanim.tzeitHaKochavimSec) {
            return RecommendedPrayer::Havdalah;
        }
    }

    // Standard Weekday
    if (currentSeconds < zmanim.sofZmanTefilahGraSec + 3600) {
        return RecommendedPrayer::Shacharit;
    }
    if (currentSeconds >= zmanim.minchaGedolaSec && currentSeconds <= zmanim.sunsetSec + 900) {
        return RecommendedPrayer::Mincha;
    }
    if (currentSeconds > zmanim.sunsetSec + 900 || currentSeconds < zmanim.alotHashacharSec) {
        return RecommendedPrayer::Arvit;
    }

    return RecommendedPrayer::None;
}

std::string HebrewCalendarEngine::formatTime(int secondsFromMidnight) {
    if (secondsFromMidnight < 0) return "--:--";
    int h = (secondsFromMidnight / 3600) % 24;
    int m = (secondsFromMidnight % 3600) / 60;
    char buf[16];
    std::snprintf(buf, sizeof(buf), "%02d:%02d", h, m);
    return std::string(buf);
}

std::string HebrewCalendarEngine::getHebrewMonthName(int hebrewMonth, bool isLeapYear) {
    static const char* regular[] = {
        "", "תשרי", "חשון", "כסלו", "טבת", "שבט", "אדר",
        "ניסן", "אייר", "סיוון", "תמוז", "אב", "אלול"
    };
    if (!isLeapYear && hebrewMonth >= 1 && hebrewMonth <= 12) {
        return regular[hebrewMonth];
    }
    if (isLeapYear) {
        if (hebrewMonth >= 1 && hebrewMonth <= 5) return regular[hebrewMonth];
        if (hebrewMonth == 6 || hebrewMonth == 13) return "אדר א׳";
        if (hebrewMonth == 14) return "אדר ב׳";
        if (hebrewMonth >= 7 && hebrewMonth <= 12) return regular[hebrewMonth];
    }
    return "";
}

std::string HebrewCalendarEngine::getSpanishMonthName(int hebrewMonth, bool isLeapYear) {
    static const char* regular[] = {
        "", "Tishrei", "Jeshván", "Kislev", "Tevet", "Shevat", "Adar",
        "Nisán", "Iyar", "Siván", "Tamuz", "Av", "Elul"
    };
    if (!isLeapYear && hebrewMonth >= 1 && hebrewMonth <= 12) {
        return regular[hebrewMonth];
    }
    if (isLeapYear) {
        if (hebrewMonth >= 1 && hebrewMonth <= 5) return regular[hebrewMonth];
        if (hebrewMonth == 6 || hebrewMonth == 13) return "Adar I";
        if (hebrewMonth == 14) return "Adar II";
        if (hebrewMonth >= 7 && hebrewMonth <= 12) return regular[hebrewMonth];
    }
    return "";
}

} // namespace siddur
