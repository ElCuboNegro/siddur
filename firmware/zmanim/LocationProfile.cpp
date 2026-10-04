/**
 * firmware/zmanim/LocationProfile.cpp
 * Implementation of LocationProfileManager.
 */

#include "LocationProfile.h"
#include <algorithm>
#include <cctype>

namespace siddur {

std::vector<CityPreset> LocationProfileManager::getPresets() {
    return {
        // Colombia (User's locale - Diaspora, UTC-5, no DST)
        {
            "Bogotá",
            "Colombia",
            {4.7110, -74.0721, -5.0, false},
            18,
            2600
        },
        {
            "Medellín",
            "Colombia",
            {6.2442, -75.5812, -5.0, false},
            18,
            1495
        },
        {
            "Cali",
            "Colombia",
            {3.4516, -76.5320, -5.0, false},
            18,
            1018
        },
        {
            "Barranquilla",
            "Colombia",
            {10.9685, -74.7813, -5.0, false},
            18,
            18
        },
        // Latin America
        {
            "Ciudad de México",
            "México",
            {19.4326, -99.1332, -6.0, false},
            18,
            2240
        },
        {
            "Buenos Aires",
            "Argentina",
            {-34.6037, -58.3816, -3.0, false},
            18,
            25
        },
        {
            "Santiago",
            "Chile",
            {-33.4489, -70.6693, -4.0, false},
            18,
            570
        },
        {
            "Panamá",
            "Panamá",
            {8.9824, -79.5199, -5.0, false},
            18,
            10
        },
        {
            "Caracas",
            "Venezuela",
            {10.4806, -66.9036, -4.0, false},
            18,
            900
        },
        // North America
        {
            "Miami",
            "Estados Unidos",
            {25.7617, -80.1918, -5.0, false},
            18,
            2
        },
        {
            "Nueva York",
            "Estados Unidos",
            {40.7128, -74.0060, -5.0, false},
            18,
            10
        },
        // Israel (Eretz Yisrael)
        {
            "Jerusalén",
            "Israel",
            {31.7767, 35.2345, 2.0, true},
            40, // 40 minutes custom in Jerusalem
            754
        },
        {
            "Tel Aviv",
            "Israel",
            {32.0853, 34.7818, 2.0, true},
            20,
            5
        }
    };
}

CityPreset LocationProfileManager::getDefaultPreset() {
    // Default to Bogotá, Colombia (Diaspora, UTC-5)
    return {
        "Bogotá",
        "Colombia",
        {4.7110, -74.0721, -5.0, false},
        18,
        2600
    };
}

CityPreset LocationProfileManager::findPresetByName(const std::string& name) {
    auto presets = getPresets();
    std::string lowerQuery = name;
    std::transform(lowerQuery.begin(), lowerQuery.end(), lowerQuery.begin(), [](unsigned char c){
        return std::tolower(c);
    });

    for (const auto& preset : presets) {
        std::string lowerCity = preset.cityName;
        std::transform(lowerCity.begin(), lowerCity.end(), lowerCity.begin(), [](unsigned char c){
            return std::tolower(c);
        });
        if (lowerCity.find(lowerQuery) != std::string::npos || lowerQuery.find(lowerCity) != std::string::npos) {
            return preset;
        }
    }

    return getDefaultPreset();
}

GeoLocation LocationProfileManager::createCustomLocation(double lat, double lon, double tzOffset, bool isIsrael) {
    GeoLocation loc;
    loc.latitude = lat;
    loc.longitude = lon;
    loc.timeZoneOffsetHours = tzOffset;
    loc.isIsrael = isIsrael;
    return loc;
}

} // namespace siddur
