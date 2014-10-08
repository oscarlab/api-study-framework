CREATE TYPE output AS (file_name VARCHAR, symbol VARCHAR, popularity FLOAT);

CREATE FUNCTION query_output(libpkg VARCHAR)
RETURNS SETOF output AS $$
DECLARE
	p INT := (SELECT id FROM package_id WHERE package_name = libpkg);

BEGIN

	RETURN QUERY
	SELECT DISTINCT t3.file_name, t2.symbol_name, t1.popularity
	FROM call_popularity AS t1
	INNER JOIN
	binary_symbol AS t2
	ON t1.pkg_id = p AND t2.pkg_id = p AND t1.bin_id = t2.bin_id
	INNER JOIN
	binary_id AS t3
	ON t1.bin_id = t3.id
	ORDER BY t1.popularity DESC, t3.file_name, t2.symbol_name;

END
$$ LANGUAGE plpgsql;

\copy (SELECT * FROM query_output('libc6')) TO '/tmp/libc-popularity.csv' WITH CSV
\echo 'Output to /tmp/libc-popularity.csv'

DROP FUNCTION query_output(libpkg VARCHAR);
DROP TYPE output CASCADE;
