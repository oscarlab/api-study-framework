DO $$
BEGIN
IF NOT table_exists('executable_call') THEN
	CREATE TABLE executable_call (
		pkg_id INT NOT NULL, bin_id INT NOT NULL,
		dep_pkg_id INT NOT NULL,
		dep_bin_id INT NOT NULL,
		call INT NOT NULL,
		PRIMARY KEY(pkg_id, bin_id, dep_pkg_id, dep_bin_id, call)
	);
	CREATE INDEX executable_call_pkg_id_bin_id_idx
		ON executable_call (pkg_id, bin_id);
	CREATE INDEX executable_call_dep_pkg_id_dep_bin_id_idx
		ON executable_call (dep_pkg_id, dep_bin_id);
	CREATE INDEX executable_call_call_idx
		ON executable_call (call);
END IF;

IF NOT table_exists('executable_syscall') THEN
	CREATE TABLE executable_syscall (
		pkg_id INT NOT NULL, bin_id INT NOT NULL,
		syscall SMALLINT NOT NULL,
		PRIMARY KEY (pkg_id, bin_id, syscall)
	);
	CREATE INDEX executable_syscall_pkg_id_bin_id_idx
		ON executable_syscall (pkg_id, bin_id);
END IF;

IF NOT table_exists('executable_vecsyscall') THEN
	CREATE TABLE executable_vecsyscall (
		pkg_id INT NOT NULL, bin_id INT NOT NULL,
		syscall SMALLINT NOT NULL,
		request BIGINT NOT NULL,
		PRIMARY KEY (pkg_id, bin_id, syscall, request)
	);
	CREATE INDEX executable_vecsyscall_pkg_id_bin_id_idx
		ON executable_vecsyscall (pkg_id, bin_id);
END IF;

IF NOT table_exists('executable_fileaccess') THEN
	CREATE TABLE executable_fileaccess (
		pkg_id INT NOT NULL, bin_id INT NOT NULL,
		file VARCHAR NOT NULL,
		PRIMARY KEY (pkg_id, bin_id, file)
	);
	CREATE INDEX executable_fileaccess_pkg_id_bin_id_idx
		ON executable_fileaccess (pkg_id, bin_id);
END IF;
END $$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION analysis_executable(p INT, b INT)
RETURNS void AS $$

DECLARE
	q INT;
	d INT;

