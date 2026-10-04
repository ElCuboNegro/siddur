/**
 * firmware/activities/VerseModalActivity.cpp
 * Implementation of VerseModalPresenter.
 */

#include "VerseModalActivity.h"
#include <algorithm>
#include <sstream>

namespace siddur {

VerseModalPresenter::VerseModalPresenter(const VerseModalContent& content)
    : content_(content) {}

bool VerseModalPresenter::nextPage() {
    if (currentPage_ + 1 < totalPages_) {
        currentPage_++;
        return true;
    }
    return false;
}

bool VerseModalPresenter::previousPage() {
    if (currentPage_ > 0) {
        currentPage_--;
        return true;
    }
    return false;
}

static void simpleWordWrap(const std::string& prefix, const std::string& text, int maxCharsPerLine, std::vector<std::string>& out) {
    if (text.empty()) return;
    std::string full = prefix.empty() ? text : (prefix + ": " + text);
    std::istringstream words(full);
    std::string word;
    std::string currentLine;

    while (words >> word) {
        if (currentLine.empty()) {
            currentLine = word;
        } else if (currentLine.length() + 1 + word.length() <= static_cast<size_t>(maxCharsPerLine)) {
            currentLine += " " + word;
        } else {
            out.push_back(currentLine);
            currentLine = word;
        }
    }
    if (!currentLine.empty()) {
        out.push_back(currentLine);
    }
}

void VerseModalPresenter::layout(int maxWidth, int maxHeight, int lineHeight) {
    formattedLines_.clear();

    // Approximate characters per line for proportional e-ink typography (e.g. ~45 chars at 16pt on 800px)
    int maxCharsPerLine = std::max(20, maxWidth / 12);

    // 1. Source Reference / Title
    if (!content_.sourceReference.empty()) {
        formattedLines_.push_back("[" + content_.sourceReference + "]");
        formattedLines_.push_back("");
    }

    // 2. Full idiomatic Spanish translation
    if (!content_.spanishFull.empty()) {
        simpleWordWrap("Traducción", content_.spanishFull, maxCharsPerLine, formattedLines_);
        formattedLines_.push_back("");
    }

    // 3. Phonetic transliteration
    if (!content_.transliteration.empty()) {
        simpleWordWrap("Fonética", content_.transliteration, maxCharsPerLine, formattedLines_);
        formattedLines_.push_back("");
    }

    // 4. Halachic and contextual notes
    if (!content_.notes.empty()) {
        simpleWordWrap("Comentario", content_.notes, maxCharsPerLine, formattedLines_);
    }

    // Calculate pagination
    linesPerPage_ = std::max(1, maxHeight / lineHeight);
    totalPages_ = std::max(1, (static_cast<int>(formattedLines_.size()) + linesPerPage_ - 1) / linesPerPage_);
    currentPage_ = 0;
}

} // namespace siddur
