"""
traffic_models.py

Classes for analyzing San Diego County collision records (SWITRS, via SANDAG).

- CollisionRecord: one crash, with its severity, location, year, road,
  road type, and primary cause.
- FatalIncident and InjuryIncident: subclasses that add victim counts.
- SafetyAnalyzer: a collection of crashes, with methods for loading data,
  filtering, and summarizing risk (EPDO), deaths, KSI, and crash causes.

This file only defines tools. main.py loads the data and runs the menu.
"""
from csv import DictReader


def to_int(value):
    """Convert a CSV cell to an integer. Blanks and 'NULL' become 0.

    Anything else that isn't a whole number raises a ValueError, so
    unexpected data is noticed instead of hidden.
    """
    value = value.strip()
    if value in ('', 'NULL'):
        return 0
    return int(value)


class SafetyAnalyzer:
    """A collection of collision records and the reports built from them.

    Records are stored in a dictionary keyed by SANDAG case ID. Every
    report method works on whatever records the analyzer holds, so a
    filtered analyzer (one year, one city, local roads) reuses all of them.
    """

    def __init__(self):
        self.collision_records = {}
        self.population = {}

    # ---------- Loading ----------
    def open_file_and_add_dict(self, filename, last_year=None):
        """Load crashes from a SWITRS CSV file.

        Fatal crashes become FatalIncident objects, injury crashes become
        InjuryIncident objects, and the rest become CollisionRecord objects.
        Rows after last_year are skipped (None means keep every year).
        """
        with open(filename, mode='r', newline='', encoding='utf-8') as file:
            reader = DictReader(file)

            for row in reader:
                year = to_int(row['ACCIDENT_YEAR'])
                if last_year is not None and year > last_year:
                    continue

                if row['COLLISION_SEVERITY'] == 'Fatal':
                    record = FatalIncident(row)
                elif 'Injury' in row['COLLISION_SEVERITY']:
                    record = InjuryIncident(row)
                else:
                    record = CollisionRecord(row)

                self.collision_records[record.case_ID] = record

    def load_population(self, filename):
        """Load 2020 Census population by jurisdiction from SANDAG's CSV.

        The file has one row per age/sex/ethnicity group, so rows are summed
        per jurisdiction. Names are cleaned to match the crash data
        ('City of Chula Vista' becomes 'Chula Vista').
        """
        self.population = {}

        with open(filename, mode='r', newline='', encoding='utf-8') as file:
            reader = DictReader(file)

            for row in reader:
                name = row['jurisdiction'].replace('City of ', '')
                if name == 'Unincorporated San Diego County':
                    name = 'Unincorporated'

                population = int(row['population'].replace(',', ''))
                self.population[name] = self.population.get(name, 0) + population

    # ---------- Searching and filtering ----------
    def get_unique_values(self, attribute):
        """Return the set of distinct values of an attribute, like 'year'."""
        unique_values = set()
        for record in self.collision_records.values():
            unique_values.add(getattr(record, attribute))
        return unique_values

    def get_records_by_attribute(self, attribute, looking_for):
        """Return a list of records whose attribute equals looking_for."""
        matches = []
        for record in self.collision_records.values():
            if getattr(record, attribute) == looking_for:
                matches.append(record)
        return matches

    def filter_by(self, attribute, value):
        """Return a new SafetyAnalyzer holding only the matching records.

        The population data is shared, so per-resident reports still work.
        Filters can be chained:
            analyzer.filter_by('road_type', 'Local road').filter_by('year', 2021)
        """
        new_analyzer = SafetyAnalyzer()

        for record in self.collision_records.values():
            if getattr(record, attribute) == value:
                new_analyzer.collision_records[record.case_ID] = record

        new_analyzer.population = self.population
        return new_analyzer

    # ---------- Risk (EPDO) ----------
    def total_risk(self, records=None):
        """Sum the EPDO weights of the given records (default: all of them)."""
        if records is None:
            records = self.collision_records.values()
        return sum(record.risk_weight() for record in records)

    def risk_by_attribute(self, attribute):
        """Return {value: total EPDO} for an attribute, in one pass."""
        results = {}
        for record in self.collision_records.values():
            value = getattr(record, attribute)
            results[value] = results.get(value, 0) + record.risk_weight()
        return results

    def top_locations(self, n=10):
        """Return the n locations with the highest total EPDO.

        Crashes with no recorded location are left out of the ranking.
        """
        results = self.risk_by_attribute('location')
        ranking = sorted(results.items(), key=lambda pair: pair[1], reverse=True)

        filtered = []
        for location, score in ranking:
            if location != 'Missing location':
                filtered.append((location, score))

        return filtered[0:n]

    def top_roads(self, n=10):
        """Return the n roads with the highest total EPDO.

        Road names repeat across cities, so this is most meaningful
        on an analyzer filtered to one location.
        """
        results = self.risk_by_attribute('primary_road')
        ranking = sorted(results.items(), key=lambda pair: pair[1], reverse=True)
        return ranking[0:n]

    def risk_by_year(self):
        """Return [(year, total EPDO), ...] sorted by year."""
        results = self.risk_by_attribute('year')
        return sorted(results.items())

    def cost_by_year(self):
        """Return [(year, estimated societal cost in dollars), ...].

        EPDO units are converted to dollars by multiplying by the cost
        of one property-damage-only crash.
        """
        pdo_cost = CollisionRecord.CRASH_COSTS['Property Damage Only']

        costs = []
        for year, score in self.risk_by_year():
            costs.append((year, score * pdo_cost))
        return costs

    def risk_per_1000(self):
        """Return [(location, annual EPDO per 1,000 residents), ...], highest first.

        Locations without population data (such as tribal reservations)
        are skipped. The rate is divided by the number of years in the data.
        """
        risk = self.risk_by_attribute('location')
        number_of_years = len(self.get_unique_values('year'))
        rates = []

        for location, score in risk.items():
            if location in self.population:
                rate = score / self.population[location] * 1000 / number_of_years
                rates.append((location, rate))

        return sorted(rates, key=lambda pair: pair[1], reverse=True)

    # ---------- Deaths, KSI, and causes ----------
    def deaths_by_road_user(self):
        """Return deaths by road user type, from the fatal crashes.

        Keys: total, pedestrians, bicyclists, motorcyclists,
        occupants_and_others (everyone killed who isn't in the first three).
        """
        fatal_records = self.get_records_by_attribute('severity', 'Fatal')
        total = 0
        pedestrians = 0
        bicyclists = 0
        motorcyclists = 0

        for record in fatal_records:
            total += record.number_killed
            pedestrians += record.ped_killed
            bicyclists += record.bicyclist_killed
            motorcyclists += record.motorcyclist_killed

        occupants_and_others = total - pedestrians - bicyclists - motorcyclists

        return {'total': total, 'pedestrians': pedestrians, 'bicyclists': bicyclists,
                'motorcyclists': motorcyclists, 'occupants_and_others': occupants_and_others}

    def death_percentages(self):
        """Return each road user group's share of deaths, rounded to 0.1%.

        Percentages may not sum to 100 due to rounding.
        """
        counts = self.deaths_by_road_user()
        total = counts['total']

        percentages = {}
        for road_user, number in counts.items():
            if road_user != 'total':
                percentages[road_user] = round(number / total * 100, 1)
        return percentages

    def ksi_by_year(self):
        """Return [(year, ksi_crashes, ksi_people), ...] sorted by year.

        KSI means killed or seriously injured, the standard Vision Zero measure.
        - ksi_crashes: fatal crashes plus severe-injury crashes.
        - ksi_people: everyone killed plus everyone severely injured.
        Years with no KSI crashes are still listed, with zeros.
        """
        crashes = {year: 0 for year in self.get_unique_values('year')}
        people = dict(crashes)

        for record in self.collision_records.values():
            if record.is_ksi:
                crashes[record.year] += 1
                people[record.year] += record.killed + record.severe_injured

        return [(year, crashes[year], people[year]) for year in sorted(crashes)]

    def top_causes(self, n=10):
        """Return the n leading crash causes as (cause, all_crashes, ksi_crashes).

        Cause is the primary collision factor recorded by the reporting
        officer. Causes are ranked by KSI crashes first, then by all crashes.
        """
        crashes = {}
        ksi = {}

        for record in self.collision_records.values():
            crashes[record.cause] = crashes.get(record.cause, 0) + 1
            if record.is_ksi:
                ksi[record.cause] = ksi.get(record.cause, 0) + 1

        rows = [(cause, count, ksi.get(cause, 0)) for cause, count in crashes.items()]
        rows.sort(key=lambda row: (row[2], row[1]), reverse=True)
        return rows[0:n]


