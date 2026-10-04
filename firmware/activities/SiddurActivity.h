/**
 * firmware/activities/SiddurActivity.h
 * Top-level liturgical reader activity for embedded e-ink Siddur.
 * Integrates HebrewCalendarEngine, time-aware prayer recommendations,
 * bilingual text rendering (Hebrew + Spanish), and verse-tap interactive modals.
 */

#pragma once

#include <string>
#include <vector>
#include <memory>
#include "VerseModalActivity.h"
#include "../zmanim/HebrewCalendarEngine.h"
#include "../zmanim/LocationProfile.h"

namespace siddur {

struct LiturgicalVerse {
    std::string verseId;
    std::string hebrew;
    std::string spanishInterlinear;
    std::string spanishFull;
    std::string transliteration;
    std::string notes;
    std::string sourceRef;
};

struct LiturgicalSection {
    std::string titleHebrew;
    std::string titleSpanish;
    std::vector<LiturgicalVerse> verses;
};

struct VerseTouchRegion {
    int x;
    int y;
    int width;
    int height;
    size_t verseIndex;
};

class SiddurActivityPresenter {
public:
    SiddurActivityPresenter(const HebrewCalendarEngine& engine, const CityPreset& preset);

    // Date & Time Updates
    void updateDateTime(int day, int month, int year, int currentSecondsFromMidnight);

    // Prayer Selection
    void loadPrayer(const std::string& prayerName, const std::vector<LiturgicalSection>& sections);
    void autoSelectRecommendedPrayer();

    // Pagination
    int getCurrentPage() const { return currentPage_; }
    int getTotalPages() const { return totalPages_; }
    bool nextPage();
    bool previousPage();

    // Layout on 800x480 screen
    void layout(int screenWidth = 800, int screenHeight = 480);

    // Touch interaction
    bool handleTap(int touchX, int touchY, VerseModalContent& outModalContent) const;

    // Getters for UI display
    const std::string& getPrayerTitle() const { return activePrayerTitle_; }
    const std::string& getHebrewDateString() const { return hebrewDateString_; }
    const std::string& getHolidayString() const { return holidayString_; }
    const std::string& getInsertionsString() const { return insertionsString_; }
    const std::string& getRecommendedPrayerString() const { return recommendedPrayerString_; }
    const std::string& getLocationName() const { return activePreset_.cityName; }

    const std::vector<VerseTouchRegion>& getTouchRegions() const { return touchRegions_; }
    const std::vector<LiturgicalSection>& getSections() const { return sections_; }

private:
    HebrewCalendarEngine engine_;
    CityPreset activePreset_;
    int gDay_ = 4;
    int gMonth_ = 10;
    int gYear_ = 2026;
    int currentSeconds_ = 34440; // 09:34 AM

    HDate currentHDate_{};
    ZmanimDay currentZmanim_{};
    LiturgicalInsertions currentInsertions_{};
    RecommendedPrayer currentRecommendation_ = RecommendedPrayer::None;

    std::string activePrayerTitle_ = "Shajarit";
    std::string hebrewDateString_;
    std::string holidayString_;
    std::string insertionsString_;
    std::string recommendedPrayerString_;

    std::vector<LiturgicalSection> sections_;
    std::vector<VerseTouchRegion> touchRegions_;

    int currentPage_ = 0;
    int totalPages_ = 1;
    int versesPerPage_ = 4;
};

} // namespace siddur
