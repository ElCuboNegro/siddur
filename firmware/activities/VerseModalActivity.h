/**
 * firmware/activities/VerseModalActivity.h
 * Interactive modal activity displaying in-depth translation, transliteration,
 * and halachic/kabbalistic commentary when a liturgical verse is tapped on the e-ink screen.
 */

#pragma once

#include <string>
#include <vector>
#include <cstdint>

namespace siddur {

struct VerseModalContent {
    std::string verseId;
    std::string hebrew;
    std::string spanishInterlinear;
    std::string spanishFull;
    std::string transliteration;
    std::string notes;
    std::string sourceReference;
};

/**
 * VerseModalPresenter manages the text wrapping and pagination for the verse modal dialog.
 * Structured to run on CrossPoint Reader's GfxRenderer.
 */
class VerseModalPresenter {
public:
    explicit VerseModalPresenter(const VerseModalContent& content);

    const VerseModalContent& getContent() const { return content_; }

    int getCurrentPage() const { return currentPage_; }
    int getTotalPages() const { return totalPages_; }

    bool nextPage();
    bool previousPage();

    // Prepare line layout given screen width and line heights
    void layout(int maxWidth, int maxHeight, int lineHeight);

    const std::vector<std::string>& getFormattedLines() const { return formattedLines_; }

private:
    VerseModalContent content_;
    int currentPage_ = 0;
    int totalPages_ = 1;
    int linesPerPage_ = 8;
    std::vector<std::string> formattedLines_;
};

} // namespace siddur
