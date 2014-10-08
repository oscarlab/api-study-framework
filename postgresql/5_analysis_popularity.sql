DO $$
BEGIN
IF NOT table_exists('call_popularity') THEN
	CREATE TABLE call_popularity (
		pkg_id INT NOT NULL, bin_id INT NOT NULL,
		func_addr INT NOT NULL,
		popularity FLOAT,
		popularity_with_internal FLOAT,
		PRIMARY KEY(pkg_id, bin_id, func_addr)
	);
END IF;

IF NOT table_exists('syscall_popularity') THEN
	CREATE TABLE syscall_popularity (
		syscall SMALLINT NOT NULL,
		popularity FLOAT,
		popularity_with_libc FLOAT,
		PRIMARY KEY (syscall)
	);
END IF;

IF NOT table_exists('vecsyscall_popularity') THEN
	CREATE TABLE vecsyscall_popularity (
		syscall SMALLINT NOT NULL,
		request BIGINT NOT NULL,
		popularity FLOAT,
		popularity_with_libc FLOAT,
		PRIMARY KEY (syscall, request)
	);
END IF;

IF NOT table_exists('fileaccess_popularity') THEN
	CREATE TABLE fileaccess_popularity (
		file VARCHAR NOT NULL,
		popularity FLOAT,
		popularity_with_libc FLOAT,
		PRIMARY KEY (file)
	);
END IF;
END $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION add_pop(pop FLOAT, inst INT, total INT)
RETURNS FLOAT AS $$
BEGIN
	RETURN pop + log(total) - log(total - inst);
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_pop(pop FLOAT)
RETURNS FLOAT AS $$
BEGIN
	RETURN 1.0 - 10.0 ^ (-pop);
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analysis_call_popularity(p INT)
RETURNS void AS $$

DECLARE
	total INT := inst FROM package_popularity WHERE package_name = 'Total';
	q INT;
	d INT;
	c INT;
	inst INT;

BEGIN
	CREATE TEMP TABLE IF NOT EXISTS call_tmp (
		bin_id INT NOT NULL, func_addr INT NOT NULL,
		popularity FLOAT,
		popularity_with_internal FLOAT,
		PRIMARY KEY(bin_id, func_addr));
	INSERT INTO call_tmp
		SELECT DISTINCT dep_bin_id, call, 0.0, 0.0 FROM package_call
		WHERE dep_pkg_id = p;

	FOR q, d, c IN (
		SELECT DISTINCT pkg_id, dep_bin_id, call FROM package_call
		WHERE dep_pkg_id = p
	) LOOP
		inst := (
			SELECT t1.inst FROM
			package_popularity AS t1 INNER JOIN package_id AS t2
			ON  t2.id = q
			AND t1.package_name = t2.package_name
		);

		IF NOT EXISTS (
			SELECT * FROM package_call
			WHERE pkg_id = q AND bin_id = b AND call = c
			AND by_pkg_id != p
		) THEN
			UPDATE call_tmp SET
			popularity_with_internal =
			add_pop(popularity_with_internal, inst, total)
			WHERE bin_id = d AND func_addr = c;
		ELSE
			UPDATE call_tmp SET
			popularity = add_pop(popularity, inst, total),
			popularity_with_internal =
			add_pop(popularity_with_internal, inst, total)
			WHERE bin_id = d AND func_addr = c;
		END IF;
	END LOOP;

	DELETE FROM call_popularity WHERE pkg_id = p;
	INSERT INTO call_popularity
		SELECT p, bin_id, func_addr,
		get_pop(popularity) AS popularity,
		get_pop(popularity_with_internal) AS popularity_with_internal
		FROM call_tmp
		ORDER BY popularity DESC, func_addr;

	TRUNCATE TABLE call_tmp;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analysis_syscall_popularity()
RETURNS void AS $$

DECLARE
	libc INT := id FROM package_id WHERE package_name = 'libc6';
	total INT := inst FROM package_popularity WHERE package_name = 'Total';
	p INT;
	s SMALLINT;
	inst INT;

BEGIN
	CREATE TEMP TABLE IF NOT EXISTS syscall_tmp (
		syscall SMALLINT NOT NULL,
		popularity FLOAT,
		popularity_with_libc FLOAT,
		PRIMARY KEY(syscall));
	INSERT INTO syscall_tmp
		SELECT DISTINCT syscall, 0.0, 0.0 FROM package_syscall;

	FOR p, s IN (
		SELECT DISTINCT pkg_id, syscall FROM package_syscall
	) LOOP
		inst := (
			SELECT t1.inst FROM
			package_popularity AS t1 INNER JOIN package_id AS t2
			ON  t2.id = p
			AND t1.package_name = t2.package_name
		);

		IF NOT EXISTS (
			SELECT * FROM package_syscall
			WHERE pkg_id = p AND syscall = s
			AND by_pkg_id != libc
		) THEN
			UPDATE syscall_tmp SET
			popularity_with_libc =
			add_pop(popularity_with_libc, inst, total)
			WHERE syscall = s;
		ELSE
			UPDATE syscall_tmp SET
			popularity = add_pop(popularity, inst, total),
			popularity_with_libc =
			add_pop(popularity_with_libc, inst, total)
			WHERE syscall = s;
		END IF;
	END LOOP;

	TRUNCATE TABLE syscall_popularity;
	INSERT INTO syscall_popularity
		SELECT syscall,
		get_pop(popularity) AS popularity,
		get_pop(popularity_with_libc) AS popularity_with_libc
		FROM syscall_tmp
		ORDER BY popularity DESC, syscall;

	TRUNCATE TABLE syscall_tmp;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analysis_vecsyscall_popularity()