class CollisionRecord:
    """One crash from the SWITRS data.

    Each crash gets an EPDO weight: its severity's crash cost divided by
    the cost of a property-damage-only crash.
    """

    # FHWA national comprehensive crash costs by KABCO severity, 2024 dollars
    # Source: FHWA HSIP, "Updated Crash Costs for Highway Safety Analysis"
    CRASH_COSTS = {
        'Fatal': 15_988_000,                        # K
        'Injury (Severe)': 1_705_100,               # A
        'Injury (Other Visible)': 384_000,          # B
        'Injury (Complaint of Pain)': 204_600,      # C
        'Property Damage Only': 18_100,             # O
    }

    def __init__(self, row):
        self.case_ID = row['SANDAG_CASE_ID']

        # Location: blanks and 'NULL' are grouped as missing
        self.location = row['Location_sandag']
        if self.location.strip() in ('', 'NULL'):
            self.location = 'Missing location'

        self.year = to_int(row['ACCIDENT_YEAR'])

        self.primary_road = row['PRIMARY_RD'].strip().upper()

        # Road type: who is responsible for the road
        road = row['STATE_HWY_IND']
        if road == 'State Highway':
            self.road_type = 'State highway'
        elif road == 'Not State Highway':
            self.road_type = 'Local road'
        else:
            self.road_type = 'Not stated'

        # Severity: the data uses two spellings for property damage only
        self.severity = row['COLLISION_SEVERITY']
        if self.severity == 'PDO':
            self.severity = 'Property Damage Only'

        # EPDO weight, calculated once per crash
        self.weight = self.CRASH_COSTS[self.severity] / self.CRASH_COSTS['Property Damage Only']

        # KSI: killed or seriously injured
        self.killed = to_int(row['NUMBER_KILLED'])
        self.severe_injured = to_int(row['COUNT_SEVERE_INJ'])
        self.is_ksi = self.severity in ('Fatal', 'Injury (Severe)')

        # Primary collision factor (cause), with blanks grouped together
        cause = row['PCF_VIOL_CATEGORY'].strip()
        if cause in ('', 'NULL', '- Not Stated -', 'Not Stated'):
            cause = 'Not stated'
        self.cause = cause

    def risk_weight(self):
        """Return this crash's EPDO weight (property damage only = 1)."""
        return self.weight


