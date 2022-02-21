# Skyrim VR Address Tools

[![GitHub Release][releases-shield]][releases]
![GitHub all releases][download-all]
![GitHub release (latest by SemVer)][download-latest]
[![GitHub Activity][commits-shield]][commits]

[![License][license-shield]][license]

![Project Maintenance][maintenance-shield]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

Tools for converting a Skyrim SSE skse mod to Skyrim VR.

## Description

This repo consists of two main components:
1. Python files for analyzing c++ code.
2. CSV files that include various data.

### Python

#### vr_address_tools.py

This is a python tool that uses the various csv files to analyze c++ code. It is intended to analyze code built using [commonlibsse](https://github.com/Ryan-rsm-McKenzie/CommonLibSSE) for readiness to compile against [commonlibvr](https://github.com/alandtse/CommonLibVR/tree/vr). This currently requires a commonlibvr that can read csv files.

##### Setting up
1. Pull git repo.
```shell
git clone https://github.com/alandtse/vr_address_tools
cd vr_address_tools
```
2. Install [poetry](https://python-poetry.org/docs/#installation)
3. Install python dependencies
```shell
poetry install
```

##### analyze

Analyze code to determine if uses of rel::id have been defined in `database.csv`. This allows the mod to be compiled with rel::id's without further changes. Rel::ids using offsets may require further code changes if the VR function has changed.

Output will be a tab separated with warnings and potential SSE or VR addresses to check:
```shell
> ./vr_address_tools.py ../CommonLibVR analyze
Finished scanning 1,820 files. rel_ids: 8351 offsets: 4013 results: 90
Database matched: 3869 ida_suggested: 4234 unverified: 3 mismatch: 16 missing: 4466
include/RE/B/BSFaceGenAnimationData.h:26        REL::ID(25977)  SSE: 0x1403c38e0                        WARNING: VR Address undefined.
include/RE/B/BSFaceGenAnimationData.h:33        REL::ID(25980)  SSE: 0x1403c3f00                        WARNING: VR Address undefined.
include/RE/B/BSMusicManager.h:26        REL::ID(514738) SSE: 0x142ec5ce0                        WARNING: VR Address undefined.
include/RE/B/BSPointerHandle.h:213      REL::ID(15967)  SSE: 0x1401ee670                        WARNING: VR Address undefined.
include/RE/B/BSPointerHandle.h:220      REL::ID(12204), 1234    SSE: 0x1401329d0        REL::Offset(0x0143180)  0x140143180     WARNING: Offset detected; offset may need to be manually updated for VR
include/RE/B/BSPointerHandleManager.h:30        REL::ID(514478) SSE: 0x141ec47c0                        WARNING: VR Address undefined.
```

**Warning: rel::id with offsets may require change if the underlying function has been changed in VR.**

```cpp
REL::Relocation<std::uintptr_t> target{ REL::ID(41659), 0x526 };
```
In this example, even if 41659 exists in database.csv, the offset to 0x526 may not be the same in VR and will need to be manually updated.

##### generate

Generate a [database.csv](#databasecsv) or [release csv](#release-csvs). `Database.csv` can be edited manually or generated. Release csvs should be generated using the tool.

###### Generate Release csv:
This will take the database.csv and convert it to a release csv.

```shell
./vr_address_tools.py . generate -rv 1.1.25
Finished scanning 0 files. rel_ids: 0 offsets: 0 results: 0
Filtered 749049 to 3884 using min_confidence 2
Wrote 3884 rows into version-1.4.15.0.csv with release version 1.1.25
```

###### Generate Database.csv
This is intended to scan an existing project that defines both rel::id and rel::offset files with the same namespace. For example, exit-9b's [commonsse vr branch](https://github.com/Exit-9B/CommonLibSSE/tree/vr) was used to generate the initial database.csv file.

```shell
./vr_address_tools.py . generate -d
Finished scanning 0 files. rel_ids: 0 offsets: 0 results: 0
Filtered 749049 to 3884 using min_confidence 2
Wrote 3888 rows into database.csv with release version 0.0.0
```
### CSV Files

#### database.csv
A csv for generating release csv files for loading in CommonLibVR to replace [addresslib][addresslib]. This intended to be a database to identify addresslib ids that represent SkyrimSSE addresses and convert to appropriate VR address. This can be manually edited and is intended to be a community resource. The database.csv can be converted to a release csv using [vr_address_tools.py generate](#generate).

|id|sse|vr|status|name|
|---|--|--|--|----|
|10878|0x1400f7210|0x1401077c0|3|RE::Offset::BGSDefaultObjectManager::GetSingleton

  * id  - Addresslib id
  * sse - SSE Address with base (e.g., 0x1400f7210)
  * vr - VR Address with base (e.g., 0x1401077c0)
  * status - The level of confidence in the VR address.
       * 0 - Unknown
       * 1 - Suggested by automatic tools
       * 2 - Manually entered and assumed manually verified
       * 3 - Manually entered with suggested automatic tools verification
  * name (optional) - A friendly name to describe the id

#### Release CSVs
A non-standard csv installed by end users in the `data/skse/plugins/` directory. This follows the addresslib naming of `version-{skyrim version}.csv`. The first row of data is the csv header, second row is meta data, and third row and beyond is the actual data:

| id | offset |
|-----|--------|
| total entries | version |
| 10878 | 01077c0 |
* id  - Addresslib id
* offset - VR Address as offset (e.g., 01077c0)
* total entries - The number of entries to reserve space for. **WARNING**: CTDs may occur if the **total entries** is less than the actual number of entries since it is allocating space for a memory map.
* version - The release version which is a [semantic version](https://semver.org/).

#### Analysis CSVs
These are CSVs intended to aid in analysis.
##### offsets-1.5.97.0.csv

A dump of addresslib for SkyrimSSE 1.5.97.0. This should be considered canonical for the id -> sse mapping.

|id|sse|
|--|--|
2|10d0

* id  - Addresslib id
* sse - SSE offset (e.g., 10d0)

##### addrlib.csv

A mapping file generated by bakou using ida. Partially automated.
|vr|sse|id|
|--|--|--|
0x1400010d0|0x1400010d0|2
* vr - VR Address with base (e.g., 0x1401077c0)
* sse - SSE Address with base (e.g., 0x1400f7210)
* id  - Addresslib id

##### sse_vr.csv

A mapping file generated by meh321 using IDADiffCalculator, the script used to calculate SSE offsets. Partially automated.
|sse|vr|
|--|--|
|0x141992C10|0x141A33D38|
* sse - SSE Address with base (e.g., 0x1400f7210)
* vr - VR Address with base (e.g., 0x1401077c0)

## Porting a Skyrim VR mod

### Setup CommonLibVR
1. Download [CommonLibVR with csv support](https://github.com/alandtse/CommonLibVR/tree/vr).
2. Set environment variable for `CommonLibVRPath` to CommonLibVR location.
3. Set environment variable for `SkyrimVRPath` to SkyrimVR path
4. Build CommonLibVR. `cmake -B buildVR -S . -DBUILD_SKYRIMVR=ON` to confirm it builds.

### Modify mod
1. Use vr_address_tools to [analyze](#analyze) source tree (the tool currently identifies common `rel::id` formulations. Others may need to be manually found).
2. For any missing rel::ids `WARNING: VR Address undefined.`, modify [database.csv](database.csv) with proper address. Consider upstreaming once verified.
3. For any rel::ids with offsets `WARNING: Offset detected; offset may need to be manually updated for VR`, modify offsets if VR function is different using `#ifndef SKYRIMVR` as appropriate (see 6).
4. [Generate](#generate) release csv file.
5. Copy release csv to SkyrimVR directory: `data/SKSE/Plugins`.
6. Use `#ifndef SKYRIMVR` to identify SSE or VR only sections. For example, the SKSE version check is a common area. Common things (hardest to easiest):
   * x64 Assembly for patchers. This is only needed if functions instructions are not identical. When this happens, the registers used commonly shift in VR vs SSE.
   * [Offsets](https://github.com/alandtse/FEC/commit/b156fdb55c7d7b57f58682f3c31f02dd6097ad36#diff-a1d1f93383f850eb7fdf2ae2c15dbf907badcecde1259ef815c5bf82dfdf1cc7R363-R368) if the function or [vtables](https://github.com/alandtse/FEC/commit/b156fdb55c7d7b57f58682f3c31f02dd6097ad36#diff-a1d1f93383f850eb7fdf2ae2c15dbf907badcecde1259ef815c5bf82dfdf1cc7R363-R368) has changed.
   * Hard coded values [such as `Skyrim Special Edition` like in a path](https://github.com/powerof3/SeasonsOfSkyrim/commit/1c8de7235e2cc01712eb98d5249c641f78d97bbc#diff-276e8ca429d7bc09ead2412ad3d0b2c0f75220f1af3b6922047a145b7133816fR225-R229).
   * [Version checks](https://github.com/powerof3/SeasonsOfSkyrim/commit/1c8de7235e2cc01712eb98d5249c641f78d97bbc#diff-34d21af3c614ea3cee120df276c9c4ae95053830d7f1d3deaf009a4625409ad2R96-R102)
   * Broken functions in VR: 
       * [ActiveEffectsVisitor](https://github.com/alandtse/FEC/commit/b156fdb55c7d7b57f58682f3c31f02dd6097ad36#diff-34d21af3c614ea3cee120df276c9c4ae95053830d7f1d3deaf009a4625409ad2R33-R54)
       * [Mod Counting](https://github.com/powerof3/SeasonsOfSkyrim/commit/1150e58defef7a6c51bfd577be67980909751ead#diff-276e8ca429d7bc09ead2412ad3d0b2c0f75220f1af3b6922047a145b7133816fR128-R137)
       * [Light mod access](https://github.com/alandtse/FEC/commit/b156fdb55c7d7b57f58682f3c31f02dd6097ad36#diff-34d21af3c614ea3cee120df276c9c4ae95053830d7f1d3deaf009a4625409ad2R33-R54)
8. Modify cmakelists.txt, cmakepresets.json. See [example](https://github.com/alandtse/SeasonsOfSkyrim/compare/2804cfdfe6c09569a82ebd46f36fc06c3393da60...alandtse:master#files_bucket).

### Build mod
1. `cmake --preset vs2022-windows-vcpkg-vr`
2. `cmake --build buildvr --config Release` or open buildvr/modname.sln. Build release and copy to SkyrimVR.

## Address IDs

Address IDs are keyed into SSE. However, occasionally an SSE address will not have an Address ID. In that case, they may still be entered by taking the integer value of the SkyrimSSE address.

|id|sse|vr|status|name|
|---|--|--|--|----|
|5370397616|0x14019c3b0|0x1401ac0e0|3|RE::BSShaderProperty::InvalidateMaterial


<!---->

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

---

[buymecoffee]: https://www.buymeacoffee.com/alandtse
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/w/alandtse/vr_address_tools?style=for-the-badge
[commits]: https://github.com/alandtse/vr_address_tools/commits/main
[license]: LICENSE
[license-shield]: https://img.shields.io/github/license/alandtse/vr_address_tools.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Alan%20Tse%20%40alandtse-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/alandtse/vr_address_tools.svg?style=for-the-badge
[releases]: https://github.com/alandtse/vr_address_tools/releases
[download-all]: https://img.shields.io/github/downloads/alandtse/vr_address_tools/total?style=for-the-badge
[download-latest]: https://img.shields.io/github/downloads/alandtse/vr_address_tools/latest/total?style=for-the-badge
[addresslib]: https://www.nexusmods.com/skyrimspecialedition/mods/32444
