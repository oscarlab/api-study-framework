DO $$
BEGIN
IF NOT table_exists('call_popularity') THEN
	CREATE TABLE call_popularity (
		pkg_id INT NOT NULL, bin_id INT NOT NULL,
		func_addr INT NOT NULL,
		popularity FLOAT,
		PRIMARY KEY(pkg_id, bin_id, func_addr)
	);
END IF;

IF NOT table_exists('syscall_popularity') THEN
	CREATE TABLE syscall_popularity (
		syscall SMALLINT NOT NULL,
		popularity FLOAT,
		PRIMARY KEY (syscall)
	);
END IF;

IF NOT table_exists('vecsyscall_popularity') THEN
	CREATE TABLE vecsyscall_popularity (
		syscall SMALLINT NOT NULL,
		request BIGINT NOT NULL,
		popularity FLOAT,
		PRIMARY KEY (syscall, request)
	);
END IF;

IF NOT table_exists('fileaccess_popularity') THEN
	CREATE TABLE fileaccess_popularity (
		file VARCHAR NOT NULL,
		popularity FLOAT,
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

CREATE OR REPLACE FUNCTION analysis_call_popularity(p INT, b INT)
RETURNS void AS $$

DECLARE
	total INT := inst FROM package_popularity WHERE package_name = 'Total';
	c INT;
	inst INT;

BEGIN
	CREATE TEMP TABLE IF NOT EXISTS call_tmp (
		func_addr INT NOT NULL PRIMARY KEY,
		popularity FLOAT);
	INSERT INTO call_tmp
		SELECT DISTINCT call, 0.0 FROM package_call
		WHERE dep_pkg_id = p AND dep_bin_id = b;

	FOR c, inst IN (
		SELECT t1.call, t3.inst FROM
		package_call AS t1 INNER JOIN package_id AS t2
		ON  t1.dep_pkg_id = p AND t1.dep_bin_id = b
		AND t1.pkg_id = t2.id
		INNER JOIN package_popularity AS t3
		ON  t2.package_name = t3.package_name
		AND t3.inst != 0
	) LOOP
		UPDATE call_tmp
		SET popularity = add_pop(popularity, inst, total)
		WHERE func_addr = c;
	END LOOP;

	DELETE FROM call_popularity WHERE pkg_id = p AND bin_id = b;
	INSERT INTO call_popularity
		SELECT p, b, func_addr, popularity
		FROM call_tmp
		ORDER BY popularity DESC, func_addr;

	TRUNCATE TABLE call_tmp;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analysis_syscall_popularity()
RETURNS void AS $$

DECLARE
	total INT := inst FROM package_popularity WHERE package_name = 'Total';
	s SMALLINT;
	inst INT;

BEGIN
	CREATE TEMP TABLE IF NOT EXISTS syscall_tmp (
		syscall SMALLINT NOT NULL PRIMARY KEY,
		popularity FLOAT);
	INSERT INTO syscall_tmp
		SELECT DISTINCT syscall, 0.0 FROM package_syscall;

	FOR s, inst IN (
		SELECT t1.syscall, t3.inst FROM
		package_syscall AS t1 INNER JOIN package_id AS t2
		ON  t1.pkg_id = t2.id
		INNER JOIN package_popularity AS t3
		ON  t2.package_name = t3.package_name
		AND t3.inst != 0
	) LOOP
		UPDATE syscall_tmp
		SET popularity = add_pop(popularity, inst, total)
		WHERE syscall = s;
	END LOOP;

	TRUNCATE TABLE syscall_popularity;
	INSERT INTO syscall_popularity
		SELECT syscall, popularity
		FROM syscall_tmp
		ORDER BY popularity DESC, syscall;

	TRUNCATE TABLE syscall_tmp;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analysis_vecsyscall_popularity()
RETURNS void AS $$

DECLARE
	total INT := inst FROM package_popularity WHERE package_name = 'Total';
	s SMALLINT;
	r BIGINT;
	inst INT;

BEGIN
	CREATE TEMP TABLE IF NOT EXISTS vecsyscall_tmp (
		syscall SMALLINT NOT NULL,
		request BIGINT NOT NULL,
		popularity FLOAT,
		PRIMARY KEY (syscall, request));
	INSERT INTO vecsyscall_tmp
		SELECT DISTINCT syscall, request, 0.0 FROM package_vecsyscall;

	FOR s, r, inst IN (
		SELECT t1.syscall, t1.request, t3.inst FROM
		package_vecsyscall AS t1 INNER JOIN package_id AS t2
		ON  t1.pkg_id = t2.id
		INNER JOIN package_popularity AS t3
		ON  t2.package_name = t3.package_name
		AND t3.inst != 0
	) LOOP
		UPDATE vecsyscall_tmp
		SET popularity = add_pop(popularity, inst, total)
		WHERE syscall = s AND request = r;
	END LOOP;

	TRUNCATE TABLE vecsyscall_popularity;
	INSERT INTO vecsyscall_popularity
		SELECT syscall, request, popularity
		FROM vecsyscall_tmp
		ORDER BY syscall, popularity DESC, request;

	TRUNCATE TABLE vecsyscall_tmp;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analysis_fileaccess_popularity()
RETURNS void AS $$

DECLARE
	total INT := inst FROM package_popularity WHERE package_name = 'Total';
	f VARCHAR;
	inst INT;

BEGIN
	CREATE TEMP TABLE IF NOT EXISTS fileaccess_tmp (
		file VARCHAR NOT NULL PRIMARY KEY,
		popularity FLOAT);
	INSERT INTO fileaccess_tmp
		SELECT DISTINCT file, 0.0 FROM package_fileaccess;

	FOR f, inst IN (
		SELECT t1.file, t3.inst FROM
		package_fileaccess AS t1 INNER JOIN package_id AS t2
		ON  t1.pkg_id = t2.id
		INNER JOIN package_popularity AS t3
		ON  t2.package_name = t3.package_name
		AND t3.inst != 0
	) LOOP
		UPDATE fileaccess_tmp
		SET popularity = add_pop(popularity, inst, total)
		WHERE file = f;
	END LOOP;

	TRUNCATE TABLE fileaccess_popularity;
	INSERT INTO fileaccess_popularity
		SELECT file, popularity
		FROM fileaccess_tmp
		ORDER BY popularity DESC, file;

	TRUNCATE TABLE fileaccess_tmp;
END
$$ LANGUAGE plpgsql;


