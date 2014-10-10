CREATE OR REPLACE FUNCTION analysis_compatibility(
	syscalls INT[]
)
RETURNS FLOAT AS $$

DECLARE
	total INT := inst FROM package_popularity WHERE package_name = 'Total';
	compat FLOAT := 0.0;
	p INT;
	x FLOAT;

BEGIN
	IF NOT temp_table_exists('pop_tmp') THEN
		CREATE TEMP TABLE IF NOT EXISTS pop_tmp (
			pkg_id INT NOT NULL PRIMARY KEY, pop FLOAT);
		INSERT INTO pop_tmp
			SELECT t1.id, add_pop(t2.inst, total) FROM
			package_id AS t1 INNER JOIN package_popularity AS t2
			ON t1.package_name = t2.package_name;
	END IF;

	FOR p IN (
		SELECT DISTINCT pkg_id
		FROM package_syscall
		WHERE syscall != ALL(syscalls)
	) LOOP
		compat := compat + (SELECT pop FROM pop_tmp WHERE pkg_id = p);
	END LOOP;

	RETURN 10.0 ^ (-compat);
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analysis_syscall_compatibility()
RETURNS SETOF FLOAT AS $$

DECLARE
	syscalls INT[];
	s INT;
	i INT := 0;

BEGIN
	FOR s IN (
		SELECT syscall FROM syscall_popularity
		ORDER BY popularity_with_libc DESC
	) LOOP
		RAISE NOTICE 'analyze %', s;
		syscalls := syscalls || s;
		RETURN NEXT (
			SELECT analysis_compatibility(syscalls)
		);
	END LOOP;
	RETURN;
END
$$ LANGUAGE plpgsql;
