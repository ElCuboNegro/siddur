/**
 * firmware/activities/SiddurActivity.cpp
 * Implementation of SiddurActivityPresenter.
 */

#include "SiddurActivity.h"
#include <sstream>
#include <algorithm>

namespace siddur {

SiddurActivityPresenter::SiddurActivityPresenter(const HebrewCalendarEngine& engine, const CityPreset& preset)
    : engine_(engine), activePreset_(preset) {
    engine_.setLocation(activePreset_.location);
    updateDateTime(4, 10, 2026, 9 * 3600 + 34 * 60); // Default to current session timestamp
}

void SiddurActivityPresenter::updateDateTime(int day, int month, int year, int currentSecondsFromMidnight) {
    gDay_ = day;
    gMonth_ = month;
    gYear_ = year;
    currentSeconds_ = currentSecondsFromMidnight;

    currentHDate_ = engine_.computeDate(day, month, year);
    currentZmanim_ = engine_.computeZmanim(day, month, year);
    currentInsertions_ = engine_.getInsertions(currentHDate_);
    currentRecommendation_ = engine_.recommendPrayer(currentHDate_, currentZmanim_, currentSeconds_);

    // 1. Format Hebrew Date
    std::ostringstream ssDate;
    ssDate << currentHDate_.hd_day << " de "
           << HebrewCalendarEngine::getSpanishMonthName(currentHDate_.hd_mon, hdate_is_leap_year(currentHDate_.hd_year))
           << " de " << currentHDate_.hd_year;
    hebrewDateString_ = ssDate.str();

    // 2. Format Holiday / Day status
    if (!currentInsertions_.holidayName.empty()) {
        holidayString_ = currentInsertions_.holidayName;
    } else if (currentHDate_.hd_dw == 7) {
        holidayString_ = "Shabat Kodesh";
    } else if (currentInsertions_.roshChodesh) {
        holidayString_ = "Rosh Jódesh";
    } else {
        holidayString_ = "Día Laboral";
    }

    // 3. Format Insertions
    std::ostringstream ssIns;
    if (currentInsertions_.mashivHaRuach) {
        ssIns << "Mashiv HaRúaj";
    } else if (currentInsertions_.moridHaTal) {
        ssIns << "Morid HaTal";
    }

    if (currentInsertions_.talUMatar) {
        ssIns << " | Barej Aleinu (Tal UMatar)";
    } else {
        ssIns << " | Barejenu";
    }

    if (currentInsertions_.tachanunOmitted) {
        ssIns << " | Sin Tajanún";
    } else {
        ssIns << " | Con Tajanún";
    }
    insertionsString_ = ssIns.str();

    // 4. Recommendation
    switch (currentRecommendation_) {
        case RecommendedPrayer::Shacharit:
            recommendedPrayerString_ = "Shajarit (Rezo Matutino)";
            break;
        case RecommendedPrayer::Mincha:
            recommendedPrayerString_ = "Minjá (Rezo Vespertino)";
            break;
        case RecommendedPrayer::Arvit:
            recommendedPrayerString_ = "Arvit (Rezo Nocturno)";
            break;
        case RecommendedPrayer::KiddushFridayNight:
            recommendedPrayerString_ = "Kidush Noche de Shabat";
            break;
        case RecommendedPrayer::KiddushShabbatDay:
            recommendedPrayerString_ = "Kidush Día de Shabat";
            break;
        case RecommendedPrayer::Havdalah:
            recommendedPrayerString_ = "Havdalá";
            break;
        case RecommendedPrayer::BirkatHaMazon:
            recommendedPrayerString_ = "Birkát HaMazón";
            break;
        default:
            recommendedPrayerString_ = "Lectura Libre";
            break;
    }
}

void SiddurActivityPresenter::loadPrayer(const std::string& prayerName, const std::vector<LiturgicalSection>& sections) {
    activePrayerTitle_ = prayerName;
    sections_ = sections;
    currentPage_ = 0;

    size_t totalVerses = 0;
    for (const auto& sec : sections_) {
        totalVerses += sec.verses.size();
    }

    if (totalVerses == 0) {
        totalPages_ = 1;
    } else {
        totalPages_ = static_cast<int>((totalVerses + versesPerPage_ - 1) / versesPerPage_);
    }

    layout(800, 480);
}

void SiddurActivityPresenter::autoSelectRecommendedPrayer() {
    switch (currentRecommendation_) {
        case RecommendedPrayer::Shacharit:
            activePrayerTitle_ = "Shajarit";
            break;
        case RecommendedPrayer::Mincha:
            activePrayerTitle_ = "Minjá";
            break;
        case RecommendedPrayer::Arvit:
            activePrayerTitle_ = "Arvit";
            break;
        case RecommendedPrayer::KiddushFridayNight:
        case RecommendedPrayer::KiddushShabbatDay:
            activePrayerTitle_ = "Kidush de Shabat";
            break;
        case RecommendedPrayer::BirkatHaMazon:
            activePrayerTitle_ = "Birkát HaMazón";
            break;
        default:
            activePrayerTitle_ = "Sidur Diario";
            break;
    }
}

bool SiddurActivityPresenter::nextPage() {
    if (currentPage_ + 1 < totalPages_) {
        currentPage_++;
        layout(800, 480);
        return true;
    }
    return false;
}

bool SiddurActivityPresenter::previousPage() {
    if (currentPage_ > 0) {
        currentPage_--;
        layout(800, 480);
        return true;
    }
    return false;
}

void SiddurActivityPresenter::layout(int screenWidth, int screenHeight) {
    touchRegions_.clear();

    // Flatten verses from sections
    std::vector<const LiturgicalVerse*> flatVerses;
    for (const auto& sec : sections_) {
        for (const auto& v : sec.verses) {
            flatVerses.push_back(&v);
        }
    }

    size_t startIdx = static_cast<size_t>(currentPage_ * versesPerPage_);
    size_t endIdx = std::min(flatVerses.size(), startIdx + static_cast<size_t>(versesPerPage_));

    // Usable area: 800x480
    // Header occupies Y: 0..60
    // Footer occupies Y: 440..480
    // Content body: Y: 60..440 (height = 380px)
    int bodyY = 65;
    int bodyHeight = 370;
    int itemsOnPage = static_cast<int>(endIdx - startIdx);
    if (itemsOnPage <= 0) return;

    int slotHeight = bodyHeight / itemsOnPage;

    for (size_t i = startIdx; i < endIdx; ++i) {
        int idxOnPage = static_cast<int>(i - startIdx);
        VerseTouchRegion region;
        region.x = 20;
        region.y = bodyY + idxOnPage * slotHeight;
        region.width = screenWidth - 40; // 760px
        region.height = slotHeight - 8;
        region.verseIndex = i;
        touchRegions_.push_back(region);
    }
}

bool SiddurActivityPresenter::handleTap(int touchX, int touchY, VerseModalContent& outModalContent) const {
    std::vector<const LiturgicalVerse*> flatVerses;
    for (const auto& sec : sections_) {
        for (const auto& v : sec.verses) {
            flatVerses.push_back(&v);
        }
    }

    for (const auto& region : touchRegions_) {
        if (touchX >= region.x && touchX <= (region.x + region.width) &&
            touchY >= region.y && touchY <= (region.y + region.height)) {
            if (region.verseIndex < flatVerses.size()) {
                const auto* v = flatVerses[region.verseIndex];
                outModalContent.verseId = v->verseId;
                outModalContent.hebrew = v->hebrew;
                outModalContent.spanishInterlinear = v->spanishInterlinear;
                outModalContent.spanishFull = v->spanishFull;
                outModalContent.transliteration = v->transliteration;
                outModalContent.notes = v->notes;
                outModalContent.sourceReference = v->sourceRef;
                return true;
            }
        }
    }
    return false;
}

} // namespace siddur
