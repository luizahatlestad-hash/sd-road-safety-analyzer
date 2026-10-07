# San Diego County Road Safety Analyzer

A Python tool for exploring nine years of traffic collision data in San Diego County through a Vision Zero lens: where people are killed and seriously injured, on which roads, from what causes, and whether things are getting better.

Built as an object-oriented Python project using only the standard library.

## What it does

The program loads about 220,000 collision records (2014–2022) and lets you explore them from an interactive menu:

- **Choose the data:** the whole county, one year, or one city, and switch between **all roads** and **local roads only** (excluding state highways and freeways, which Caltrans controls).
- **Choose a report:**
  - Top locations by total risk, and by risk per 1,000 residents
  - Most dangerous roads within a city
  - Killed or seriously injured (KSI) by year
  - Leading crash causes, ranked by KSI
  - Estimated societal crash cost by year
  - Deaths by road user (pedestrians, cyclists, motorcyclists, vehicle occupants)
- **Print or save** a full report for any selection as a text file.

## Selected findings (2014–2022)

- **2,306 people were killed** in traffic crashes in San Diego County. About **1 in 3 was a pedestrian** (750) and nearly **1 in 5 a motorcyclist** (434).
- About **60% of severity-weighted crash harm happened on local roads**, the streets cities and the County control, rather than on state highways.
- Per resident, **El Cajon, the unincorporated county, and National City** rank near the top whether or not freeways are included. Some small cities, like Del Mar, also rank high, but their rates can swing with just a few crashes and are affected by visitor traffic.
- In small cities, harm is often concentrated on a few corridors. In Imperial Beach, two roads (Palm Ave and Imperial Beach Blvd) account for over half of local-road crash harm.

## How to run it

Requires Python 3.9 or newer. No packages to install.

1. Download the data zip from the [v1.0 release](https://github.com/luizahatlestad-hash/sd-road-safety-analyzer/releases/tag/v1.0) 
   and unzip it into the project folder. It contains two files:
   
   - `SWITRS Collisions Records 2014-2023.csv`
   - `2020 Census Population by Age Sex Ethnicity.csv`

   Both were originally downloaded from SANDAG's Open Data Portal in October 2026.
3. Run:
   ```
   python main.py
   ```
4. Follow the menu. Loading takes a few seconds.

## Project structure

| File | Purpose |
|---|---|
| `traffic_models.py` | The classes: loading, filtering, and calculating every report |
| `main.py` | The interactive menu, table formatting, and saving reports |

### Design

- **`CollisionRecord`** represents one crash: its severity, location, year, road, road type, cause, and severity weight.
- **`FatalIncident`** and **`InjuryIncident`** inherit from `CollisionRecord` and add counts of who was killed or injured.
- **`SafetyAnalyzer`** holds a collection of crashes and produces every report. Its `filter_by()` method returns a new, smaller analyzer, so every report works the same way on the whole county, one year, one city, or local roads only. Filters can be chained.

## Methodology

**Severity weighting (EPDO).** Counting crashes treats a fender-bender and a fatal crash the same. Instead, each crash is weighted by its estimated societal cost relative to a property-damage-only crash ("equivalent property damage only," or EPDO). Weights use FHWA's national comprehensive crash costs by KABCO severity level (2024 dollars):

| Severity | Cost | EPDO weight |
|---|---|---|
| Fatal (K) | $15,988,000 | ≈ 883 |
| Severe injury (A) | $1,705,100 | ≈ 94 |
| Other visible injury (B) | $384,000 | ≈ 21 |
| Complaint of pain (C) | $204,600 | ≈ 11 |
| Property damage only (O) | $18,100 | 1 |

**Crash cost** converts EPDO back to dollars (EPDO × $18,100).

**KSI** (killed or seriously injured) is the standard Vision Zero measure: fatal and severe-injury crashes, and the people killed or severely injured in them.

**Risk per 1,000 residents** divides each location's annual EPDO by its 2020 Census population.

**Vulnerable road users** follow the federal definition (23 U.S.C. 148(a)(15)): pedestrians and cyclists, not motorcyclists. Motorcyclists are reported separately.

## Data sources

- **Collisions:** SWITRS (Statewide Integrated Traffic Records System) records for San Diego County, published by [SANDAG's Open Data Portal](https://opendata.sandag.org).
- **Population:** 2020 Census Population by Age, Sex and Ethnicity by Jurisdiction, [SANDAG Open Data Portal](https://opendata.sandag.org).
- **Crash costs:** FHWA Highway Safety Improvement Program, *Updated Crash Costs for Highway Safety Analysis* (2024 dollars).

## Notes

- **2023 is excluded.** Every 2023 record in the source file is missing its location, and the year has noticeably fewer crashes than others, suggesting it is incomplete.
- **Crash costs are national.** California agencies often use Caltrans' Local Roadway Safety Manual values instead, so dollar figures and severity weights would differ.
- **Population is a rough measure of exposure.** Cities with freeways, tourism, or many commuters get crashes from people who don't live there. Miles traveled would be a better denominator but isn't available at the city level here.
- **Small numbers are noisy.** In small cities, one serious crash can move rates and percentages a lot.
- **Causes are officer judgments.** The cause is the primary collision factor recorded on the crash report, and many reports list it as "not stated."
- **Road names are as recorded.** One road can appear under several names (for example, a freeway listed by route number and by direction), so road rankings are approximate.
- **Tribal reservations** appear in the crash data but not in the population file, so they are not included in per-resident rankings.

## Author

Luiza Hatlestad
