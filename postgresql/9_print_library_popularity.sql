CREATE TYPE output AS (symbol VARCHAR, popularity FLOAT);

CREATE FUNCTION query_output()
RETURNS SETOF output AS $$
DECLARE
	p INT := id FROM package_id WHERE package_name = 'libc6';

BEGIN

	RETURN QUERY
	SELECT DISTINCT t2.symbol_name, t1.popularity
	FROM call_popularity AS t1
	INNER JOIN
	binary_symbol AS t2
	ON t1.bin_id = t2.bin_id
	WHERE t1.popularity >= 0.000001
	AND   t2.pkg_id = p AND t1.bin_id = t2.bin_id
	ORDER BY t1.popularity DESC, t2.symbol_name;

END
$$ LANGUAGE plpgsql;

\copy (SELECT * FROM query_output()) TO '/tmp/libc-popularity.csv' WITH CSV
\echo 'Output to /tmp/libc-popularity.csv'

DROP FUNCTION query_output();
DROP TYPE output CASCADE;
