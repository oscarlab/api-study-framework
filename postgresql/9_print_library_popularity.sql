CREATE TYPE output AS (symbol VARCHAR, popularity FLOAT);

CREATE FUNCTION query_output()
RETURNS SETOF output AS $$
DECLARE
	p INT := id FROM package_id WHERE package_name = 'libc6';

BEGIN
	RETURN QUERY
	SELECT DISTINCT t2.symbol_name AS symbol_name, t1.popularity AS popularity
	FROM call_popularity AS t1
	RIGHT JOIN
	libc_symbol AS t2
	ON t1.bin_id = t2.bin_id AND t1.func_addr = t2.func_addr
	ORDER BY t1.popularity DESC, t2.symbol_name;

END
$$ LANGUAGE plpgsql;

CREATE FUNCTION query_output_by_vote()
RETURNS SETOF output AS $$
DECLARE
	p INT := id FROM package_id WHERE package_name = 'libc6';

BEGIN
	RETURN QUERY
	SELECT DISTINCT t2.symbol_name AS symbol_name, t1.popularity AS popularity
	FROM call_popularity_by_vote AS t1
	RIGHT JOIN
	libc_symbol AS t2
	ON t1.bin_id = t2.bin_id AND t1.func_addr = t2.func_addr
	ORDER BY t1.popularity DESC, t2.symbol_name;

END
$$ LANGUAGE plpgsql;

\copy (SELECT t1.symbol, get_pop(t1.popularity) AS by_inst, get_pop(t2.popularity) AS by_vote FROM query_output() AS t1 JOIN query_output_by_vote() AS t2 ON t1.symbol = t2.symbol) TO '/tmp/libc-popularity.csv' WITH CSV HEADER
\echo 'Output to /tmp/libc-popularity.csv'

DROP FUNCTION query_output();
DROP FUNCTION query_output_by_vote();
DROP TYPE output CASCADE;
