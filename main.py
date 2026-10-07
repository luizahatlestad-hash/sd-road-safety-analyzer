"""
main.py

Interactive menu for the San Diego County road safety report.

Loads the collision and population data once, then lets the user choose
what to look at (the whole county, one year, one location, all roads or
local roads only) and which report to see, print, or save to a text file.

Run with:  python main.py
"""
import os
from contextlib import redirect_stdout

from traffic_models import SafetyAnalyzer

# ---------- Settings ----------
# Look for data files next to this script, wherever the program is run from
HERE = os.path.dirname(os.path.abspath(__file__))
FILENAME = os.path.join(HERE, 'SWITRS Collisions Records 2014-2023.csv')
POPULATION_FILE = os.path.join(HERE, '2020 Census Population by Age Sex Ethnicity.csv')
FIRST_YEAR = 2014
LAST_YEAR = 2022   # 2023 excluded: incomplete records, no location data

LABELS = {
    'total': 'Total deaths',
    'pedestrians': 'Pedestrians',
    'bicyclists': 'Bicyclists',
    'motorcyclists': 'Motorcyclists',
    'occupants_and_others': 'Vehicle occupants & others',
}


# ---------- Formatting helpers ----------
def cause_label(cause):
    """Return a shorter display name for long crash-cause categories."""
    if 'influence' in cause.lower():
        return 'DUI (alcohol or drugs)'
    return cause

def format_cost(value):
    """Format dollars as $1.23B for large values or $45.6M for smaller ones."""
    if value >= 1e9:
        return f'${value / 1e9:.2f}B'
    return f'${value / 1e6:,.1f}M'


def format_change(current, previous):
    """Format the percent change from previous to current, like '+4.2%'."""
    if previous is None:
        return '—'
    if previous == 0:
        return 'n/a'
    return f'{(current - previous) / previous * 100:+.1f}%'


# ---------- Report tables ----------
def show_top_locations(a, n=10):
    """Print the n locations with the highest total risk (EPDO)."""
    total = a.total_risk()
    if total == 0:
        print('\nNo crashes found for this selection.')
        return

    top = a.top_locations(n)
    rank_w, name_w, num_w, pct_w = 6, 25, 15, 10
    line = '-' * (rank_w + name_w + num_w + pct_w)

    print(f'\n{"Rank":<{rank_w}}{"Location":<{name_w}}{"Risk (EPDO)":>{num_w}}{"Share":>{pct_w}}')
    print(line)
    for rank, (location, score) in enumerate(top, start=1):
        share = score / total * 100
        print(f'{rank:<{rank_w}}{location:<{name_w}}{score:>{num_w},.0f}{share:>{pct_w - 1}.1f}%')
    print(line)
    print(f'{"":<{rank_w}}{"Total":<{name_w}}{total:>{num_w},.0f}')
    print('EPDO = crashes weighted by severity (1 fatal crash ≈ 883 property-damage crashes).')


def show_risk_per_1000(a, n=10):
    """Print the n locations with the highest annual risk per 1,000 residents."""
    rates = a.risk_per_1000()
    if not rates:
        print('\nNo population data available for this selection.')
        return

    rank_w, name_w, pop_w, rate_w = 6, 25, 14, 14
    line = '-' * (rank_w + name_w + pop_w + rate_w)

    print(f'\n{"Rank":<{rank_w}}{"Location":<{name_w}}{"Population":>{pop_w}}{"EPDO/1,000":>{rate_w}}')
    print(line)
    for rank, (location, rate) in enumerate(rates[0:n], start=1):
        population = a.population[location]
        print(f'{rank:<{rank_w}}{location:<{name_w}}{population:>{pop_w},}{rate:>{rate_w},.1f}')
    print(line)
    print('Rate = annual severity-weighted risk (EPDO) per 1,000 residents.')
    print('Population: 2020 Census (SANDAG). Locations without population data are not ranked.')
    print('Small cities and places with many visitors may show higher rates.')


