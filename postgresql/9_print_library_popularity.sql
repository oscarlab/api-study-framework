CREATE TYPE output AS (symbol VARCHAR, popularity FLOAT);

CREATE FUNCTION query_output()
RETURNS SETOF output AS $$
DECLARE
	p INT := id FROM package_id WHERE package_name = 'libc6';

BEGIN

	RETURN QUERY
	SELECT DISTINCT t2.symbol_name, t1.popularity
	FROM call_popularity AS t1
	RIGHT JOIN
	libc_symbol AS t2
	ON t1.bin_id = t2.bin_id AND t1.func_addr = t2.func_addr
	ORDER BY t1.popularity DESC, t2.symbol_name;

END
$$ LANGUAGE plpgsql;

\copy (SELECT * FROM query_output()) TO '/tmp/libc-popularity.csv' WITH CSV
\echo 'Output to /tmp/libc-popularity.csv'

DROP FUNCTION query_output();
DROP TYPE output CASCADE;
