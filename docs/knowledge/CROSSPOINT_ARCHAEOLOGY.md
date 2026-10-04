# Retro-Engineering Report

**Target:** `C:\Users\ROG STRIX\Desktop\siddur-init-monorepo-and-prd\input\crosspoint-reader`  
**Generated:** 2026-10-04 09:08  
**Primary Language:** C/C++ Header  
**Platform:** Cross-platform NFC  

---

## 1. Technology Stack

- **Languages:** C/C++ Header (367 files), C++ (225 files), Python (31 files), C (10 files), Shell (4 files), JavaScript (1 files)
- **Build Systems:** pip/Python, CMake/C++
- **Total Source Files:** 638
- **Total Lines:** 752,013

### Hardware / External APIs Detected

| Pattern | Description | Category | Files |
|---------|-------------|----------|-------|
| `FF000000` | ACR122U escape command prefix | nfc | `lib\expat\nametab.h` |

## 2. Architecture & Structure

### Modules (638 source files)

| File | Language | Classes | Functions | Lines |
|------|----------|---------|-----------|-------|
| `lib\Epub\Epub\hyphenation\generated\hyph-de.trie.h` | .h | 0 | 0 | 12908 |
| `lib\expat\xmlparse.c` | .c | 0 | 189 | 8210 |
| `lib\miniz\third_party\miniz.c` | .c | 0 | 193 | 7922 |
| `lib\EpdFont\builtinFonts\notoserif_18_bolditalic.h` | .h | 0 | 0 | 4817 |
| `lib\EpdFont\builtinFonts\notoserif_18_italic.h` | .h | 0 | 0 | 4612 |
| `lib\EpdFont\builtinFonts\notosans_18_bolditalic.h` | .h | 0 | 0 | 4541 |
| `lib\EpdFont\builtinFonts\notoserif_16_bolditalic.h` | .h | 0 | 0 | 4320 |
| `lib\EpdFont\builtinFonts\notosans_18_italic.h` | .h | 0 | 0 | 4300 |
| `lib\EpdFont\builtinFonts\notoserif_18_bold.h` | .h | 0 | 0 | 4180 |
| `lib\EpdFont\builtinFonts\notoserif_16_italic.h` | .h | 0 | 0 | 4156 |
| `lib\EpdFont\builtinFonts\ubuntu_12_bold.h` | .h | 0 | 0 | 4115 |
| `lib\EpdFont\builtinFonts\notosans_16_bolditalic.h` | .h | 0 | 0 | 4077 |
| `lib\EpdFont\builtinFonts\notosans_18_bold.h` | .h | 0 | 0 | 4016 |
| `lib\EpdFont\builtinFonts\notoserif_18_regular.h` | .h | 0 | 0 | 3975 |
| `lib\EpdFont\builtinFonts\notoserif_14_bolditalic.h` | .h | 0 | 0 | 3910 |
| `lib\EpdFont\builtinFonts\notosans_16_italic.h` | .h | 0 | 0 | 3863 |
| `lib\EpdFont\builtinFonts\notosans_18_regular.h` | .h | 0 | 0 | 3781 |
| `lib\EpdFont\builtinFonts\notoserif_14_italic.h` | .h | 0 | 0 | 3750 |
| `lib\EpdFont\builtinFonts\notoserif_16_bold.h` | .h | 0 | 0 | 3750 |
| `lib\EpdFont\builtinFonts\ubuntu_12_regular.h` | .h | 0 | 0 | 3744 |
| `lib\EpdFont\builtinFonts\notosans_14_bolditalic.h` | .h | 0 | 0 | 3690 |
| `lib\EpdFont\builtinFonts\notosans_16_bold.h` | .h | 0 | 0 | 3646 |
| `lib\EpdFont\builtinFonts\notoserif_16_regular.h` | .h | 0 | 0 | 3627 |
| `lib\EpdFont\builtinFonts\notosans_14_italic.h` | .h | 0 | 0 | 3501 |
| `lib\EpdFont\builtinFonts\ubuntu_10_bold.h` | .h | 0 | 0 | 3498 |
| `lib\EpdFont\builtinFonts\notosans_16_regular.h` | .h | 0 | 0 | 3474 |
| `lib\EpdFont\builtinFonts\notoserif_12_bolditalic.h` | .h | 0 | 0 | 3438 |
| `lib\EpdFont\builtinFonts\notoserif_14_bold.h` | .h | 0 | 0 | 3435 |
| `lib\EpdFont\builtinFonts\notosans_14_bold.h` | .h | 0 | 0 | 3324 |
| `lib\EpdFont\builtinFonts\notoserif_14_regular.h` | .h | 0 | 0 | 3318 |