BEGIN
	IF NOT EXISTS (
		SELECT * FROM binary_list WHERE pkg_id = p AND bin_id = b
		AND type = 'exe'
	) THEN
		RAISE EXCEPTION 'binary %d in package %d: not a executable', b, p;
	END IF;

	RAISE NOTICE 'analyze binary: % in package %', b, p;

	CREATE TEMP TABLE IF NOT EXISTS dep_lib (
		pkg_id INT NOT NULL,
		bin_id INT NOT NULL,
		linking BOOLEAN,
		PRIMARY KEY(pkg_id, bin_id));
	INSERT INTO dep_lib
		SELECT DISTINCT t2.pkg_id, t2.bin_id, t2.linking FROM
		binary_linking AS t1
		INNER JOIN
		binary_list AS t2
		ON t1.pkg_id = p AND t1.bin_id = b AND t1.dep_id = t2.bin_id;
	
	IF EXISTS (
		SELECT * FROM dep_lib WHERE linking = False
	) THEN
		RAISE EXCEPTION 'linking not resolved: % in package %', b, p;
	END IF;

	FOR q, d IN (SELECT pkg_id, bin_id FROM dep_lib) LOOP
		RAISE NOTICE 'dependency: % in package %', d, q;
	END LOOP;

	CREATE TEMP TABLE IF NOT EXISTS dep_sym (
		pkg_id INT NOT NULL, bin_id INT NOT NULL,
		symbol_name VARCHAR NOT NULL,
		func_addr INT NOT NULL);
	FOR q, d IN (SELECT pkg_id, bin_id FROM dep_lib) LOOP
		INSERT INTO dep_sym
			SELECT DISTINCT q, d, symbol_name, func_addr
			FROM binary_symbol
			WHERE pkg_id = q AND bin_id = d AND defined = True;
	END LOOP;

	CREATE TEMP TABLE IF NOT EXISTS interp_call (
		pkg_id INT NOT NULL, bin_id INT NOT NULL,
		func_addr INT NOT NULL,
		call_name VARCHAR NOT NULL);
	FOR q, d IN (
		SELECT t2.pkg_id, t2.bin_id FROM (
			SELECT interp FROM binary_interp WHERE
			pkg_id = p AND bin_id = b
			UNION
			SELECT t2.dep_id AS interp FROM
			binary_interp AS t1 INNER JOIN binary_linking AS t2
			ON  t1.pkg_id = p AND t1.bin_id = b
			AND t1.interp = t2.bin_id AND t2.by_link = True
		) AS t1 INNER JOIN
		dep_lib AS t2
		ON t1.interp = t2.bin_id
	) LOOP
		INSERT INTO interp_call
			SELECT q, d, t1.func_addr, t2.call_name FROM
			binary_symbol AS t1
			INNER JOIN
			library_call AS t2
			ON  t1.pkg_id = q AND t1.bin_id = d
			AND t2.pkg_id = q AND t2.bin_id = d
			AND t1.symbol_name = '.entry'
			AND t1.func_addr = t2.func_addr;
	END LOOP;

	CREATE TEMP TABLE IF NOT EXISTS dep_call (
		pkg_id INT NOT NULL, bin_id INT NOT NULL,
		func_addr INT NOT NULL,
		symbol_name VARCHAR, call_name VARCHAR);
	FOR q, d IN (SELECT * FROM dep_lib) LOOP
		INSERT INTO dep_call
			SELECT q, d, t1.func_addr, symbol_name, call_name FROM
			binary_symbol AS t1
			INNER JOIN
			library_call AS t2
			ON  t1.pkg_id = q AND t1.bin_id = d
			AND t2.pkg_id = 1 AND t2.bin_id = d
			AND t1.func_addr = t2.func_addr
			UNION
			SELECT q, d, func_addr, symbol_name, NULL
			FROM dep_sym
			WHERE pkg_id = q AND bin_id = d;
	END LOOP;

	CREATE TEMP TABLE IF NOT EXISTS bin_call (
		pkg_id INT NOT NULL, bin_id INT NOT NULL,
		func_addr INT NOT NULL,
		PRIMARY KEY (pkg_id, bin_id, func_addr));

	WITH RECURSIVE
	analysis(pkg_id, bin_id, func_addr, call_name) AS (
		SELECT 0, 0, 0, symbol_name FROM binary_symbol
		WHERE pkg_id = p AND bin_id = b AND defined = 'False'
		UNION
		SELECT * FROM interp_call
		UNION
		VALUES	(0, 0, 0, '.init'),
			(0, 0, 0, '.fini'),
			(0, 0, 0, '.init_array'),
			(0, 0, 0, '.fini_array')
		UNION
		SELECT DISTINCT
		t2.pkg_id, t2.bin_id, t2.func_addr, t2.call_name
		FROM analysis AS t1
		INNER JOIN
		dep_call AS t2
		ON t1.call_name = t2.symbol_name
	)
	INSERT INTO bin_call
		SELECT DISTINCT pkg_id, bin_id, func_addr
		from analysis
		WHERE pkg_id != 0 AND bin_id != 0 AND func_addr != 0;

	DELETE FROM executable_call WHERE pkg_id = p AND bin_id = b;
	INSERT INTO executable_call
		SELECT p, b, pkg_id, bin_id, func_addr FROM bin_call;

	DELETE FROM executable_syscall WHERE pkg_id = p AND bin_id = b;
	INSERT INTO executable_syscall
		SELECT DISTINCT p, b, syscall FROM binary_syscall
		WHERE pkg_id = p AND bin_id = b
		UNION
		SELECT DISTINCT p, b, syscall FROM binary_unknown_syscall
		WHERE pkg_id = p AND bin_id = b
		AND known = True
		UNION
		SELECT DISTINCT p, b, t2.syscall FROM
		bin_call AS t1 INNER JOIN library_syscall AS t2
		ON  t1.pkg_id = t2.pkg_id AND t1.bin_id = t2.bin_id
		AND t1.func_addr = t2.func_addr;

	DELETE FROM executable_vecsyscall WHERE pkg_id = p AND bin_id = b;
	INSERT INTO executable_vecsyscall
		SELECT DISTINCT p, b, syscall, request FROM binary_vecsyscall
		WHERE pkg_id = p AND bin_id = b
		UNION
		SELECT DISTINCT p, b, syscall, request FROM binary_unknown_vecsyscall
		WHERE pkg_id = p AND bin_id = b
		AND known = True
		UNION
		SELECT DISTINCT p, b, t2.syscall, t2.request FROM
		bin_call AS t1 INNER JOIN library_vecsyscall AS t2
		ON  t1.pkg_id = t2.pkg_id AND t1.bin_id = t2.bin_id
		AND t1.func_addr = t2.func_addr;

	DELETE FROM executable_fileaccess WHERE pkg_id = p AND bin_id = b;
	INSERT INTO executable_fileaccess
		SELECT DISTINCT p, b, file FROM binary_fileaccess
		WHERE pkg_id = p AND bin_id = b
		UNION
		SELECT DISTINCT p, b, t2.file FROM
		bin_call AS t1 INNER JOIN library_fileaccess AS t2
		ON  t1.pkg_id = t2.pkg_id AND t1.bin_id = t2.bin_id
		AND t1.func_addr = t2.func_addr;

	UPDATE binary_list SET callgraph = True
	WHERE pkg_id = p AND bin_id = b;

	TRUNCATE TABLE dep_lib;
	TRUNCATE TABLE dep_sym;
	TRUNCATE TABLE interp_call;
	TRUNCATE TABLE dep_call;
	TRUNCATE TABLE bin_call;

	RAISE NOTICE 'binary % of package %: callgraph generated', b, p;
END
$$ LANGUAGE plpgsql;
