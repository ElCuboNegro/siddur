/**
 * tests/test_zmanim_engine.cpp
 * Unit test and verification suite for HebrewCalendarEngine and libhdate_core.
 */

#include "../firmware/zmanim/HebrewCalendarEngine.h"
#include <iostream>
#include <cassert>

using namespace siddur;

void testDateConversion() {
    std::cout << "[TEST] Running testDateConversion...\n";
    HebrewCalendarEngine engine;

    // Test Rosh Hashanah 5785: October 3, 2024 -> 1 Tishrei 5785
    HDate h1 = engine.computeDate(3, 10, 2024);
    std::cout << "  2024-10-03 -> Hebrew: " << h1.hd_day << " " 
              << HebrewCalendarEngine::getSpanishMonthName(h1.hd_mon, hdate_is_leap_year(h1.hd_year))
              << " " << h1.hd_year << " (DOW: " << h1.hd_dw << ")\n";
    assert(h1.hd_day == 1);
    assert(h1.hd_mon == 1); // Tishrei
    assert(h1.hd_year == 5785);
    assert(h1.hd_dw == 5);  // Thursday

    // Test Pesach 5785: April 13, 2025 -> 15 Nisan 5785
    HDate h2 = engine.computeDate(13, 4, 2025);
    std::cout << "  2025-04-13 -> Hebrew: " << h2.hd_day << " " 
              << HebrewCalendarEngine::getSpanishMonthName(h2.hd_mon, hdate_is_leap_year(h2.hd_year))
              << " " << h2.hd_year << "\n";
    assert(h2.hd_day == 15);
    assert(h2.hd_mon == 7); // Nisan
    assert(h2.hd_year == 5785);

    std::cout << "  ✓ Date conversion assertions passed.\n";
}

void testLiturgicalInsertions() {
    std::cout << "[TEST] Running testLiturgicalInsertions...\n";
    HebrewCalendarEngine engine;

    // 1. Chanukah test: 25 Kislev 5785 -> Dec 26, 2024
    HDate hChanukah = engine.computeDate(26, 12, 2024);
    LiturgicalInsertions insChanukah = engine.getInsertions(hChanukah);
    std::cout << "  Chanukah (25 Kislev): alHaNissim=" << insChanukah.alHaNissimChanukah
              << ", tachanunOmitted=" << insChanukah.tachanunOmitted << "\n";
    assert(insChanukah.alHaNissimChanukah == true);
    assert(insChanukah.tachanunOmitted == true);

    // 2. Pesach test: 15 Nisan 5785 -> April 13, 2025
    HDate hPesach = engine.computeDate(13, 4, 2025);
    LiturgicalInsertions insPesach = engine.getInsertions(hPesach);
    std::cout << "  Pesach (15 Nisan): yaalehVeYavo=" << insPesach.yaalehVeYavo
              << ", tachanunOmitted=" << insPesach.tachanunOmitted
              << ", moridHaTal=" << insPesach.moridHaTal << "\n";
    assert(insPesach.yaalehVeYavo == true);
    assert(insPesach.tachanunOmitted == true);

    // 3. Winter rain test (Mashiv HaRuach in Tevet)
    HDate hTevet = engine.computeDate(10, 1, 2025);
    LiturgicalInsertions insTevet = engine.getInsertions(hTevet);
    assert(insTevet.mashivHaRuach == true);
    assert(insTevet.moridHaTal == false);

    // 4. Omer count on 20 Nisan (Day 5 of Omer)
    HDate hOmer = engine.computeDate(18, 4, 2025); // 20 Nisan
    LiturgicalInsertions insOmer = engine.getInsertions(hOmer);
    std::cout << "  Omer count for 20 Nisan: " << insOmer.omerDay << " (expected 5)\n";
    assert(insOmer.omerDay == 5);

    std::cout << "  ✓ Liturgical insertions assertions passed.\n";
}

