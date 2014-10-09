DO $$
BEGIN
IF NOT table_exists('executable_call') THEN
	CREATE TABLE executable_call (
		pkg_id INT NOT NULL, bin_id INT NOT NULL,
		dep_pkg_id INT NOT NULL,
		dep_bin_id INT NOT NULL,
		call INT NOT NULL,
		by_pkg_id INT NOT NULL,
		by_bin_id INT NOT NULL,
		PRIMARY KEY(pkg_id, bin_id, dep_pkg_id, dep_bin_id, call, by_pkg_id, by_bin_id)
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
		by_pkg_id INT NOT NULL,
		by_bin_id INT NOT NULL,
		PRIMARY KEY (pkg_id, bin_id, syscall, by_pkg_id, by_bin_id)
	);
	CREATE INDEX executable_syscall_pkg_id_bin_id_idx
		ON executable_syscall (pkg_id, bin_id);
END IF;

IF NOT table_exists('executable_vecsyscall') THEN
	CREATE TABLE executable_vecsyscall (
		pkg_id INT NOT NULL, bin_id INT NOT NULL,
		syscall SMALLINT NOT NULL,
		request BIGINT NOT NULL,
		by_pkg_id INT NOT NULL,
		by_bin_id INT NOT NULL,
		PRIMARY KEY (pkg_id, bin_id, syscall, request, by_pkg_id, by_bin_id)
	);
	CREATE INDEX executable_vecsyscall_pkg_id_bin_id_idx
		ON executable_vecsyscall (pkg_id, bin_id);
END IF;