class FatalIncident(CollisionRecord):
    """A fatal crash, with counts of who was killed."""

    def __init__(self, row):
        super().__init__(row)
        self.number_killed = to_int(row['NUMBER_KILLED'])
        self.ped_killed = to_int(row['COUNT_PED_KILLED'])
        self.bicyclist_killed = to_int(row['COUNT_BICYCLIST_KILLED'])
        self.motorcyclist_killed = to_int(row['COUNT_MC_KILLED'])

    def was_vulnerable_road_user_killed(self):
        """True if a pedestrian or cyclist was killed.

        Follows the federal definition (23 U.S.C. 148(a)(15)),
        which excludes motorcyclists.
        """
        return self.ped_killed > 0 or self.bicyclist_killed > 0

    def was_motorcyclist_killed(self):
        """True if a motorcyclist was killed."""
        return self.motorcyclist_killed > 0


class InjuryIncident(CollisionRecord):
    """An injury crash, with counts of who was injured (at any level)."""

    def __init__(self, row):
        super().__init__(row)
        self.number_injured = to_int(row['NUMBER_INJURED'])
        self.ped_injured = to_int(row['COUNT_PED_INJURED'])
        self.bicyclist_injured = to_int(row['COUNT_BICYCLIST_INJURED'])
        self.motorcyclist_injured = to_int(row['COUNT_MC_INJURED'])

    def was_vulnerable_road_user_injured(self):
        """True if a pedestrian or cyclist was injured.

        Follows the federal definition (23 U.S.C. 148(a)(15)),
        which excludes motorcyclists.
        """
        return self.ped_injured > 0 or self.bicyclist_injured > 0

    def was_motorcyclist_injured(self):
        """True if a motorcyclist was injured."""
        return self.motorcyclist_injured > 0


if __name__ == '__main__':
    import os
    HERE = os.path.dirname(os.path.abspath(__file__))
    analyzer = SafetyAnalyzer()
    analyzer.open_file_and_add_dict(os.path.join(HERE, 'SWITRS Collisions Records 2014-2023.csv'), last_year=2022)
    analyzer.load_population(os.path.join(HERE, '2020 Census Population by Age Sex Ethnicity.csv'))
    print(f'{len(analyzer.collision_records):,} crashes loaded')