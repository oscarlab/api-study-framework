CREATE TYPE output AS (executable_type VARCHAR, popularity INT);

CREATE OR REPLACE FUNCTION query_output()
RETURNS SETOF output AS $$
DECLARE
	r output%ROWTYPE;

BEGIN
	FOR r IN (
		SELECT concat('ELF Binary'), count(*)
		FROM binary_list WHERE type = 'exe'
	) LOOP
		RETURN NEXT r;
	END LOOP;

	FOR r IN (
		SELECT concat('Scripts'), count(*)
		FROM binary_list WHERE type = 'scr'
	) LOOP
		RETURN NEXT r;
	END LOOP;

	CREATE TEMP TABLE exetype (executable_type VARCHAR, popularity INT);

	INSERT INTO exetype
		SELECT t2.binary_name, count(*)
		FROM binary_interp AS t1 INNER JOIN binary_id AS t2
		ON t1.interp = t2.id
		GROUP BY t2.binary_name;

	For r IN (
		SELECT concat('Python') AS executable_type, sum(popularity)
		FROM exetype WHERE executable_type LIKE '%python%'
	) LOOP
		RETURN NEXT r;
	END LOOP;

	For r IN (
		SELECT concat('Perl') AS executable_type, sum(popularity)
		FROM exetype WHERE executable_type LIKE '%perl%'
	) LOOP
		RETURN NEXT r;
	END LOOP;

	For r IN (
		SELECT concat('Ruby') AS executable_type, sum(popularity)
		FROM exetype WHERE executable_type LIKE '%ruby%'
	) LOOP
		RETURN NEXT r;
	END LOOP;

	For r IN (
		SELECT concat('Dash') AS executable_type, sum(popularity)
		FROM exetype WHERE executable_type = '/bin/sh' OR executable_type = '/bin/dash'
	) LOOP
		RETURN NEXT r;
	END LOOP;

	FOR r IN (
		SELECT concat('Bash') AS executable_type, sum(popularity)
		FROM exetype WHERE executable_type = '/bin/bash'
	) LOOP
		RETURN NEXT r;
	END LOOP;

	DROP TABLE exetype;

	RETURN;
END
$$ LANGUAGE plpgsql;

\copy (SELECT * FROM query_output()) TO '/tmp/executable-types.csv' WITH CSV
\echo 'Output to /tmp/executable-types.csv'

DROP FUNCTION query_output();
DROP TYPE output CASCADE;