IF NOT table_exists('executable_fileaccess') THEN
	CREATE TABLE executable_fileaccess (
		pkg_id INT NOT NULL, bin_id INT NOT NULL,
		file VARCHAR NOT NULL,
		by_pkg_id INT NOT NULL,
		by_bin_id INT NOT NULL,
		PRIMARY KEY (pkg_id, bin_id, file, by_pkg_id, by_bin_id)
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
	time1 TIMESTAMP;
	time2 TIMESTAMP;

BEGIN
	IF NOT EXISTS (
		SELECT * FROM binary_list WHERE pkg_id = p AND bin_id = b
		AND type = 'exe'
	) THEN
		RAISE EXCEPTION 'binary %d in package %d: not a executable', b, p;
	END IF;

	RAISE NOTICE 'analyze binary: % in package %', b, p;

	time1 := clock_timestamp();

	CREATE TEMP TABLE IF NOT EXISTS dep_lib (
		pkg_id INT NOT NULL,
		bin_id INT NOT NULL,
		PRIMARY KEY(pkg_id, bin_id));
	INSERT INTO dep_lib
		SELECT dep_pkg_id, dep_bin_id
		FROM get_dependency(p, b)
		UNION
		SELECT dep_pkg_id, dep_bin_id
		FROM get_interp(p, b);

	FOR q, d IN (SELECT * FROM dep_lib) LOOP
		IF NOT EXISTS (
			SELECT * FROM binary_list
			WHERE pkg_id = q AND bin_id = d
			AND callgraph = True
		) THEN
			RAISE EXCEPTION 'binary % in package % dependency not analyzed: % in package %', b, p, d, q;
		END IF;
	END LOOP;

	time2 := clock_timestamp();
	RAISE NOTICE 'dep_lib: %', time2 - time1;
	time1 := time2;

	IF NOT temp_table_exists('interp_call') THEN
		CREATE TEMP TABLE interp_call (
			pkg_id INT NOT NULL, bin_id INT NOT NULL,
			func_addr INT NOT NULL,
			call_name VARCHAR NOT NULL);
		CREATE INDEX interp_call_pkg_id_bin_id_idx ON interp_call(pkg_id, bin_id);
		CREATE INDEX interp_call_call_name_idx ON interp_call(call_name);
	END IF;

	INSERT INTO interp_call
		SELECT t1.pkg_id, t1.bin_id, t2.func_addr, t3.call_name FROM
		get_interp(p, b) AS t1
		INNER JOIN
		binary_symbol AS t2
		ON  t1.pkg_id = t2.pkg_id AND t1.bin_id = t2.bin_id
		AND t2.symbol_name = '.entry'
		INNER JOIN
		library_call AS t3
		ON  t1.pkg_id = t3.pkg_id AND t1.bin_id = t3.bin_id
		AND t2.func_addr = t3.func_addr;

	time2 := clock_timestamp();
	RAISE NOTICE 'interp_call: %', time2 - time1;
	time1 := time2;

	IF NOT temp_table_exists('dep_call') THEN
		CREATE TEMP TABLE dep_call (
			pkg_id INT NOT NULL, bin_id INT NOT NULL,
			func_addr INT NOT NULL,
			symbol_name VARCHAR, call_name VARCHAR);
		CREATE INDEX dep_call_pkg_id_bin_id_idx ON dep_call(pkg_id, bin_id);
		CREATE INDEX dep_call_call_name_idx ON dep_call(call_name);
	END IF;

	FOR q, d IN (SELECT * FROM dep_lib) LOOP
		RAISE NOTICE '% in %', d, q;

		INSERT INTO dep_call
			SELECT q, d, t1.func_addr, symbol_name, call_name FROM
			binary_symbol AS t1
			RIGHT JOIN
			library_call AS t2
			ON t1.func_addr = t2.func_addr
			WHERE t1.pkg_id = q AND t1.bin_id = d
			AND   t2.pkg_id = q AND t2.bin_id = d
			AND   t1.defined = True;

	END LOOP;

	time2 := clock_timestamp();
	RAISE NOTICE 'dep_call: %', time2 - time1;
	time1 := time2;

	IF NOT temp_table_exists('bin_call') THEN
		CREATE TEMP TABLE IF NOT EXISTS bin_call (
			pkg_id INT NOT NULL, bin_id INT NOT NULL,
			func_addr INT NOT NULL,
			by_pkg_id INT NOT NULL,
			by_bin_id INT NOT NULL);
		CREATE INDEX bin_call_pkg_id_bin_id_func_addr_idx ON bin_call(pkg_id, bin_id, func_addr);
	END IF;

	WITH RECURSIVE
	analysis(pkg_id, bin_id, func_addr, call_name, by_pkg_id, by_bin_id) AS (
		SELECT 0, 0, 0, symbol_name, p, b
		FROM binary_symbol
		WHERE pkg_id = p AND bin_id = b AND defined = False
		UNION
		SELECT *, pkg_id, bin_id FROM interp_call
		UNION
		SELECT pkg_id, bin_id, func_addr, call_name, pkg_id, bin_id FROM dep_call
		WHERE symbol_name = '.init'
		OR    symbol_name = '.fini'
		OR    symbol_name = '.init_array'
		OR    symbol_name = '.fini_array'
		UNION
		SELECT
		t2.pkg_id, t2.bin_id, t2.func_addr, t2.call_name,
		t1.by_pkg_id, t1.by_bin_id
		FROM analysis AS t1
		INNER JOIN
		dep_call AS t2
		ON t1.call_name = t2.symbol_name
	)
	INSERT INTO bin_call
		SELECT pkg_id, bin_id, func_addr, by_pkg_id, by_bin_id
		from analysis
		WHERE pkg_id != 0 AND bin_id != 0 AND func_addr != 0;

	time2 := clock_timestamp();
	RAISE NOTICE 'bin_call: %', time2 - time1;
	time1 := time2;

	DELETE FROM executable_call WHERE pkg_id = p AND bin_id = b;
	INSERT INTO executable_call
		SELECT DISTINCT
		p, b, pkg_id, bin_id, func_addr, by_pkg_id, by_bin_id
		FROM bin_call;

	time2 := clock_timestamp();
	RAISE NOTICE '%', time2 - time1;
	time1 := time2;

	DELETE FROM executable_syscall WHERE pkg_id = p AND bin_id = b;
	INSERT INTO executable_syscall
		SELECT DISTINCT p, b, syscall, p, b FROM binary_syscall
		WHERE pkg_id = p AND bin_id = b
		UNION
		SELECT DISTINCT p, b, syscall, p, b FROM binary_unknown_syscall
		WHERE pkg_id = p AND bin_id = b
		AND known = True
		UNION
		SELECT DISTINCT p, b, t2.syscall,
		t1.by_pkg_id, t1.by_bin_id
		FROM
		bin_call AS t1 INNER JOIN library_syscall AS t2
		ON  t1.pkg_id = t2.pkg_id AND t1.bin_id = t2.bin_id
		AND t1.func_addr = t2.func_addr;

	time2 := clock_timestamp();
	RAISE NOTICE '%', time2 - time1;
	time1 := time2;

	DELETE FROM executable_vecsyscall WHERE pkg_id = p AND bin_id = b;
	INSERT INTO executable_vecsyscall
		SELECT DISTINCT p, b, syscall, request, p, b FROM binary_vecsyscall
		WHERE pkg_id = p AND bin_id = b
		UNION
		SELECT DISTINCT p, b, syscall, request, p, b FROM binary_unknown_vecsyscall
		WHERE pkg_id = p AND bin_id = b
		AND known = True
		UNION
		SELECT DISTINCT p, b, t2.syscall, t2.request,
		t1.by_pkg_id, t1.by_bin_id
		FROM
		bin_call AS t1 INNER JOIN library_vecsyscall AS t2
		ON  t1.pkg_id = t2.pkg_id AND t1.bin_id = t2.bin_id
		AND t1.func_addr = t2.func_addr;

	time2 := clock_timestamp();
	RAISE NOTICE '%', time2 - time1;
	time1 := time2;

	DELETE FROM executable_fileaccess WHERE pkg_id = p AND bin_id = b;
	INSERT INTO executable_fileaccess
		SELECT DISTINCT p, b, file, p, b FROM binary_fileaccess
		WHERE pkg_id = p AND bin_id = b
		UNION
		SELECT DISTINCT p, b, t2.file,
		t1.by_pkg_id, t1.by_bin_id
		FROM
		bin_call AS t1 INNER JOIN library_fileaccess AS t2
		ON  t1.pkg_id = t2.pkg_id AND t1.bin_id = t2.bin_id
		AND t1.func_addr = t2.func_addr;

	time2 := clock_timestamp();
	RAISE NOTICE '%', time2 - time1;
	time1 := time2;

	UPDATE binary_list SET callgraph = True WHERE pkg_id = p AND bin_id = b;
	UPDATE package_id SET footprint = False WHERE id = p;

	TRUNCATE TABLE dep_lib;
	TRUNCATE TABLE interp_call;
	TRUNCATE TABLE dep_call;
	TRUNCATE TABLE bin_call;

	RAISE NOTICE 'binary % of package %: callgraph generated', b, p;
END
$$ LANGUAGE plpgsql;
