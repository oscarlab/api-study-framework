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
	d INT;
	c INT;
	inst INT;
	internal BOOLEAN;

BEGIN
	CREATE TEMP TABLE IF NOT EXISTS call_tmp (
		bin_id INT NOT NULL, func_addr INT NOT NULL,
		popularity FLOAT,
		popularity_with_internal FLOAT,
		PRIMARY KEY(bin_id, func_addr));
	INSERT INTO call_tmp
		SELECT DISTINCT dep_bin_id, call, 0.0, 0.0 FROM package_call
		WHERE dep_pkg_id = p;

	FOR d, c, inst, internal IN (
		SELECT
		t1.dep_bin_id, t1.call, t3.inst,
		bool_or(t1.by_pkg_id = p)
		FROM
		package_call AS t1 INNER JOIN package_id AS t2
		ON  t1.dep_pkg_id = p
		AND t1.pkg_id = t2.id
		INNER JOIN package_popularity AS t3
		ON  t2.package_name = t3.package_name
		AND t3.inst != 0
		GROUP BY t1.dep_bin_id, t1.call, t3.inst
	) LOOP
		UPDATE call_tmp SET
		popularity = add_pop(popularity, inst, total)
		WHERE func_addr = c;

		IF internal THEN
			UPDATE call_tmp SET
			popularity_with_internal =
			add_pop(popularity_with_internal, inst, total)
			WHERE func_addr = c;
		END IF;
	END LOOP;

	DELETE FROM call_popularity WHERE pkg_id = p;
	INSERT INTO call_popularity
		SELECT p, bin_id, func_addr,
		get_pop(popularity) AS popularity,
		get_pop(popularity_with_internal) AS popularity_with_internal
		FROM call_tmp
		ORDER BY popularity_with_internal DESC, func_addr;

	TRUNCATE TABLE call_tmp;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analysis_syscall_popularity(p INT)
RETURNS void AS $$

DECLARE
	libc INT := id FROM package_id WHERE package_name = 'libc6';
	total INT := inst FROM package_popularity WHERE package_name = 'Total';
	s SMALLINT;
	inst INT;
	is_libc BOOLEAN;

BEGIN
	CREATE TEMP TABLE IF NOT EXISTS syscall_tmp (
		syscall SMALLINT NOT NULL,
		popularity FLOAT,
		popularity_with_libc FLOAT,
		PRIMARY KEY(syscall));
	INSERT INTO syscall_tmp
		SELECT DISTINCT syscall, 0.0, 0.0 FROM package_syscall;

	FOR s, inst, is_libc IN (
		SELECT
		t1.syscall, t3.inst,
		bool_or(t1.by_pkg_id = libc)
		FROM
		package_syscall AS t1 INNER JOIN package_id AS t2
		ON  t1.pkg_id = t2.id
		INNER JOIN package_popularity AS t3
		ON  t2.package_name = t3.package_name
		AND t3.inst != 0
		GROUP BY t1.syscall, t3.inst
	) LOOP
		UPDATE syscall_tmp SET
		popularity = add_pop(popularity, inst, total)
		WHERE syscall = s;

		IF is_libc THEN
			UPDATE syscall_tmp SET
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
		ORDER BY popularity_with_libc DESC, syscall;

	TRUNCATE TABLE syscall_tmp;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analysis_vecsyscall_popularity(p INT)
RETURNS void AS $$

DECLARE
	libc INT := id FROM package_id WHERE package_name = 'libc6';
	total INT := inst FROM package_popularity WHERE package_name = 'Total';
	s SMALLINT;
	r BIGINT;
	inst INT;
	is_libc BOOLEAN;

BEGIN
	CREATE TEMP TABLE IF NOT EXISTS vecsyscall_tmp (
		vecsyscall SMALLINT NOT NULL,
		request BIGINT NOT NULL,
		popularity FLOAT,
		popularity_with_libc FLOAT,
		PRIMARY KEY(syscall, request));
	INSERT INTO vecsyscall_tmp
		SELECT DISTINCT syscall, request, 0.0, 0.0 FROM package_vecsyscall;

	FOR s, r, inst, is_libc IN (
		SELECT
		t1.syscall, t1.request, t3.inst,
		bool_or(t1.by_pkg_id = libc)
		FROM
		package_vecsyscall AS t1 INNER JOIN package_id AS t2
		ON  t1.pkg_id = t2.id
		INNER JOIN package_popularity AS t3
		ON  t2.package_name = t3.package_name
		AND t3.inst != 0
		GROUP BY t1.syscall, t1.request, t3.inst
	) LOOP
		UPDATE vecsyscall_tmp SET
		popularity = add_pop(popularity, inst, total)
		WHERE syscall = s AND request = r;

		IF is_libc THEN
			UPDATE vecsyscall_tmp SET
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
		ORDER BY syscall, popularity_with_libc DESC, request;

	TRUNCATE TABLE vecsyscall_tmp;
END
$$ LANGUAGE plpgsql;