RETURNS void AS $$

DECLARE
	libc INT := id FROM package_id WHERE package_name = 'libc6';
	total INT := inst FROM package_popularity WHERE package_name = 'Total';
	p INT;
	s SMALLINT;
	r BIGINT;
	inst INT;

BEGIN
	CREATE TEMP TABLE IF NOT EXISTS vecsyscall_tmp (
		syscall SMALLINT NOT NULL,
		request BIGINT NOT NULL,
		popularity FLOAT,
		popularity_with_libc FLOAT,
		PRIMARY KEY(syscall, request));
	INSERT INTO vecsyscall_tmp
		SELECT DISTINCT syscall, request, 0.0, 0.0
		FROM package_vecsyscall;

	FOR p, s, r IN (
		SELECT DISTINCT pkg_id, syscall, request FROM package_vecsyscall
	) LOOP
		inst := (
			SELECT t1.inst FROM
			package_popularity AS t1 INNER JOIN package_id AS t2
			ON  t2.id = p
			AND t1.package_name = t2.package_name
		);

		IF NOT EXISTS (
			SELECT * FROM package_vecsyscall
			WHERE pkg_id = p AND syscall = s AND request = r
			AND by_pkg_id != libc
		) THEN
			UPDATE vecsyscall_tmp SET
			popularity_with_libc =
			add_pop(popularity_with_libc, inst, total)
			WHERE syscall = s AND request = r;
		ELSE
			UPDATE vecsyscall_tmp SET
			popularity = add_pop(popularity, inst, total),
			popularity_with_libc =
			add_pop(popularity_with_libc, inst, total)
			WHERE syscall = s AND request = r;
		END IF;
	END LOOP;

	TRUNCATE TABLE vecsyscall_popularity;
	INSERT INTO vecsyscall_popularity
		SELECT syscall, request,
		get_pop(popularity) AS popularity,
		get_pop(popularity_with_libc) AS popularity_with_libc
		FROM vecsyscall_tmp
		ORDER BY syscall, popularity DESC, request;

	TRUNCATE TABLE vecsyscall_tmp;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analysis_fileaccess_popularity()
RETURNS void AS $$

DECLARE
	libc INT := id FROM package_id WHERE package_name = 'libc6';
	total INT := inst FROM package_popularity WHERE package_name = 'Total';
	p INT;
	f VARCHAR;
	inst INT;
	is_libc BOOLEAN;

BEGIN
	CREATE TEMP TABLE IF NOT EXISTS package_fileaccess_tmp (
		pkg_id INT NOT NULL, file VARCHAR NOT NULL,
		by_pkg_id INT NOT NULL,
		PRIMARY KEY (pkg_id, file, by_pkg_id));
	WITH RECURSIVE
	analysis (pkg_id, file, by_pkg_id)
	AS (
		SELECT pkg_id, trim(trailing '/' from file), by_pkg_id
		FROM package_fileaccess
		UNION
		SELECT pkg_id, regexp_replace(file, '/[^/]+$', ''), by_pkg_id
		FROM analysis WHERE file != ''
	)
	INSERT INTO package_fileaccess_tmp
		SELECT * FROM analysis WHERE file != '';

	CREATE TEMP TABLE IF NOT EXISTS fileaccess_tmp (
		file VARCHAR NOT NULL,
		popularity FLOAT,
		popularity_with_libc FLOAT,
		PRIMARY KEY(file));
	INSERT INTO fileaccess_tmp
		SELECT DISTINCT file, 0.0, 0.0 FROM package_fileaccess_tmp;

	FOR p, f IN (
		SELECT DISTINCT pkg_id, file FROM package_fileaccess
	) LOOP
		inst := (
			SELECT t1.inst FROM
			package_popularity AS t1 INNER JOIN package_id AS t2
			ON  t2.id = p
			AND t1.package_name = t2.package_name
		);

		IF NOT EXISTS (
			SELECT * FROM package_fileaccess
			WHERE pkg_id = p AND file = f
			AND by_pkg_id != libc
		) THEN
			UPDATE fileaccess_tmp SET
			popularity_with_libc =
			add_pop(popularity_with_libc, inst, total)
			WHERE file = f;
		ELSE
			UPDATE fileaccess_tmp SET
			popularity = add_pop(popularity, inst, total),
			popularity_with_libc =
			add_pop(popularity_with_libc, inst, total)
			WHERE file = f;
		END IF;
	END LOOP;

	TRUNCATE TABLE fileaccess_popularity;
	INSERT INTO fileaccess_popularity
		SELECT file,
		get_pop(popularity) AS popularity,
		get_pop(popularity_with_libc) AS popularity_with_libc
		FROM fileaccess_tmp
		ORDER BY popularity DESC, file;

	TRUNCATE TABLE package_fileaccess_tmp;
	TRUNCATE TABLE fileaccess_tmp;
END
$$ LANGUAGE plpgsql;
