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

This is a python tool that uses the various csv files to analyze c++ code. It is intended to analyze code built using [commonlibsse](https://github.com/Ryan-rsm-McKenzie/CommonLibSSE) for readiness to compile against commonlibvr.

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

Analyze code to determine if uses of rel::id have been defined in `database.csv`. This allows the mod to be compiled with the rel::id's without further changes. 

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

Generate a database.csv or release csv. This is intended to scan an existing project that defines both rel::id and rel::offset files with the same namespace. For example, exit-9b's [commonsse vr branch](https://github.com/Exit-9B/CommonLibSSE/tree/vr) was used to generate the initial database.csv file.

### CSV Files

#### database.csv 
A csv for generating release csv files for loading in CommonLibVR to replace [addresslib][addresslib]. This intended to be a database to identify addresslib ids that represent SkyrimSSE addresses and convert to appropriate VR address. This can be manually edited and is intended to be a community resource. The database.csv can be converted to a release csv using vr_address_tools.py.

```shell
./vr_address_tools.py . generate -rv 1.1.25
Finished scanning 0 files. rel_ids: 0 offsets: 0 results: 0
Filtered 749049 to 3884 using min_confidence 2
Wrote 3884 rows into version-1.4.15.0.csv with release version 1.1.25
```

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

A mapping file generated by meth321 using IDADiffCalculator, the script used to calculate SSE offsets. Partially automated.
|sse|vr|
|--|--|
|0x141992C10|0x141A33D38|
* sse - SSE Address with base (e.g., 0x1400f7210)
* vr - VR Address with base (e.g., 0x1401077c0)

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