void testZmanimCalculations() {
    std::cout << "[TEST] Running testZmanimCalculations...\n";
    HebrewCalendarEngine engine;

    // Jerusalem coordinates
    GeoLocation jlm = { 31.7767, 35.2345, 2.0, true };
    engine.setLocation(jlm);

    // Compute for 2026-10-04
    ZmanimDay z = engine.computeZmanim(4, 10, 2026);

    std::cout << "  Jerusalem Zmanim for 2026-10-04:\n";
    std::cout << "    Alot HaShachar:     " << HebrewCalendarEngine::formatTime(z.alotHashacharSec) << "\n";
    std::cout << "    Misheyakir:         " << HebrewCalendarEngine::formatTime(z.misheyakirSec) << "\n";
    std::cout << "    Sunrise (Hanetz):   " << HebrewCalendarEngine::formatTime(z.sunriseSec) << "\n";
    std::cout << "    Sof Zman Shema Gra: " << HebrewCalendarEngine::formatTime(z.sofZmanShemaGraSec) << "\n";
    std::cout << "    Sof Zman Tefilah:   " << HebrewCalendarEngine::formatTime(z.sofZmanTefilahGraSec) << "\n";
    std::cout << "    Chatzot:            " << HebrewCalendarEngine::formatTime(z.chatzotSec) << "\n";
    std::cout << "    Mincha Gedola:      " << HebrewCalendarEngine::formatTime(z.minchaGedolaSec) << "\n";
    std::cout << "    Plag HaMincha:      " << HebrewCalendarEngine::formatTime(z.plagHaMinchaSec) << "\n";
    std::cout << "    Sunset (Shkia):     " << HebrewCalendarEngine::formatTime(z.sunsetSec) << "\n";
    std::cout << "    Tzeit HaKochavim:   " << HebrewCalendarEngine::formatTime(z.tzeitHaKochavimSec) << "\n";
    std::cout << "    Shaah Zmanit (min): " << (z.shaahZmanitSec / 60.0) << "\n";

    // Monotonicity assertions
    assert(z.alotHashacharSec < z.misheyakirSec);
    assert(z.misheyakirSec < z.sunriseSec);
    assert(z.sunriseSec < z.sofZmanShemaGraSec);
    assert(z.sofZmanShemaGraSec < z.sofZmanTefilahGraSec);
    assert(z.sofZmanTefilahGraSec < z.chatzotSec);
    assert(z.chatzotSec < z.minchaGedolaSec);
    assert(z.minchaGedolaSec < z.plagHaMinchaSec);
    assert(z.plagHaMinchaSec < z.sunsetSec);
    assert(z.sunsetSec < z.tzeitHaKochavimSec);

    // Prayer recommendation test
    HDate h = engine.computeDate(4, 10, 2026);
    // Morning time (07:30)
    RecommendedPrayer rMorning = engine.recommendPrayer(h, z, 7 * 3600 + 30 * 60);
    assert(rMorning == RecommendedPrayer::Shacharit);

    // Afternoon time (15:00)
    RecommendedPrayer rAfternoon = engine.recommendPrayer(h, z, 15 * 3600);
    assert(rAfternoon == RecommendedPrayer::Mincha);

    // Night time (20:00)
    RecommendedPrayer rNight = engine.recommendPrayer(h, z, 20 * 3600);
    assert(rNight == RecommendedPrayer::Arvit);

    std::cout << "  ✓ Zmanim calculations & recommendations assertions passed.\n";
}

