DO $$
BEGIN
IF NOT table_exists('executable_call') THEN
	CREATE TABLE executable_call (
		pkg_id INT NOT NULL, bin_id INT NOT NULL,
		dep_bin_id INT NOT NULL,
		call INT NOT NULL,
		PRIMARY KEY(pkg_id, bin_id, dep_bin_id, call)
	);
	CREATE INDEX executable_call_pkg_id_bin_id_idx
		ON executable_call (pkg_id, bin_id);
	CREATE INDEX executable_call_dep_bin_id_call_idx
		ON executable_call (dep_bin_id, call);
END IF;

IF NOT table_exists('executable_syscall') THEN
	CREATE TABLE executable_syscall (
		pkg_id INT NOT NULL, bin_id INT NOT NULL,
		syscall SMALLINT NOT NULL,
		by_libc BOOLEAN,
		PRIMARY KEY (pkg_id, bin_id, syscall, by_libc)
	);
	CREATE INDEX executable_syscall_pkg_id_bin_id_idx
		ON executable_syscall (pkg_id, bin_id);
END IF;

IF NOT table_exists('executable_vecsyscall') THEN
	CREATE TABLE executable_vecsyscall (
		pkg_id INT NOT NULL, bin_id INT NOT NULL,
		syscall SMALLINT NOT NULL,
		request BIGINT NOT NULL,
		by_libc BOOLEAN,
		PRIMARY KEY (pkg_id, bin_id, syscall, request, by_libc)
	);
	CREATE INDEX executable_vecsyscall_pkg_id_bin_id_idx
		ON executable_vecsyscall (pkg_id, bin_id);
END IF;

IF NOT table_exists('executable_fileaccess') THEN
	CREATE TABLE executable_fileaccess (
		pkg_id INT NOT NULL, bin_id INT NOT NULL,
		file VARCHAR NOT NULL,
		by_libc BOOLEAN,
		PRIMARY KEY (pkg_id, bin_id, file, by_libc)
	);
	CREATE INDEX executable_fileaccess_pkg_id_bin_id_idx
		ON executable_fileaccess (pkg_id, bin_id);
END IF;
END $$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION analysis_executable(p INT, b INT)
RETURNS void AS $$

DECLARE
	libc INT := id FROM package_id WHERE package_name = 'libc6';
	q INT;
	d INT;
	entry		INT := hashtext('.entry');
	init		INT := hashtext('.init');
	init_array	INT := hashtext('.init_array');
	fini		INT := hashtext('.fini');
	fini_array	INT := hashtext('.fini_array');
	time1 TIMESTAMP;
	time2 TIMESTAMP;

