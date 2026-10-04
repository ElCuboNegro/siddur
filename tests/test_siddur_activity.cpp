/**
 * tests/test_siddur_activity.cpp
 * Verification suite for SiddurActivityPresenter and VerseModalPresenter.
 */

#include "../firmware/activities/SiddurActivity.h"
#include "../firmware/activities/VerseModalActivity.h"
#include <iostream>
#include <cassert>

using namespace siddur;

void testSiddurActivityWithUserLocale() {
    std::cout << "[TEST] Running testSiddurActivityWithUserLocale (Bogotá, Colombia)...\n";

    HebrewCalendarEngine engine;
    CityPreset bogota = LocationProfileManager::getDefaultPreset();
    assert(bogota.cityName == "Bogotá");
    assert(bogota.country == "Colombia");
    assert(bogota.location.isIsrael == false);

    SiddurActivityPresenter presenter(engine, bogota);

    // Verify header status for today 2026-10-04 at 09:34 AM
    std::cout << "  Location: " << presenter.getLocationName() << "\n";
    std::cout << "  Hebrew Date: " << presenter.getHebrewDateString() << "\n";
    std::cout << "  Holiday: " << presenter.getHolidayString() << "\n";
    std::cout << "  Insertions: " << presenter.getInsertionsString() << "\n";
    std::cout << "  Recommendation: " << presenter.getRecommendedPrayerString() << "\n";

    assert(presenter.getLocationName() == "Bogotá");
    assert(presenter.getRecommendedPrayerString() == "Shajarit (Rezo Matutino)");

    // Create sample prayer sections (Shema Yisrael)
    std::vector<LiturgicalSection> sections;
    LiturgicalSection sec1;
    sec1.titleHebrew = "קְרִיאַת שְׁמַע";
    sec1.titleSpanish = "Lectura del Shemá";

    LiturgicalVerse v1;
    v1.verseId = "shema_1";
    v1.hebrew = "שְׁמַע יִשְׂרָאֵל יְהוָה אֱלֹהֵינוּ יְהוָה אֶחָד:";
    v1.spanishInterlinear = "Escucha | Israel | HaShem | nuestro Dios | HaShem | Uno es";
    v1.spanishFull = "Oye, Israel: el Eterno es nuestro Dios, el Eterno es Uno.";
    v1.transliteration = "Shemá Yisrael Adonai Eloheinu Adonai Ejad.";
    v1.notes = "Declaración central monoteísta del pueblo judío. Concentración obligatoria (kavaná).";
    v1.sourceRef = "Deuteronomio 6:4";
    sec1.verses.push_back(v1);

    LiturgicalVerse v2;
    v2.verseId = "shema_2";
    v2.hebrew = "בָּרוּךְ שֵׁם כְּבוֹד מַלְכוּתוֹ לְעוֹלָם וָעֶד:";
    v2.spanishInterlinear = "Bendito | nombre de | gloria de | Su reino | por siempre | y jamás";
    v2.spanishFull = "Bendito sea el Nombre de la gloria de Su reino por siempre jamás.";
    v2.transliteration = "Baruj shem kevod maljuto leolam vaed.";
    v2.notes = "Se pronuncia en susurro, excepto en Yom Kipur cuando se proclama en voz alta.";
    v2.sourceRef = "Talmud Pesajim 56a";
    sec1.verses.push_back(v2);

    sections.push_back(sec1);

    presenter.loadPrayer("Kriyat Shema", sections);
    assert(presenter.getCurrentPage() == 0);
    assert(presenter.getTotalPages() == 1);

    // Verify layout on 800x480 screen
    const auto& regions = presenter.getTouchRegions();
    std::cout << "  Configured touch regions on 800x480 screen: " << regions.size() << "\n";
    assert(regions.size() == 2);

    // Test tap on Verse 1 (x: 200, y: 150)
    VerseModalContent modalContent;
    bool tappedV1 = presenter.handleTap(200, 150, modalContent);
    assert(tappedV1 == true);
    assert(modalContent.verseId == "shema_1");
    assert(modalContent.sourceReference == "Deuteronomio 6:4");
    std::cout << "  ✓ Tap on verse 1 detected: \"" << modalContent.hebrew << "\"\n";
    std::cout << "    Spanish: \"" << modalContent.spanishFull << "\"\n";

    // Test VerseModalPresenter with the tapped verse
    VerseModalPresenter modalPresenter(modalContent);
    modalPresenter.layout(760, 400, 24);
    std::cout << "  Modal pages: " << modalPresenter.getTotalPages() << "\n";
    assert(modalPresenter.getTotalPages() >= 1);
    assert(!modalPresenter.getFormattedLines().empty());

    // Test miss tap outside bounds (x: 5, y: 5)
    VerseModalContent emptyContent;
    bool missed = presenter.handleTap(5, 5, emptyContent);
    assert(missed == false);

    // Test Afternoon transition in Bogotá: 15:00 PM
    presenter.updateDateTime(4, 10, 2026, 15 * 3600);
    std::cout << "  At 15:00 PM in Bogotá, Recommendation: " << presenter.getRecommendedPrayerString() << "\n";
    assert(presenter.getRecommendedPrayerString() == "Minjá (Rezo Vespertino)");

    // Test Evening transition in Bogotá: 20:00 PM
    presenter.updateDateTime(4, 10, 2026, 20 * 3600);
    std::cout << "  At 20:00 PM in Bogotá, Recommendation: " << presenter.getRecommendedPrayerString() << "\n";
    assert(presenter.getRecommendedPrayerString() == "Arvit (Rezo Nocturno)");

    std::cout << "  ✓ testSiddurActivityWithUserLocale passed completely.\n";
}

int main() {
    std::cout << "=== Running SiddurActivity & VerseModal Unit Tests ===\n";
    testSiddurActivityWithUserLocale();
    std::cout << "=== ALL SIDDUR ACTIVITY TESTS PASSED! ===\n";
    return 0;
}