def show_top_roads(a, n=10):
    """Print the n roads with the highest total risk (for one location)."""
    total = a.total_risk()
    if total == 0:
        print('\nNo crashes found for this selection.')
        return

    top = a.top_roads(n)
    rank_w, name_w, num_w, pct_w = 6, 30, 15, 10
    line = '-' * (rank_w + name_w + num_w + pct_w)

    print(f'\n{"Rank":<{rank_w}}{"Road":<{name_w}}{"Risk (EPDO)":>{num_w}}{"Share":>{pct_w}}')
    print(line)
    for rank, (road, score) in enumerate(top, start=1):
        share = score / total * 100
        print(f'{rank:<{rank_w}}{road:<{name_w}}{score:>{num_w},.0f}{share:>{pct_w - 1}.1f}%')
    print(line)
    print('Road names are as recorded in crash reports; one road may appear')
    print('under more than one name.')


def show_cost_by_year(a):
    """Print the estimated societal crash cost for each year."""
    costs = a.cost_by_year()
    if not costs:
        print('\nNo crashes found for this selection.')
        return

    year_w, cost_w, change_w = 10, 15, 15
    line = '-' * (year_w + cost_w + change_w)

    print(f'\n{"Year":<{year_w}}{"Crash cost":>{cost_w}}{"vs. prior year":>{change_w}}')
    print(line)
    previous = None
    for year, cost in costs:
        print(f'{year:<{year_w}}{format_cost(cost):>{cost_w}}{format_change(cost, previous):>{change_w}}')
        previous = cost

    total_cost = sum(cost for year, cost in costs)
    print(line)
    print(f'{"Total":<{year_w}}{format_cost(total_cost):>{cost_w}}')
    print('Crash cost = estimated societal cost (FHWA 2024 comprehensive crash costs).')


def show_ksi_by_year(a):
    """Print KSI (killed or seriously injured) crashes and people for each year."""
    rows = a.ksi_by_year()
    total_crashes = sum(crashes for year, crashes, people in rows)
    if total_crashes == 0:
        print('\nNo fatal or severe-injury crashes found for this selection.')
        return

    year_w, crash_w, people_w, change_w = 10, 14, 14, 16
    line = '-' * (year_w + crash_w + people_w + change_w)

    print(f'\n{"Year":<{year_w}}{"KSI crashes":>{crash_w}}{"People KSI":>{people_w}}{"vs. prior year":>{change_w}}')
    print(line)
    previous = None
    for year, crashes, people in rows:
        print(f'{year:<{year_w}}{crashes:>{crash_w},}{people:>{people_w},}{format_change(people, previous):>{change_w}}')
        previous = people

    total_people = sum(people for year, crashes, people in rows)
    print(line)
    print(f'{"Total":<{year_w}}{total_crashes:>{crash_w},}{total_people:>{people_w},}')
    print('KSI = killed or seriously injured, the standard Vision Zero measure.')
    print('People KSI counts everyone killed or severely injured; one crash can involve several people.')
    if total_people < 20:
        print('Small numbers: year-to-year changes can swing a lot with a single crash.')


def show_top_causes(a, n=10):
    """Print the leading crash causes, ranked by KSI crashes."""
    rows = a.top_causes(n)
    if not rows:
        print('\nNo crashes found for this selection.')
        return

    total_ksi = sum(1 for record in a.collision_records.values() if record.is_ksi)
    rank_w, name_w, all_w, ksi_w, pct_w = 6, 32, 12, 14, 14
    line = '-' * (rank_w + name_w + all_w + ksi_w + pct_w)

    print(f'\n{"Rank":<{rank_w}}{"Cause":<{name_w}}{"Crashes":>{all_w}}{"KSI crashes":>{ksi_w}}{"Share of KSI":>{pct_w}}')
    print(line)
    for rank, (cause, crashes, ksi) in enumerate(rows, start=1):
        share = ksi / total_ksi * 100 if total_ksi else 0
        label = cause_label(cause)
        if len(label) > name_w - 2:
            label = label[:name_w - 3] + '…'   # shorten anything still too long
        print(f'{rank:<{rank_w}}{label:<{name_w}}{crashes:>{all_w},}{ksi:>{ksi_w},}{share:>{pct_w - 1}.1f}%')
    print(line)
    print('Cause = primary collision factor recorded by the reporting officer.')
    print('Ranked by KSI crashes, so the causes behind the most serious harm come first.')

