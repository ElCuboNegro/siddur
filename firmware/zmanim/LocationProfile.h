/**
 * firmware/zmanim/LocationProfile.h
 * Halachic location profile and city presets for Siddur e-ink.
 * Handles Diaspora vs Israel rules, coordinates, timezones, and elevations.
 */

#ifndef SIDDUR_LOCATION_PROFILE_H
#define SIDDUR_LOCATION_PROFILE_H

#include "HebrewCalendarEngine.h"
#include <string>
#include <vector>

namespace siddur {

struct CityPreset {
    std::string cityName;
    std::string country;
    GeoLocation location;
    int candleLightingMinutes; // Standard is 18, Jerusalem is 40, some communities use 20
    int elevationMeters;        // Meters above sea level
};

class LocationProfileManager {
public:
    // Returns the curated list of default city presets
    static std::vector<CityPreset> getPresets();

    // Returns default preset matching user's primary diaspora locale (Bogotá, Colombia, UTC-5)
    static CityPreset getDefaultPreset();

    // Find preset by city name (case-insensitive search)
    static CityPreset findPresetByName(const std::string& name);

    // Create a custom location profile
    static GeoLocation createCustomLocation(double lat, double lon, double tzOffset, bool isIsrael);
};

} // namespace siddur

#endif // SIDDUR_LOCATION_PROFILE_H