### Public API Surface (4166 symbols)

- **function** `repl` — `scripts\build_html.py`
- **function** `preserve` — `scripts\build_html.py`
- **function** `enumerate` — `scripts\build_html.py`
- **function** `isdigit` — `scripts\build_html.py`
- **function** `walk` — `scripts\build_html.py`
- **function** `len` — `scripts\build_html.py`
- **function** `svg_to_png_bytes` — `scripts\convert_icon.py`
- **function** `load_image` — `scripts\convert_icon.py`
- **function** `image_to_c_array` — `scripts\convert_icon.py`
- **function** `range` — `scripts\convert_icon.py`
- **function** `enumerate` — `scripts\convert_icon.py`
- **function** `main` — `scripts\convert_icon.py`
- **function** `signal_handler` — `scripts\debugging_monitor.py`
- **function** `items` — `scripts\debugging_monitor.py`
- **function** `any` — `scripts\debugging_monitor.py`
- **function** `is_set` — `scripts\debugging_monitor.py`
- **function** `print` — `scripts\debugging_monitor.py`
- **function** `startswith` — `scripts\debugging_monitor.py`
- **function** `lower` — `scripts\debugging_monitor.py`
- **function** `except` — `scripts\debugging_monitor.py`
- **function** `in` — `scripts\debugging_monitor.py`
- **function** `modes` — `scripts\firmware_size_history.py`
- **function** `run` — `scripts\firmware_size_history.py`
- **function** `resolve_ref` — `scripts\firmware_size_history.py`
- **function** `git_current_ref` — `scripts\firmware_size_history.py`
- **function** `git_commit_list` — `scripts\firmware_size_history.py`
- **function** `splitlines` — `scripts\firmware_size_history.py`
- **function** `git_checkout` — `scripts\firmware_size_history.py`
- **function** `build_firmware` — `scripts\firmware_size_history.py`
- **function** `parse_size_line` — `scripts\firmware_size_history.py`
- **function** `write_csv` — `scripts\firmware_size_history.py`
- **function** `format_table` — `scripts\firmware_size_history.py`
- **function** `fmt_size` — `scripts\firmware_size_history.py`
- **function** `fmt_delta` — `scripts\firmware_size_history.py`
- **function** `build_commits_from_range` — `scripts\firmware_size_history.py`
- **function** `build_commits_from_list` — `scripts\firmware_size_history.py`
- **function** `main` — `scripts\firmware_size_history.py`
- **function** `enumerate` — `scripts\firmware_size_history.py`
- **function** `get` — `scripts\generate-font-manifest.py`
- **function** `range` — `scripts\generate-font-manifest.py`
- ... and 4126 more

## 3. Call Tree

*No entry point flows detected.*

### External/Hardware API Call Sites (1012 calls)