def show_deaths(a):
    """Print traffic deaths by type of road user."""
    counts = a.deaths_by_road_user()
    if counts['total'] == 0:
        print('\nNo traffic deaths recorded for this selection.')
        return

    percents = a.death_percentages()
    name_w, num_w, pct_w = 30, 10, 10
    line = '-' * (name_w + num_w + pct_w)

    print(f'\n{"Road user":<{name_w}}{"Deaths":>{num_w}}{"Share":>{pct_w}}')
    print(line)
    for road_user, deaths in counts.items():
        if road_user != 'total':
            label = LABELS.get(road_user, road_user)
            print(f'{label:<{name_w}}{deaths:>{num_w},}{percents[road_user]:>{pct_w - 1}.1f}%')
    print(line)
    print(f'{"Total deaths":<{name_w}}{counts["total"]:>{num_w},}')
    print('Percentages may not sum to 100 due to rounding.')
    if counts['total'] < 20:
        print('Small numbers: one more or one fewer death changes these shares a lot.')


def show_about():
    """Print data sources, definitions, and notes."""
    print(f'''
=== About this data ===

Crashes:     SWITRS collision records for San Diego County (SANDAG),
             {FIRST_YEAR}–{LAST_YEAR}. 2023 is excluded: its records have no
             location data and the year appears incomplete.

Risk (EPDO): Each crash is weighted by severity using FHWA national
             comprehensive crash costs (2024 dollars). A property-damage-only
             crash counts as 1; a fatal crash counts as about 883.

Crash cost:  EPDO multiplied by the cost of a property-damage-only crash
             ($18,100), giving an estimated societal cost.

KSI:         Killed or seriously injured. KSI crashes are fatal and
             severe-injury crashes; people KSI counts every person killed
             or severely injured.

Cause:       The primary collision factor recorded by the reporting officer.

Population:  2020 Census, SANDAG jurisdiction estimates. Tribal reservations
             and some other locations have no population figure and are not
             included in per-resident rankings.

Road type:   "Local roads" excludes state highways and freeways (Caltrans).
             85 crashes with no road type recorded are excluded from that view.

Road names:  As recorded in crash reports. The same road may appear under
             more than one name, so road rankings are approximate.

Note:        Population is a rough measure of exposure. Places with freeways
             or many visitors may show higher per-resident rates. Small cities
             can swing a lot from just a few serious crashes.''')


# ---------- Asking the user ----------
def ask_year():
    """Ask for a year in range. Return it, or None if the input is invalid."""
    answer = input(f'Which year ({FIRST_YEAR}–{LAST_YEAR})? ')
    try:
        year = int(answer)
    except ValueError:
        print('Please enter a year as a number, like 2019.')
        return None

    if year < FIRST_YEAR or year > LAST_YEAR:
        print(f'Please choose a year between {FIRST_YEAR} and {LAST_YEAR}.')
        return None
    return year


def ask_location(a):
    """Ask for a location name, ignoring capitalization.

    Return the name as spelled in the data, or None if it isn't found.
    """
    answer = input('Which location? ').strip().lower()

    locations = {}
    for name in a.get_unique_values('location'):
        locations[name.lower()] = name

    if answer in locations:
        return locations[answer]

    print(f'"{answer}" was not found. Choose option 5 to see all locations.')
    return None


def ask_count(current):
    """Ask how many rows ranking tables should show. Keep current if invalid."""
    answer = input(f'How many rows should ranking tables show (currently {current})? ').strip()
    try:
        n = int(answer)
    except ValueError:
        print('Please enter a whole number, like 20.')
        return current

    if n < 1:
        print('Please enter a number of 1 or more.')
        return current
    return n


