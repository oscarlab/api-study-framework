DO $$
BEGIN
IF NOT table_exists('call_popularity') THEN
	CREATE TABLE call_popularity (
		bin_id INT NOT NULL,
		call VARCHAR NOT NULL,
		popularity FLOAT,
		PRIMARY KEY(bin_id, call)
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

IF NOT table_exists('call_popularity_by_vote') THEN
	CREATE TABLE call_popularity_by_vote (
		bin_id INT NOT NULL,
		call VARCHAR NOT NULL,
		popularity FLOAT,
		PRIMARY KEY(bin_id, call)
	);
END IF;

IF NOT table_exists('syscall_popularity_by_vote') THEN
	CREATE TABLE syscall_popularity_by_vote (
		syscall SMALLINT NOT NULL,
		popularity FLOAT,
		popularity_with_libc FLOAT,
		PRIMARY KEY (syscall)
	);
END IF;

IF NOT table_exists('vecsyscall_popularity_by_vote') THEN
	CREATE TABLE vecsyscall_popularity_by_vote (
		syscall SMALLINT NOT NULL,
		request BIGINT NOT NULL,
		popularity FLOAT,
		popularity_with_libc FLOAT,
		PRIMARY KEY (syscall, request)
	);
END IF;

IF NOT table_exists('fileaccess_popularity_by_vote') THEN
	CREATE TABLE fileaccess_popularity_by_vote (
		file VARCHAR NOT NULL,
		popularity FLOAT,
		popularity_with_libc FLOAT,
		PRIMARY KEY (file)
	);
END IF;
END $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analysis_call_popularity()
RETURNS void AS $$

DECLARE
	total INT := (SELECT COUNT(DISTINCT pkg_id) FROM package_call);
	count INT := 1;
	p INT;
	d INT;
	c INT;
	x FLOAT;
	y FLOAT;
BEGIN
	CREATE TEMP TABLE IF NOT EXISTS call_tmp (
		bin_id INT NOT NULL, func_addr INT NOT NULL,
		popularity FLOAT,
		popularity_by_vote FLOAT,
		PRIMARY KEY(bin_id, func_addr));

	CREATE TEMP TABLE IF NOT EXISTS pkg_call_tmp (
		bin_id INT NOT NULL, func_addr INT NOT NULL,
		PRIMARY KEY(bin_id, func_addr));

	FOR p IN (SELECT DISTINCT pkg_id FROM package_call) LOOP

		RAISE NOTICE 'analyze package %/%', count, total;
		count := count + 1;

		INSERT INTO pkg_call_tmp
			SELECT t2.bin_id, t2.func_addr FROM
			package_call AS t1 INNER JOIN libc_symbol AS t2
			ON t1.dep_bin_id = t2.bin_id AND t1.call = t2.func_addr
			WHERE t1.pkg_id = p;

		x := (SELECT inst FROM package_inst WHERE pkg_id = p);
		y := (SELECT vote FROM package_vote WHERE pkg_id = p);

		FOR d, c IN (SELECT * FROM pkg_call_tmp) LOOP
			IF EXISTS(
				SELECT * FROM call_tmp WHERE
				bin_id = d AND func_addr = c
			) THEN
				UPDATE call_tmp
				SET popularity = popularity + x,
				popularity_by_vote = popularity_by_vote + y
				WHERE bin_id = d AND func_addr = c;
			ELSE
				INSERT INTO call_tmp VALUES (d, c, x, y);
			END IF;
		END LOOP;

		TRUNCATE pkg_call_tmp;
	END LOOP;

	TRUNCATE TABLE call_popularity;
	INSERT INTO call_popularity
		SELECT t1.bin_id, t2,symbol_name,
		t1.popularity
		FROM call_tmp AS t1
		JOIN
		binary_symbol AS t2
		ON
		t1.bin_id = t2.bin_id AND t1.func_addr = t2.func_addr
		ORDER BY t1.popularity DESC, t1.func_addr;

	TRUNCATE TABLE call_popularity_by_vote;
	INSERT INTO call_popularity_by_vote
		SELECT t1.bin_id, t2.symbol_name,
		t1.popularity_by_vote
		FROM call_tmp AS t1
		JOIN
		binary_symbol AS t2
		ON
		t1.bin_id = t2.bin_id AND t1.func_addr = t2.func_addr
		ORDER BY t1.popularity_by_vote DESC, t1.func_addr;

	TRUNCATE TABLE call_tmp;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analysis_syscall_popularity()
RETURNS void AS $$

DECLARE
	total INT := (SELECT COUNT(DISTINCT pkg_id) FROM package_syscall);
	count INT := 1;
	p INT;
	s SMALLINT;
	x FLOAT;
	y FLOAT;
	x2 FLOAT;
	y2 FLOAT;
	is_libc BOOLEAN;

BEGIN
	CREATE TEMP TABLE IF NOT EXISTS syscall_tmp (
		syscall SMALLINT NOT NULL,
		popularity FLOAT,
		popularity_with_libc FLOAT,
		popularity_by_vote FLOAT,
		popularity_with_libc_by_vote FLOAT,
		PRIMARY KEY(syscall));

	CREATE TEMP TABLE IF NOT EXISTS pkg_syscall_tmp (
		syscall SMALLINT NOT NULL, is_libc BOOLEAN,
		PRIMARY KEY(syscall));

	FOR p IN (SELECT DISTINCT pkg_id FROM package_syscall) LOOP

		RAISE NOTICE 'analyze package %/%', count, total;
		count := count + 1;

		INSERT INTO pkg_syscall_tmp
			SELECT syscall, bool_and(by_libc)
			FROM package_syscall
			WHERE pkg_id = p
			GROUP BY syscall;

		x := (SELECT inst FROM package_inst WHERE pkg_id = p);
		y := (SELECT vote FROM package_vote WHERE pkg_id = p);

		for s, is_libc IN (SELECT * FROM pkg_syscall_tmp) LOOP
			IF is_libc THEN
				x2 := 0.0;
				y2 := 0.0;
			ELSE
				x2 := x;
				y2 := y;
			END IF;

			IF EXISTS(
				SELECT * FROM syscall_tmp WHERE syscall = s
			) THEN
				UPDATE syscall_tmp
				SET popularity = popularity + x2,
				popularity_with_libc = popularity_with_libc + x,
				popularity_by_vote = popularity_by_vote + y2,
				popularity_with_libc_by_vote = popularity_with_libc_by_vote + y
				WHERE syscall = s;
			ELSE
				INSERT INTO syscall_tmp VALUES (s, x2, x, y2, y);
			END IF;
		END LOOP;

		TRUNCATE pkg_syscall_tmp;
	END LOOP;

	TRUNCATE TABLE syscall_popularity;
	INSERT INTO syscall_popularity
		SELECT syscall,
		popularity,
		popularity_with_libc
		FROM syscall_tmp
		ORDER BY popularity DESC, syscall;

	TRUNCATE TABLE syscall_popularity_by_vote;
	INSERT INTO syscall_popularity_by_vote
		SELECT syscall,
		popularity_by_vote,
		popularity_with_libc_by_vote
		FROM syscall_tmp
		ORDER BY popularity_by_vote DESC, syscall;


	TRUNCATE TABLE syscall_tmp;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analysis_vecsyscall_popularity()
RETURNS void AS $$

DECLARE
	total INT := (SELECT COUNT(DISTINCT pkg_id) FROM package_vecsyscall);
	count INT := 1;
	p INT;
	s SMALLINT;
	r BIGINT;
	x FLOAT;
	y FLOAT;
	x2 FLOAT;
	y2 FLOAT;
	is_libc BOOLEAN;

BEGIN
	CREATE TEMP TABLE IF NOT EXISTS vecsyscall_tmp (
		syscall SMALLINT NOT NULL,
		request BIGINT NOT NULL,
		popularity FLOAT,
		popularity_with_libc FLOAT,
		popularity_by_vote FLOAT,
		popularity_with_libc_by_vote FLOAT,
		PRIMARY KEY(syscall, request));

	CREATE TEMP TABLE IF NOT EXISTS pkg_vecsyscall_tmp (
		syscall SMALLINT NOT NULL,
		request BIGINT NOT NULL,
		is_libc BOOLEAN,
		PRIMARY KEY(syscall, request));

	FOR p IN (SELECT DISTINCT pkg_id FROM package_vecsyscall) LOOP

		RAISE NOTICE 'analyze package %/%', count, total;
		count := count + 1;

		INSERT INTO pkg_vecsyscall_tmp
			SELECT syscall, request, bool_and(by_libc)
			FROM package_vecsyscall
			WHERE pkg_id = p
			GROUP BY syscall, request;

		x := (SELECT inst FROM package_inst WHERE pkg_id = p);
		y := (SELECT vote FROM package_vote WHERE pkg_id = p);

		for s, r, is_libc IN (SELECT * FROM pkg_vecsyscall_tmp) LOOP
			IF is_libc THEN
				x2 := 0.0;
				y2 := 0.0;
			ELSE
				x2 := x;
				y2 := y;
			END IF;

			IF EXISTS(
				SELECT * FROM vecsyscall_tmp
				WHERE syscall = s AND request = r
			) THEN
				UPDATE vecsyscall_tmp
				SET popularity = popularity + x2,
				popularity_with_libc = popularity_with_libc + x,
				popularity_by_vote = popularity_by_vote + y2,
				popularity_with_libc_by_vote = popularity_with_libc_by_vote + y
				WHERE syscall = s AND request = r;
			ELSE
				INSERT INTO vecsyscall_tmp VALUES (s, r, x2, x, y2, y);
			END IF;
		END LOOP;

		TRUNCATE pkg_vecsyscall_tmp;
	END LOOP;

	TRUNCATE TABLE vecsyscall_popularity;
	INSERT INTO vecsyscall_popularity
		SELECT syscall, request,
		popularity,
		popularity_with_libc
		FROM vecsyscall_tmp
		ORDER BY syscall, popularity DESC, request;

	TRUNCATE TABLE vecsyscall_popularity_by_vote;
	INSERT INTO vecsyscall_popularity_by_vote
		SELECT syscall, request,
		popularity_by_vote,
		popularity_with_libc_by_vote
		FROM vecsyscall_tmp
		ORDER BY syscall, popularity_by_vote DESC, request;


	TRUNCATE TABLE vecsyscall_tmp;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analysis_fileaccess_popularity()
RETURNS void AS $$

DECLARE
	total INT := (SELECT COUNT(DISTINCT pkg_id) FROM package_fileaccess);
	count INT := 1;
	p INT;
	f VARCHAR;
	x FLOAT;
	y FLOAT;
	x2 FLOAT;
	y2 FLOAT;
	is_libc BOOLEAN;

BEGIN
	CREATE TEMP TABLE IF NOT EXISTS fileaccess_tmp (
		file VARCHAR NOT NULL,
		popularity FLOAT,
		popularity_with_libc FLOAT,
		popularity_by_vote FLOAT,
		popularity_with_libc_by_vote FLOAT,
		PRIMARY KEY(file));

	CREATE TEMP TABLE IF NOT EXISTS pkg_fileaccess_tmp (
		file VARCHAR NOT NULL, is_libc BOOLEAN,
		PRIMARY KEY(file));

	FOR p IN (SELECT DISTINCT pkg_id FROM package_fileaccess) LOOP

		RAISE NOTICE 'analyze package %/%', count, total;
		count := count + 1;

		WITH RECURSIVE
		analysis (file, by_libc)
		AS (
			SELECT trim(trailing '/' from file), by_libc
			FROM package_fileaccess
			WHERE pkg_id = p
			UNION
			SELECT regexp_replace(file, '/[^/]+$', ''), by_libc
			FROM analysis
			WHERE file != ''
		)
		INSERT INTO pkg_fileaccess_tmp
			SELECT * FROM analysis WHERE file != '';

		x := (SELECT inst FROM package_inst WHERE pkg_id = p);
		y := (SELECT vote FROM package_vote WHERE pkg_id = p);

		for f, is_libc IN (SELECT * FROM pkg_fileaccess_tmp) LOOP
			IF is_libc THEN
				x2 := 0.0;
				y2 := 0.0;
			ELSE
				x2 := x;
				y2 := y;
			END IF;

			IF EXISTS(
				SELECT * FROM fileaccess_tmp WHERE file = f
			) THEN
				UPDATE fileaccess_tmp
				SET popularity = popularity + x2,
				popularity_with_libc = popularity_with_libc + x,
				popularity_by_vote = popularity_by_vote + y2,
				popularity_with_libc_by_vote = popularity_with_libc_by_vote + y
				WHERE file = f;
			ELSE
				INSERT INTO fileaccess_tmp VALUES (f, x2, x, y2, y);
			END IF;
		END LOOP;

		TRUNCATE pkg_fileaccess_tmp;
	END LOOP;

	TRUNCATE TABLE fileaccess_popularity;
	INSERT INTO fileaccess_popularity
		SELECT file,
		popularity,
		popularity_with_libc
		FROM fileaccess_tmp
		ORDER BY popularity_with_libc DESC, file;

	TRUNCATE TABLE fileaccess_popularity_by_vote;
	INSERT INTO fileaccess_popularity_by_vote
		SELECT file,
		popularity_by_vote,
		popularity_with_libc_by_vote
		FROM fileaccess_tmp
		ORDER BY popularity_with_libc_by_vote DESC, file;

	TRUNCATE TABLE fileaccess_tmp;
END
$$ LANGUAGE plpgsql;
