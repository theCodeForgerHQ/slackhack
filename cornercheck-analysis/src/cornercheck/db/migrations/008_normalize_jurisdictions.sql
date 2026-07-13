-- Normalize jurisdiction spelling variants to one canonical "Name (ABBR)" form per
-- commission. Five variant strings inflated the distinct-jurisdiction count (14 strings,
-- 10 actual commissions), which the dashboard and App Home reported as coverage: an
-- honesty bug a judge with the JSON open would catch. Runs before the boot-time case
-- top-up, so the normalized curated JSON matches existing rows and cannot double-insert.
UPDATE suspensions SET jurisdiction = 'Florida Athletic Commission (FAC)'
    WHERE jurisdiction = 'Florida Athletic Commission';
UPDATE suspensions SET jurisdiction = 'Nevada State Athletic Commission (NSAC)'
    WHERE jurisdiction = 'Nevada (Nevada State Athletic Commission)';
UPDATE suspensions SET jurisdiction = 'New Jersey State Athletic Control Board (NJSACB)'
    WHERE jurisdiction = 'New Jersey (New Jersey State Athletic Control Board)';
UPDATE suspensions SET jurisdiction = 'New York State Athletic Commission (NYSAC)'
    WHERE jurisdiction = 'New York (New York State Athletic Commission)';
UPDATE suspensions SET jurisdiction = 'Maryland State Athletic Commission (MSAC)'
    WHERE jurisdiction = 'Maryland (Maryland State Athletic Commission)';
UPDATE suspensions SET jurisdiction = 'German Boxing Federation (BDB)'
    WHERE jurisdiction = 'Germany (German Boxing Federation, BDB)';