| Caller | Callee | File | Line |
|--------|--------|------|------|
| `load_image` | `BytesIO` | `scripts\convert_icon.py` | 22 |
| `any` | `Alloc` | `scripts\debugging_monitor.py` | 392 |
| `any` | `Memory` | `scripts\debugging_monitor.py` | 395 |
| `any` | `Alloc` | `scripts\debugging_monitor.py` | 406 |
| `any` | `Memory` | `scripts\debugging_monitor.py` | 409 |
| `main` | `Serial` | `scripts\debugging_monitor.py` | 489 |
| `main` | `Thread` | `scripts\debugging_monitor.py` | 502 |
| `main` | `Thread` | `scripts\debugging_monitor.py` | 506 |
| `main` | `Graph` | `scripts\debugging_monitor.py` | 509 |
| `except` | `FuncAnimation` | `scripts\debugging_monitor.py` | 533 |
| `write_csv` | `DictWriter` | `scripts\firmware_size_history.py` | 109 |
| `main` | `ArgumentParser` | `scripts\firmware_size_history.py` | 186 |
| `enumerate` | `Building` | `scripts\firmware_size_history.py` | 244 |
| `get` | `ValueError` | `scripts\generate-font-manifest.py` | 73 |
| `get` | `ValueError` | `scripts\generate-font-manifest.py` | 75 |
| `get` | `ValueError` | `scripts\generate-font-manifest.py` | 85 |
| `get` | `ValueError` | `scripts\generate-font-manifest.py` | 87 |
| `get` | `ValueError` | `scripts\generate-font-manifest.py` | 90 |
| `main` | `ArgumentParser` | `scripts\generate-font-manifest.py` | 248 |
| `main` | `Path` | `scripts\generate-font-manifest.py` | 273 |
| `endswith` | `Path` | `scripts\generate-font-manifest.py` | 286 |
| `exists` | `Path` | `scripts\generate-font-manifest.py` | 309 |
| `xhtml` | `Text` | `scripts\generate_br_section_break_epub.py` | 183 |
| `build_epub` | `ZipFile` | `scripts\generate_br_section_break_epub.py` | 208 |
| `create_epub` | `ZipFile` | `scripts\generate_dictionary_synonyms_test_epub.py` | 25 |
| `write_header` | `ValueError` | `scripts\generate_hyphenation_trie.py` | 42 |
| `len` | `ValueError` | `scripts\generate_hyphenation_trie.py` | 48 |
| `main` | `ArgumentParser` | `scripts\generate_hyphenation_trie.py` | 80 |
| `len` | `SystemExit` | `scripts\generate_hyphenation_trie.py` | 88 |
| `zip` | `Path` | `scripts\generate_hyphenation_trie.py` | 92 |
| `zip` | `Path` | `scripts\generate_hyphenation_trie.py` | 94 |
| `targeted` | `Tä` | `scripts\generate_kerning_ligature_epub.py` | 21 |
| `targeted` | `Vä` | `scripts\generate_kerning_ligature_epub.py` | 22 |
| `targeted` | `Wö` | `scripts\generate_kerning_ligature_epub.py` | 23 |
| `targeted` | `Fê` | `scripts\generate_kerning_ligature_epub.py` | 24 |
| `targeted` | `Äu` | `scripts\generate_kerning_ligature_epub.py` | 25 |
| `targeted` | `Öf` | `scripts\generate_kerning_ligature_epub.py` | 26 |
| `targeted` | `Üb` | `scripts\generate_kerning_ligature_epub.py` | 27 |
| `targeted` | `Àp` | `scripts\generate_kerning_ligature_epub.py` | 28 |
| `targeted` | `Pé` | `scripts\generate_kerning_ligature_epub.py` | 29 |
| `targeted` | `Ré` | `scripts\generate_kerning_ligature_epub.py` | 30 |
| `targeted` | `Ñu` | `scripts\generate_kerning_ligature_epub.py` | 31 |
| `targeted` | `Eñ` | `scripts\generate_kerning_ligature_epub.py` | 32 |
| `targeted` | `Çe` | `scripts\generate_kerning_ligature_epub.py` | 33 |
| `targeted` | `Åk` | `scripts\generate_kerning_ligature_epub.py` | 34 |
| `targeted` | `Ør` | `scripts\generate_kerning_ligature_epub.py` | 35 |
| `targeted` | `Cæ` | `scripts\generate_kerning_ligature_epub.py` | 36 |
| `targeted` | `Tř` | `scripts\generate_kerning_ligature_epub.py` | 43 |
| `targeted` | `Vě` | `scripts\generate_kerning_ligature_epub.py` | 44 |
| `targeted` | `Př` | `scripts\generate_kerning_ligature_epub.py` | 45 |

> Total call edges found: **39313**

## 4. External API Usage

## 5. Software Decisions

> Found 145977 decisions: 103886 protocol, 41827 constant, 146 threading, 118 comment

### Critical Decisions (145715)

- **[CONSTANT]** `scripts\debugging_monitor.py:489` — Timing decision: ser = serial.Serial(port, args.baud, timeout=0.1)
  ```
  ser = serial.Serial(port, args.baud, timeout=0.1)
  ```
- **[CONSTANT]** `scripts\debugging_monitor.py:534` — Timing decision: fig, update_graph, interval=1000, cache_frame_data=False
  ```
  fig, update_graph, interval=1000, cache_frame_data=False
  ```