BEGIN
	IF NOT EXISTS (
		SELECT * FROM binary_list WHERE pkg_id = p AND bin_id = b
		AND type = 'exe'
	) THEN
		RAISE EXCEPTION 'binary % in package %: not a executable', b, p;
	END IF;

	RAISE NOTICE 'analyze binary: % in package %', b, p;

	time1 := clock_timestamp();

	CREATE TEMP TABLE IF NOT EXISTS dep_lib (
		pkg_id INT NOT NULL,
		bin_id INT NOT NULL,
		PRIMARY KEY(pkg_id, bin_id));
	INSERT INTO dep_lib
		SELECT DISTINCT dep_pkg_id, dep_bin_id
		FROM get_dependency(p, b)
		UNION
		SELECT DISTINCT dep_pkg_id, dep_bin_id
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

	IF NOT temp_table_exists('dep_sym') THEN
		CREATE TEMP TABLE dep_sym (
			pkg_id INT NOT NULL, bin_id INT NOT NULL,
			func_addr INT NOT NULL,
			symbol INT);
		CREATE INDEX dep_sym_pkg_id_bin_id_func_addr_idx
			ON dep_sym(pkg_id, bin_id, symbol);
		CREATE INDEX dep_sym_symbol_idx ON dep_sym(symbol);
	END IF;

	FOR q, d IN (SELECT * FROM dep_lib) LOOP
		INSERT INTO dep_sym
			SELECT q, d, func_addr, symbol FROM
			binary_symbol_hash
			WHERE pkg_id = q AND bin_id = d AND func_addr != 0;
	END LOOP;

	time2 := clock_timestamp();
	RAISE NOTICE 'dep_sym: %', time2 - time1;
	time1 := time2;

	IF NOT temp_table_exists('lib_call') THEN
		CREATE TEMP TABLE lib_call (
			pkg_id INT NOT NULL, bin_id INT NOT NULL,
			func_addr INT NOT NULL,
			call INT NOT NULL,
			PRIMARY KEY(pkg_id, bin_id, func_addr, call));
		CREATE INDEX lib_call_pkg_id_bin_id_func_addr_idx
			ON lib_call(pkg_id, bin_id, func_addr);
		CREATE INDEX lib_call_call_idx ON lib_call(call);
	END IF;

	FOR q, d IN (SELECT * FROM dep_lib) LOOP
		INSERT INTO lib_call
			SELECT q, d, func_addr, call FROM
			library_call_hash
			WHERE pkg_id = q AND bin_id = d;
	END LOOP;

	time2 := clock_timestamp();
	RAISE NOTICE 'lib_call: %', time2 - time1;
	time1 := time2;

	IF NOT temp_table_exists('init_call') THEN
		CREATE TEMP TABLE init_call (
			pkg_id INT NOT NULL, bin_id INT NOT NULL,
			func_addr INT NOT NULL,
			PRIMARY KEY (pkg_id, bin_id, func_addr));
		CREATE INDEX init_call_pkg_id_bin_id_idx
			ON init_call(pkg_id, bin_id);
	END IF;

	INSERT INTO init_call
		SELECT DISTINCT t1.pkg_id, t1.bin_id, t2.func_addr FROM
		get_interp(p, b) AS t1
		INNER JOIN
		dep_sym AS t2
		ON t1.pkg_id = t2.pkg_id AND t1.bin_id = t2.bin_id
		WHERE t2.symbol = entry
		UNION
		SELECT DISTINCT pkg_id, bin_id, func_addr FROM
		dep_sym
		WHERE symbol = init
		OR    symbol = init_array
		OR    symbol = fini
		OR    symbol = fini_array;

	time2 := clock_timestamp();
	RAISE NOTICE 'init_call: %', time2 - time1;
	time1 := time2;

	IF NOT temp_table_exists('bin_call') THEN
		CREATE TEMP TABLE IF NOT EXISTS bin_call (
			pkg_id INT NOT NULL, bin_id INT NOT NULL,
			func_addr INT NOT NULL,
			by_libc BOOLEAN,
			PRIMARY KEY(pkg_id, bin_id, func_addr, by_libc));
		CREATE INDEX bin_call_pkg_id_bin_id_func_addr_idx
			ON bin_call(pkg_id, bin_id, func_addr);
	END IF;

	WITH RECURSIVE
	analysis(pkg_id, bin_id, func_addr, by_libc) AS (
		SELECT t2.pkg_id, t2.bin_id, t2.func_addr, False
		FROM binary_symbol_hash AS t1 INNER JOIN dep_sym AS t2
		ON t1.symbol = t2.symbol
		WHERE t1.pkg_id = p AND t1.bin_id = b AND t1.func_addr = 0
		UNION
		SELECT *, pkg_id = libc FROM init_call
		UNION
		SELECT DISTINCT
		t3.pkg_id, t3.bin_id, t3.func_addr,
		t1.by_libc AND t3.pkg_id = libc
		FROM analysis AS t1
		INNER JOIN
		lib_call AS t2
		ON  t1.pkg_id = t2.pkg_id
		AND t1.bin_id = t2.bin_id
		AND t1.func_addr = t2.func_addr
		INNER JOIN
		dep_sym AS t3
		ON  t2.call = t3.symbol
	)
	INSERT INTO bin_call
		SELECT pkg_id, bin_id, func_addr, by_libc
		from analysis;

	time2 := clock_timestamp();
	RAISE NOTICE 'bin_call: %', time2 - time1;
	time1 := time2;

	DELETE FROM executable_call WHERE pkg_id = p AND bin_id = b;
	INSERT INTO executable_call
		SELECT DISTINCT
		p, b, bin_id, func_addr
		FROM bin_call
		WHERE pkg_id = libc AND by_libc = False;

	time2 := clock_timestamp();
	RAISE NOTICE '%', time2 - time1;
	time1 := time2;

	DELETE FROM executable_syscall WHERE pkg_id = p AND bin_id = b;
	INSERT INTO executable_syscall
		SELECT DISTINCT p, b, syscall, False
		FROM binary_syscall
		WHERE pkg_id = p AND bin_id = b
		UNION
		SELECT DISTINCT p, b, syscall, False
		FROM binary_unknown_syscall
		WHERE pkg_id = p AND bin_id = b
		AND known = True
		UNION
		SELECT DISTINCT p, b, t2.syscall, by_libc
		FROM
		bin_call AS t1 INNER JOIN library_syscall AS t2
		ON  t1.pkg_id = t2.pkg_id AND t1.bin_id = t2.bin_id
		AND t1.func_addr = t2.func_addr;

	time2 := clock_timestamp();
	RAISE NOTICE '%', time2 - time1;
	time1 := time2;

	DELETE FROM executable_vecsyscall WHERE pkg_id = p AND bin_id = b;
	INSERT INTO executable_vecsyscall
		SELECT DISTINCT p, b, syscall, request, False
		FROM binary_vecsyscall
		WHERE pkg_id = p AND bin_id = b
		UNION
		SELECT DISTINCT p, b, syscall, request, False
		FROM binary_unknown_vecsyscall
		WHERE pkg_id = p AND bin_id = b
		AND known = True
		UNION
		SELECT DISTINCT p, b, t2.syscall, t2.request, by_libc
		FROM
		bin_call AS t1 INNER JOIN library_vecsyscall AS t2
		ON  t1.pkg_id = t2.pkg_id AND t1.bin_id = t2.bin_id
		AND t1.func_addr = t2.func_addr;

	time2 := clock_timestamp();
	RAISE NOTICE '%', time2 - time1;
	time1 := time2;

	DELETE FROM executable_fileaccess WHERE pkg_id = p AND bin_id = b;
	INSERT INTO executable_fileaccess
		SELECT DISTINCT p, b, file, False
		FROM binary_fileaccess
		WHERE pkg_id = p AND bin_id = b
		UNION
		SELECT DISTINCT p, b, t2.file, by_libc
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
	TRUNCATE TABLE dep_sym;
	TRUNCATE TABLE lib_call;
	TRUNCATE TABLE init_call;
	TRUNCATE TABLE bin_call;

	RAISE NOTICE 'binary % of package %: callgraph generated', b, p;
END
$$ LANGUAGE plpgsql;
