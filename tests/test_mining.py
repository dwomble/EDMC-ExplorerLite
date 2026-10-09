from explorer.valuation import mining

def test_ground_rocky_volcanism():
    assert mining.ground_type('Rocky body', 'minor metallic magma volcanism') == 'rocky metallic magma'
    assert mining.ground_type('Rocky body', 'major silicate vapour geysers volcanism') == 'rocky silicate vapour'
    assert mining.ground_type('Rocky body', '') == 'rocky none'

def test_ground_class_ignores_volcanism():
    assert mining.ground_type('Metal rich body', 'metallic magma volcanism') == 'metal rich'
    assert mining.ground_type('Gas giant', None) is None

def test_watched_rates_sorted():
    hits = mining.watched_rates('Icy body', None, {'deuterium', 'water', 'gold'})
    assert [n for n, _ in hits] == ['Water', 'Deuterium']

def test_watch_aliases():
    assert mining.parse_watch('Low Temperature Diamonds, Bastnäsite, helium 3, Sulfur') == {
        'lowtempdiamonds', 'bastnasite', 'helium3', 'sulphur'}
    assert [n for n, _ in mining.watched_rates('Icy body', None, mining.parse_watch('LTD'))] == ['Low Temp Diamonds']

def test_unknown_names_suggest():
    assert mining.unknown_names('Platinum, Platinun, Zzzz', mining.known_commodities()) == [('Platinun', 'Platinum'), ('Zzzz', None)]
    assert mining.unknown_names('Antimony, sulfur', list(mining.MATERIALS)) == []

def test_short_names():
    assert [mining.short(n) for n in ('Platinum', 'Low Temp Diamonds', 'Helium-3', 'Tin')] == ['Plat.', 'LTD.', 'Heli-3', 'Tin']

def test_rates_data_valid():
    for g in mining.GROUNDS.values():
        assert g['sites'] > 0 and all(0 < p <= 100 for p in g['rates'].values())