- **[CONSTANT]** `scripts\generate-font-manifest.py:155` — Hardcoded hex constant: 0xFFFFFFFF
  ```
  """Compute CRC32 of a file, matching esp_rom_crc32_le(0xFFFFFFFF, ...) ^ 0xFFFFFFFF."""
  ```
- **[CONSTANT]** `scripts\generate-font-manifest.py:155` — Hardcoded hex constant: 0xFFFFFFFF
  ```
  """Compute CRC32 of a file, matching esp_rom_crc32_le(0xFFFFFFFF, ...) ^ 0xFFFFFFFF."""
  ```
- **[CONSTANT]** `scripts\generate-font-manifest.py:160` — Hardcoded hex constant: 0xFFFFFFFF
  ```
  return crc & 0xFFFFFFFF
  ```
- **[CONSTANT]** `scripts\gen_i18n.py:692` — Hardcoded hex constant: 0x7FFF
  ```
  if current_offset > 0x7FFF:
  ```
- **[CONSTANT]** `scripts\gen_i18n.py:705` — Hardcoded hex constant: 0x8000
  ```
  offsets.append(en_offsets[i] | 0x8000)
  ```
- **[CONSTANT]** `scripts\gen_i18n.py:710` — Hardcoded hex constant: 0x7FFF
  ```
  if current_offset > 0x7FFF:
  ```
- **[CONSTANT]** `src\CrossPointSettings.h:152` — Timing decision: SLEEP = 1,
  ```
  SLEEP = 1,
  ```
- **[CONSTANT]** `src\CrossPointSettings.h:221` — Timing decision: QUICK_RESUME_AFTER_TIMEOUT = 1,
  ```
  QUICK_RESUME_AFTER_TIMEOUT = 1,
  ```
- **[CONSTANT]** `src\main.cpp:143` — Hardcoded hex constant: 0xC1EAB007
  ```
  constexpr uint32_t SILENT_REBOOT_MAGIC = 0xC1EAB007;
  ```
- **[CONSTANT]** `src\main.cpp:66` — Timing decision: constexpr unsigned long X4PRO_POWER_DOUBLE_CLICK_MS = 500;
  ```
  constexpr unsigned long X4PRO_POWER_DOUBLE_CLICK_MS = 500;
  ```
- **[CONSTANT]** `src\main.cpp:67` — Timing decision: constexpr unsigned long X4PRO_POWER_CLICK_MAX_HOLD_MS = 300;
  ```
  constexpr unsigned long X4PRO_POWER_CLICK_MAX_HOLD_MS = 300;
  ```
- **[CONSTANT]** `src\MappedInputManager.cpp:164` — Timing decision: constexpr unsigned long TOUCH_DOWN_SELECT_DELAY_MS = 90;
  ```
  constexpr unsigned long TOUCH_DOWN_SELECT_DELAY_MS = 90;
  ```
- **[CONSTANT]** `src\MappedInputManager.cpp:165` — Timing decision: constexpr unsigned long TOUCH_HELD_OVERRIDE_WINDOW_MS = 250;
  ```
  constexpr unsigned long TOUCH_HELD_OVERRIDE_WINDOW_MS = 250;
  ```
- **[CONSTANT]** `src\MappedInputManager.cpp:196` — Timing decision: unsigned long heldMs = 0;
  ```
  unsigned long heldMs = 0;
  ```
- **[CONSTANT]** `src\MappedInputManager.h:154` — Timing decision: mutable unsigned long touchHeldOverrideMs = 0;
  ```
  mutable unsigned long touchHeldOverrideMs = 0;
  ```
- **[CONSTANT]** `src\SdCardFontSystem.cpp:211` — Hardcoded hex constant: 0x4E00
  ```
  static constexpr uint32_t kFallbackProbes[] = {0x4E00, 0x3042, 0x30A2, 0xAC00, 0x03B1,
  ```
- **[CONSTANT]** `src\SdCardFontSystem.cpp:211` — Hardcoded hex constant: 0x3042
  ```
  static constexpr uint32_t kFallbackProbes[] = {0x4E00, 0x3042, 0x30A2, 0xAC00, 0x03B1,
  ```
- **[CONSTANT]** `src\SdCardFontSystem.cpp:211` — Hardcoded hex constant: 0x30A2
  ```
  static constexpr uint32_t kFallbackProbes[] = {0x4E00, 0x3042, 0x30A2, 0xAC00, 0x03B1,
  ```
