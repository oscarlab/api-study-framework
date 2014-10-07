CREATE TYPE output AS (symbol VARCHAR, popularity FLOAT);

CREATE FUNCTION query_output(libpkg VARCHAR, libname VARCHAR)
RETURNS SETOF output AS $$
DECLARE
	p INT := (SELECT id FROM package_id WHERE package_name = libpkg);
	b INT := (SELECT id FROM binary_id  WHERE binary_name  = libname);

BEGIN

	RETURN QUERY
	SELECT DISTINCT t2.symbol_name, t1.popularity
	FROM call_popularity AS t1
	INNER JOIN
	binary_symbol AS t2
	ON  t1.pkg_id = p AND t2.bin_id = b
	AND t1.pkg_id = p AND t1.bin_id = b
	ORDER BY popularity DESC, symbol_name;

END
$$ LANGUAGE plpgsql;

\copy (SELECT * FROM query_output('libc6', '/lib/x86_64-linux-gnu/libc-2.15.so')) TO '/tmp/libc-popularity.csv' WITH CSV
\echo 'Output to /tmp/libc-popularity.csv'

\copy (SELECT * FROM query_output('libc6', '/lib/x86_64-linux-gnu/ld-2.15.so')) TO '/tmp/ld-popularity.csv' WITH CSV
\echo 'Output to /tmp/ld-popularity.csv'

DROP FUNCTION query_output(libpkg VARCHAR, libname VARCHAR);
DROP TYPE output CASCADE;
