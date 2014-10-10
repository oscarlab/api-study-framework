DO $$
BEGIN
IF NOT table_exists('call_popularity') THEN
	CREATE TABLE call_popularity (
		bin_id INT NOT NULL,
		func_addr INT NOT NULL,
		popularity FLOAT,
		PRIMARY KEY(bin_id, func_addr)
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

CREATE OR REPLACE FUNCTION add_pop(inst INT, total INT)
RETURNS FLOAT AS $$
BEGIN
	RETURN log(total) - log(total - inst);
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_pop(pop FLOAT)
RETURNS FLOAT AS $$
BEGIN
	IF pop > 6 THEN
		RETURN 1.0;
	ELSE
		RETURN 1.0 - 10.0 ^ (-pop);
	END IF;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analysis_call_popularity()
RETURNS void AS $$

DECLARE
	total INT := inst FROM package_popularity WHERE package_name = 'Total';
	p INT;
	d INT;
	c INT;
	x FLOAT;

BEGIN
	CREATE TEMP TABLE IF NOT EXISTS call_tmp (
		bin_id INT NOT NULL, func_addr INT NOT NULL,
		popularity FLOAT,
		PRIMARY KEY(bin_id, func_addr));
	INSERT INTO call_tmp
		SELECT DISTINCT dep_bin_id, call, 0.0 FROM package_call;

	CREATE TEMP TABLE IF NOT EXISTS pop_tmp (
		pkg_id INT NOT NULL PRIMARY KEY, pop FLOAT);
	INSERT INTO pop_tmp
		SELECT t1.id, add_pop(t2.inst, total) FROM
		package_id AS t1 INNER JOIN package_popularity AS t2
		ON t1.package_name = t2.package_name;

	FOR p, d, c IN (
		SELECT pkg_id, dep_bin_id, call
		FROM package_call
		GROUP BY pkg_id, dep_bin_id, call
	) LOOP
		x := (SELECT pop FROM pop_tmp WHERE pkg_id = p);
		UPDATE call_tmp SET
		popularity = popularity + x
		WHERE bin_id = d AND func_addr = c;
	END LOOP;

	TRUNCATE TABLE call_popularity;
	INSERT INTO call_popularity
		SELECT bin_id, func_addr,
		get_pop(popularity) AS popularity
		FROM call_tmp
		ORDER BY popularity DESC, func_addr;

	TRUNCATE TABLE call_tmp;
	TRUNCATE TABLE pop_tmp;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analysis_syscall_popularity()
RETURNS void AS $$

DECLARE
	total INT := inst FROM package_popularity WHERE package_name = 'Total';
	p INT;
	s SMALLINT;
	x FLOAT;
	is_libc BOOLEAN;

BEGIN
	CREATE TEMP TABLE IF NOT EXISTS syscall_tmp (
		syscall SMALLINT NOT NULL,
		popularity FLOAT,
		popularity_with_libc FLOAT,
		PRIMARY KEY(syscall));
	INSERT INTO syscall_tmp
		SELECT DISTINCT syscall, 0.0, 0.0 FROM package_syscall;

	CREATE TEMP TABLE IF NOT EXISTS pop_tmp (
		pkg_id INT NOT NULL PRIMARY KEY, pop FLOAT);
	INSERT INTO pop_tmp
		SELECT t1.id, add_pop(t2.inst, total) FROM
		package_id AS t1 INNER JOIN package_popularity AS t2
		ON t1.package_name = t2.package_name;

	FOR p, s, is_libc IN (
		SELECT pkg_id, syscall, bool_and(by_libc)
		FROM package_syscall
		GROUP BY pkg_id, syscall
	) LOOP
		x := (SELECT pop FROM pop_tmp WHERE pkg_id = p);

		IF is_libc THEN
			UPDATE syscall_tmp SET
			popularity_with_libc =
			popularity_with_libc + x
			WHERE syscall = s;
		ELSE
			UPDATE syscall_tmp SET
			popularity = popularity + x,
			popularity_with_libc =
			popularity_with_libc + x
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
	TRUNCATE TABLE pop_tmp;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analysis_vecsyscall_popularity()
RETURNS void AS $$

DECLARE
	total INT := inst FROM package_popularity WHERE package_name = 'Total';
	p INT;
	s SMALLINT;
	r BIGINT;
	x FLOAT;
	is_libc BOOLEAN;

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

	CREATE TEMP TABLE IF NOT EXISTS pop_tmp (
		pkg_id INT NOT NULL PRIMARY KEY, pop FLOAT);
	INSERT INTO pop_tmp
		SELECT t1.id, add_pop(t2.inst, total) FROM
		package_id AS t1 INNER JOIN package_popularity AS t2
		ON t1.package_name = t2.package_name;

	FOR p, s, r, is_libc IN (
		SELECT pkg_id, syscall, request, bool_and(by_libc)
		FROM package_vecsyscall
		GROUP BY pkg_id, syscall, request
	) LOOP
		x := (SELECT pop FROM pop_tmp WHERE pkg_id = p);

		IF is_libc THEN
			UPDATE vecsyscall_tmp SET
			popularity_with_libc =
			popularity_with_libc + x
			WHERE syscall = s AND request = r;
		ELSE
			UPDATE vecsyscall_tmp SET
			popularity = popularity + x,
			popularity_with_libc =
			popularity_with_libc + x
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
	TRUNCATE TABLE pop_tmp;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analysis_fileaccess_popularity()
RETURNS void AS $$

DECLARE
	total INT := inst FROM package_popularity WHERE package_name = 'Total';
	p INT;
	f VARCHAR;
	x FLOAT;
	is_libc BOOLEAN;

BEGIN
	CREATE TEMP TABLE IF NOT EXISTS package_fileaccess_tmp (
		pkg_id INT NOT NULL, file VARCHAR NOT NULL,
		by_libc BOOLEAN,
		PRIMARY KEY (pkg_id, file, by_libc));
	WITH RECURSIVE
	analysis (pkg_id, file, by_libc)
	AS (
		SELECT pkg_id, trim(trailing '/' from file), by_libc
		FROM package_fileaccess
		UNION
		SELECT pkg_id, regexp_replace(file, '/[^/]+$', ''), by_libc
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

	CREATE TEMP TABLE IF NOT EXISTS pop_tmp (
		pkg_id INT NOT NULL PRIMARY KEY, pop FLOAT);
	INSERT INTO pop_tmp
		SELECT t1.id, add_pop(t2.inst, total) FROM
		package_id AS t1 INNER JOIN package_popularity AS t2
		ON t1.package_name = t2.package_name;

	FOR p, f, is_libc IN (
		SELECT pkg_id, file, bool_and(by_libc)
		FROM package_fileaccess_tmp
		GROUP BY pkg_id, file
	) LOOP
		x := (SELECT pop FROM pop_tmp WHERE pkg_id = p);

		IF is_libc THEN
			UPDATE fileaccess_tmp SET
			popularity_with_libc =
			popularity_with_libc + x
			WHERE file = f;
		ELSE
			UPDATE fileaccess_tmp SET
			popularity = popularity + x,
			popularity_with_libc =
			popularity_with_libc + x
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
	TRUNCATE TABLE pop_tmp;
END
$$ LANGUAGE plpgsql;