- **[CONSTANT]** `src\SdCardFontSystem.cpp:211` — Hardcoded hex constant: 0xAC00
  ```
  static constexpr uint32_t kFallbackProbes[] = {0x4E00, 0x3042, 0x30A2, 0xAC00, 0x03B1,
  ```
- **[CONSTANT]** `src\SdCardFontSystem.cpp:211` — Hardcoded hex constant: 0x03B1
  ```
  static constexpr uint32_t kFallbackProbes[] = {0x4E00, 0x3042, 0x30A2, 0xAC00, 0x03B1,
  ```
- **[CONSTANT]** `src\SdCardFontSystem.cpp:212` — Hardcoded hex constant: 0x0430
  ```
  0x0430, 0x05D0, 0x0627, 0x0E01, 0x0905};
  ```
- **[CONSTANT]** `src\SdCardFontSystem.cpp:212` — Hardcoded hex constant: 0x05D0
  ```
  0x0430, 0x05D0, 0x0627, 0x0E01, 0x0905};
  ```
- **[CONSTANT]** `src\SdCardFontSystem.cpp:212` — Hardcoded hex constant: 0x0627
  ```
  0x0430, 0x05D0, 0x0627, 0x0E01, 0x0905};
  ```
- **[CONSTANT]** `src\SdCardFontSystem.cpp:212` — Hardcoded hex constant: 0x0E01
  ```
  0x0430, 0x05D0, 0x0627, 0x0E01, 0x0905};
  ```
- **[CONSTANT]** `src\SdCardFontSystem.cpp:212` — Hardcoded hex constant: 0x0905
  ```
  0x0430, 0x05D0, 0x0627, 0x0E01, 0x0905};
  ```
- **[CONSTANT]** `lib\EpdFont\EpdFont.cpp:87` — Hardcoded hex constant: 0xFFFF
  ```
  if (!codepoints || count == 0 || cp > 0xFFFF) {
  ```
- **[CONSTANT]** `lib\EpdFont\EpdFont.cpp:97` — Hardcoded hex constant: 0xFFFF
  ```
  if (!entries || count == 0 || cp > 0xFFFF) {
  ```
- **[CONSTANT]** `lib\EpdFont\EpdFont.cpp:167` — Hardcoded hex constant: 0xFB50
  ```
  return (cp >= 0xFB50 && cp <= 0xFDFF) || (cp >= 0xFE70 && cp <= 0xFEFF);
  ```

### Comment Decisions (118)

- `scripts\build_html.py:85` — IMPORTANT: we don't use brotli because Firefox doesn't support brotli with insecured context (only supported on HTTPS)
- `scripts\generate_test_bmps.py:54` — important: colors
- `scripts\patch_sdfat.py:26` — Review: ed upstream and patched bytes. A dependency upgrade requires re-review.
- `lib\EpdFont\SdCardFont.cpp:1400` — Note: advance table is intentionally preserved here. It persists across
- `lib\Epub\Epub.cpp:220` — Note: We can't use `contentBasePath` here as the nav file may be in a different folder to the content.opf
- `lib\expat\expat.h:765` — Note: *:
- `lib\expat\expat.h:782` — Note: *:
- `lib\expat\internal.h:115` — Note: modifiers "td" and "zu" do not work for MinGW
- `lib\expat\internal.h:142` — NOTE: BEGIN If you ever patch these defaults to greater values
- `lib\expat\internal.h:152` — NOTE: If function expat_alloc was user facing, EXPAT_MALLOC_ALIGNMENT would
- `lib\expat\internal.h:157` — NOTE: END */
- `lib\expat\siphash.h:88` — NOTE: S:
- `lib\expat\siphash.h:105` — Workaround: to not require a C++11 compiler for using ULL suffix
- `lib\expat\siphash.h:107` — warning: use of C++11 long long integer constant [-Wlong-long]
- `lib\expat\xmlparse.c:743` — NOTE: This can be +infinity or -nan
- *... and 103 more*

### Constant Decisions (41827)