void testUserLocationBogotaColombia() {
    std::cout << "[TEST] Running testUserLocationBogotaColombia (User Environment Awareness)...\n";
    HebrewCalendarEngine engine; // Defaults to Bogota, Colombia

    const GeoLocation& loc = engine.getLocation();
    std::cout << "  Default Location: Lat=" << loc.latitude << ", Lon=" << loc.longitude 
              << ", TZ=" << loc.timeZoneOffsetHours << ", isIsrael=" << loc.isIsrael << "\n";
    assert(loc.isIsrael == false);
    assert(loc.timeZoneOffsetHours == -5.0);

    // Compute for today: 2026-10-04 (User current local date)
    ZmanimDay z = engine.computeZmanim(4, 10, 2026);
    std::cout << "  Bogotá Zmanim for today (2026-10-04):\n";
    std::cout << "    Alot HaShachar:     " << HebrewCalendarEngine::formatTime(z.alotHashacharSec) << "\n";
    std::cout << "    Misheyakir:         " << HebrewCalendarEngine::formatTime(z.misheyakirSec) << "\n";
    std::cout << "    Sunrise (Hanetz):   " << HebrewCalendarEngine::formatTime(z.sunriseSec) << "\n";
    std::cout << "    Sof Zman Shema Gra: " << HebrewCalendarEngine::formatTime(z.sofZmanShemaGraSec) << "\n";
    std::cout << "    Sof Zman Tefilah:   " << HebrewCalendarEngine::formatTime(z.sofZmanTefilahGraSec) << "\n";
    std::cout << "    Chatzot:            " << HebrewCalendarEngine::formatTime(z.chatzotSec) << "\n";
    std::cout << "    Mincha Gedola:      " << HebrewCalendarEngine::formatTime(z.minchaGedolaSec) << "\n";
    std::cout << "    Sunset (Shkia):     " << HebrewCalendarEngine::formatTime(z.sunsetSec) << "\n";
    std::cout << "    Tzeit HaKochavim:   " << HebrewCalendarEngine::formatTime(z.tzeitHaKochavimSec) << "\n";

    // Monotonicity assertions
    assert(z.alotHashacharSec < z.sunriseSec);
    assert(z.sunriseSec < z.chatzotSec);
    assert(z.chatzotSec < z.sunsetSec);
    assert(z.sunsetSec < z.tzeitHaKochavimSec);

    // Astronomical reality check for Bogota (near equator ~4.7°N, UTC-5):
    // Sunrise should be around 05:40 - 05:55 local time
    int sunriseHour = z.sunriseSec / 3600;
    assert(sunriseHour >= 5 && sunriseHour <= 6);

    // Test recommendation for user's exact current local time: 09:34 AM
    HDate h = engine.computeDate(4, 10, 2026);
    int currentTimeSec = 9 * 3600 + 34 * 60; // 09:34:00
    RecommendedPrayer rec = engine.recommendPrayer(h, z, currentTimeSec);
    std::cout << "  At 09:34 AM in Bogotá, Recommended prayer is: ";
    if (rec == RecommendedPrayer::Shacharit) std::cout << "Shacharit (Correct!)\n";
    else std::cout << "Other\n";
    assert(rec == RecommendedPrayer::Shacharit);

    std::cout << "  ✓ Bogota, Colombia location & real-time assertions passed.\n";
}

void testDiasporaVsIsraelRules() {
    std::cout << "[TEST] Running testDiasporaVsIsraelRules (Tal UMatar & Diaspora customs)...\n";
    HebrewCalendarEngine engineIsrael;
    engineIsrael.setLocation({31.7767, 35.2345, 2.0, true}); // Jerusalem

    HebrewCalendarEngine engineDiaspora;
    engineDiaspora.setLocation({4.7110, -74.0721, -5.0, false}); // Bogota, Colombia

    // Test on 10 Cheshvan 5786 (November 1, 2025):
    // In Israel: Tal UMatar started on 7 Cheshvan -> TRUE
    // In Diaspora: Tal UMatar has NOT started yet (starts Dec 4) -> FALSE
    HDate hCheshvan10 = engineIsrael.computeDate(1, 11, 2025);
    
    LiturgicalInsertions insIsrael = engineIsrael.getInsertions(hCheshvan10);
    LiturgicalInsertions insDiaspora = engineDiaspora.getInsertions(hCheshvan10);

    std::cout << "  10 Cheshvan Tal UMatar check:\n";
    std::cout << "    Israel:   talUMatar=" << insIsrael.talUMatar << " (expected 1)\n";
    std::cout << "    Diaspora: talUMatar=" << insDiaspora.talUMatar << " (expected 0)\n";

    assert(insIsrael.talUMatar == true);
    assert(insDiaspora.talUMatar == false);

    // Test on 15 December 2025:
    // Both Israel and Diaspora must have talUMatar == true
    HDate hDec15 = engineIsrael.computeDate(15, 12, 2025);
    assert(engineIsrael.getInsertions(hDec15).talUMatar == true);
    assert(engineDiaspora.getInsertions(hDec15).talUMatar == true);

    std::cout << "  ✓ Diaspora vs Israel halachic distinctions passed.\n";
}

int main() {
    std::cout << "=== HebrewCalendarEngine & Zmanim Verification Test ===\n";
    testDateConversion();
    testLiturgicalInsertions();
    testZmanimCalculations();
    testUserLocationBogotaColombia();
    testDiasporaVsIsraelRules();
    std::cout << "=== ALL TESTS PASSED SUCCESSFULLY! ===\n";
    return 0;
}