# ---------- Report menu (works for any analyzer) ----------
def report_menu(a, title, show_locations=True):
    """Show the report menu for one selection of data.

    a:              the analyzer to report on (full or filtered)
    title:          shown at the top of the menu and in saved file names
    show_locations: True for county and year views (location rankings);
                    False for a single location (road rankings instead)
    """
    # A dictionary, so the nested functions below can change the value
    settings = {'top_n': 10}

    # Individual reports: (label shown to the user, function to run)
    reports = []
    if show_locations:
        reports.append(('Top locations by total risk',
                        lambda a: show_top_locations(a, settings['top_n'])))
        reports.append(('Top locations by risk per 1,000 residents',
                        lambda a: show_risk_per_1000(a, settings['top_n'])))
    else:
        reports.append(('Most dangerous roads',
                        lambda a: show_top_roads(a, settings['top_n'])))
    reports.append(('Killed or seriously injured (KSI) by year', show_ksi_by_year))
    reports.append(('Leading crash causes',
                    lambda a: show_top_causes(a, settings['top_n'])))
    reports.append(('Crash cost by year', show_cost_by_year))
    reports.append(('Deaths by road user', show_deaths))

    def change_count(a):
        settings['top_n'] = ask_count(settings['top_n'])
        print(f'Ranking tables will show the top {settings["top_n"]}.')

    def full_report(a):
        print(f'\n{"#" * 60}\n{title}: Full report\n{"#" * 60}')
        for label, function in reports:
            print(f'\n=== {label} ===')
            function(a)
        show_about()

    def save_report(a):
        filename = os.path.join(HERE, title.replace(', ', '_').replace(' ', '_').replace('–', '-')
                    .replace('(', '').replace(')', '') + '.txt')
        with open(filename, 'w', encoding='utf-8') as file:
            with redirect_stdout(file):
                full_report(a)
        print(f'\nSaved to {os.path.abspath(filename)}')

    options = reports + [
        ('Full report (all tables)', full_report),
        ('Save full report to a text file', save_report),
        ('Change how many rows ranking tables show', change_count),
    ]

    back_number = len(options) + 1

    while True:
        print(f'\n=== {title} ===')
        print(f'(Ranking tables show the top {settings["top_n"]})')
        for number, (label, function) in enumerate(options, start=1):
            print(f'{number}. {label}')
        print(f'{back_number}. Back to main menu')

        choice = input('\nChoose a report: ').strip()

        if choice == str(back_number):
            break

        try:
            number = int(choice)
            if number < 1:
                raise IndexError
            label, function = options[number - 1]
        except (ValueError, IndexError):
            print('Please choose a number from the menu.')
            continue

        function(a)
        input('\nPress Enter to continue...')


# ---------- Program start ----------
print('Loading collision data...')
analyzer = SafetyAnalyzer()
analyzer.open_file_and_add_dict(FILENAME, last_year=LAST_YEAR)
analyzer.load_population(POPULATION_FILE)
print(f'Loaded {len(analyzer.collision_records):,} crashes ({FIRST_YEAR}–{LAST_YEAR}).')

# Build the local-roads version once, so switching is instant
local_analyzer = analyzer.filter_by('road_type', 'Local road')
local_only = False

while True:
    # Everything below uses whichever dataset the switch points to
    data = local_analyzer if local_only else analyzer
    scope = 'local roads' if local_only else 'all roads'

    print(f'\n=== San Diego County Road Safety, {FIRST_YEAR}–{LAST_YEAR} ({scope}) ===')
    print('1. Whole county')
    print('2. Filter by year')
    print('3. Filter by location')
    if local_only:
        print('4. Switch to all roads')
    else:
        print('4. Switch to local roads only')
    print('5. List all locations')
    print('6. About this data')
    print('7. Quit')

    choice = input('\nChoose an option: ').strip()

    if choice == '1':
        report_menu(data, f'San Diego County, {FIRST_YEAR}–{LAST_YEAR} ({scope})')

    elif choice == '2':
        year = ask_year()
        if year is not None:
            report_menu(data.filter_by('year', year), f'San Diego County, {year} ({scope})')

    elif choice == '3':
        location = ask_location(data)
        if location is not None:
            report_menu(data.filter_by('location', location),
                        f'{location}, {FIRST_YEAR}–{LAST_YEAR} ({scope})',
                        show_locations=False)

    elif choice == '4':
        local_only = not local_only
        if local_only:
            print('\nNow showing local roads only. State highways and freeways are excluded.')
        else:
            print('\nNow showing all roads.')

    elif choice == '5':
        for name in sorted(data.get_unique_values('location')):
            print(name)
        input('\nPress Enter to continue...')

    elif choice == '6':
        show_about()
        input('\nPress Enter to continue...')

    elif choice == '7':
        print('Goodbye!')
        break

    else:
        print('Please choose a number from the menu.')