- `scripts\debugging_monitor.py:489` — Timing decision: ser = serial.Serial(port, args.baud, timeout=0.1)
- `scripts\debugging_monitor.py:534` — Timing decision: fig, update_graph, interval=1000, cache_frame_data=False
- `scripts\generate-font-manifest.py:155` — Hardcoded hex constant: 0xFFFFFFFF
- `scripts\generate-font-manifest.py:155` — Hardcoded hex constant: 0xFFFFFFFF
- `scripts\generate-font-manifest.py:160` — Hardcoded hex constant: 0xFFFFFFFF
- `scripts\gen_i18n.py:692` — Hardcoded hex constant: 0x7FFF
- `scripts\gen_i18n.py:705` — Hardcoded hex constant: 0x8000
- `scripts\gen_i18n.py:710` — Hardcoded hex constant: 0x7FFF
- `src\CrossPointSettings.h:152` — Timing decision: SLEEP = 1,
- `src\CrossPointSettings.h:221` — Timing decision: QUICK_RESUME_AFTER_TIMEOUT = 1,
- `src\main.cpp:143` — Hardcoded hex constant: 0xC1EAB007
- `src\main.cpp:66` — Timing decision: constexpr unsigned long X4PRO_POWER_DOUBLE_CLICK_MS = 500;
- `src\main.cpp:67` — Timing decision: constexpr unsigned long X4PRO_POWER_CLICK_MAX_HOLD_MS = 300;
- `src\MappedInputManager.cpp:164` — Timing decision: constexpr unsigned long TOUCH_DOWN_SELECT_DELAY_MS = 90;
- `src\MappedInputManager.cpp:165` — Timing decision: constexpr unsigned long TOUCH_HELD_OVERRIDE_WINDOW_MS = 250;
- *... and 41812 more*

### Threading Decisions (146)

- `scripts\debugging_monitor.py:14` — Concurrency/threading: signal
- `scripts\debugging_monitor.py:16` — Concurrency/threading: thread
- `scripts\debugging_monitor.py:34` — Concurrency/threading: threading
- `scripts\debugging_monitor.py:197` — Concurrency/threading: event
- `src\CrossPointSettings.h:409` — Concurrency/threading: concurrent
- `src\CrossPointSettings.h:412` — Concurrency/threading: mutex
- `src\main.cpp:280` — Concurrency/threading: event
- `src\main.cpp:338` — Concurrency/threading: lock
- `src\main.cpp:872` — Concurrency/threading: queue
- `src\MappedInputManager.h:50` — Concurrency/threading: event
- `src\SdCardFontSystem.h:51` — Concurrency/threading: thread
- `src\WifiCredentialStore.cpp:10` — Concurrency/threading: mutex
- `src\WifiCredentialStore.h:31` — Concurrency/threading: mutex
- `test\test_trusted_time.py:18` — Concurrency/threading: lock
- `lib\DeviceSecret\DeviceSecret.cpp:8` — Concurrency/threading: mutex
- *... and 131 more*

### Protocol Decisions (103886)

- `lib\expat\nametab.h:72` — Hardcoded byte sequence (possible APDU or device command)
- `lib\expat\nametab.h:73` — Hardcoded byte sequence (possible APDU or device command)
- `lib\expat\nametab.h:74` — Hardcoded byte sequence (possible APDU or device command)
- `lib\expat\nametab.h:75` — Hardcoded byte sequence (possible APDU or device command)
- `lib\expat\nametab.h:76` — Hardcoded byte sequence (possible APDU or device command)
- `lib\expat\nametab.h:77` — Hardcoded byte sequence (possible APDU or device command)
- `lib\expat\nametab.h:78` — Hardcoded byte sequence (possible APDU or device command)
- `lib\expat\nametab.h:79` — Hardcoded byte sequence (possible APDU or device command)
- `lib\expat\nametab.h:80` — Hardcoded byte sequence (possible APDU or device command)
- `lib\expat\nametab.h:81` — Hardcoded byte sequence (possible APDU or device command)
- `lib\expat\nametab.h:82` — Hardcoded byte sequence (possible APDU or device command)
- `lib\expat\nametab.h:83` — Hardcoded byte sequence (possible APDU or device command)
- `lib\expat\nametab.h:84` — Hardcoded byte sequence (possible APDU or device command)
- `lib\expat\nametab.h:85` — Hardcoded byte sequence (possible APDU or device command)
- `lib\expat\nametab.h:88` — Hardcoded byte sequence (possible APDU or device command)
- *... and 103871 more*

## 6. Cross-Platform Porting Notes


---
*Generated by retro-engineer v1.0*