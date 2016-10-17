DO $$
BEGIN
IF NOT table_exists('executable_call') THEN
	CREATE TABLE executable_call (
		pkg_id INT NOT NULL, bin_id INT NOT NULL,
		dep_bin_id INT NOT NULL,
		call_addr INT NOT NULL,
		PRIMARY KEY(pkg_id, bin_id, dep_bin_id, call_addr)
	);
	CREATE INDEX executable_call_pkg_id_bin_id_idx
		ON executable_call (pkg_id, bin_id);
	CREATE INDEX executable_call_dep_bin_id_call_addr_idx
		ON executable_call (dep_bin_id, call_addr);
END IF;

IF NOT table_exists('executable_api_usage') THEN
	CREATE TABLE executable_api_usage (
		pkg_id INT NOT NULL, bin_id INT NOT NULL,
		api_type SMALLINT NOT NULL,
		api_id BIGINT NOT NULL,
		PRIMARY KEY (pkg_id, bin_id, api_type, api_id)
	);
	CREATE INDEX executable_api_usage_pkg_id_bin_id_idx
		ON executable_api_usage (pkg_id, bin_id);
	CREATE INDEX executable_api_usage_api_type_idx
		ON executable_api_usage (api_type);
	CREATE INDEX executable_api_usage_api_id_idx
		ON executable_api_usage (api_id);
END IF;

IF NOT table_exists('executable_opcode_usage') THEN
	CREATE TABLE executable_opcode_usage (
		pkg_id INT NOT NULL,
		bin_id INT NOT NULL,
		prefix BIGINT NULL,
		opcode BIGINT NOT NULL,
		size INT NOT NULL,
		mnem VARCHAR NOT NULL,
		count INT NOT NULL,
		PRIMARY KEY (pkg_id, bin_id, prefix, opcode, size, mnem)
	);
	CREATE INDEX executable_opcode_usage_pkg_id_bin_id_idx
		ON executable_opcode_usage (pkg_id, bin_id);
	CREATE INDEX executable_opcode_usage_prefix_opcode_size_idx
		ON executable_opcode_usage (prefix, opcode, size);
END IF;

END $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analyze_executable(p INT, b INT)
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
			symbol_hash INT);
		CREATE INDEX dep_sym_pkg_id_bin_id_func_addr_idx
			ON dep_sym(pkg_id, bin_id, func_addr);
		CREATE INDEX dep_sym_symbol_hash_idx ON dep_sym(symbol_hash);
	END IF;

	FOR q, d IN (SELECT * FROM dep_lib) LOOP
		INSERT INTO dep_sym
			SELECT q, d, func_addr, hashtext(symbol_name)
			FROM binary_symbol
			WHERE pkg_id = q AND bin_id = d AND func_addr != 0;
	END LOOP;

	time2 := clock_timestamp();
	RAISE NOTICE 'dep_sym: %', time2 - time1;
	time1 := time2;

	IF NOT temp_table_exists('dep_lib_call') THEN
		CREATE TEMP TABLE dep_lib_call (
			pkg_id INT NOT NULL, bin_id INT NOT NULL,
			func_addr INT NOT NULL,
			call_hash INT NOT NULL,
			PRIMARY KEY(pkg_id, bin_id, func_addr, call_hash));
		CREATE INDEX dep_lib_call_pkg_id_bin_id_func_addr_idx
			ON dep_lib_call(pkg_id, bin_id, func_addr);
		CREATE INDEX dep_lib_call_call_idx ON dep_lib_call(call_hash);
	END IF;

	FOR q, d IN (SELECT * FROM dep_lib) LOOP
		INSERT INTO dep_lib_call
			SELECT q, d, func_addr, call_hash FROM
			library_call
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
		SELECT DISTINCT t1.pkg_id, t1.bin_id, t2.func_addr
		FROM get_interp(p, b) AS t1
		INNER JOIN
		dep_sym AS t2
		ON t1.pkg_id = t2.pkg_id AND t1.bin_id = t2.bin_id
		WHERE t2.symbol_hash = entry
		UNION
		SELECT DISTINCT pkg_id, bin_id, func_addr
		FROM dep_sym
		WHERE symbol_hash = init
		OR    symbol_hash = init_array
		OR    symbol_hash = fini
		OR    symbol_hash = fini_array;

	time2 := clock_timestamp();
	RAISE NOTICE 'init_call: %', time2 - time1;
	time1 := time2;

	IF NOT temp_table_exists('bin_call') THEN
		CREATE TEMP TABLE IF NOT EXISTS bin_call (
			pkg_id INT NOT NULL, bin_id INT NOT NULL,
			func_addr INT NOT NULL,
			PRIMARY KEY(pkg_id, bin_id, func_addr));
		CREATE INDEX bin_call_pkg_id_bin_id_func_addr_idx
			ON bin_call(pkg_id, bin_id, func_addr);
	END IF;

	WITH RECURSIVE
	analysis(pkg_id, bin_id, func_addr) AS (
		SELECT t2.pkg_id, t2.bin_id, t2.func_addr
		FROM binary_symbol AS t1 INNER JOIN dep_sym AS t2
		ON hashtext(t1.symbol_name) = t2.symbol_hash
		WHERE t1.pkg_id = p AND t1.bin_id = b AND t1.func_addr = 0
		UNION
		SELECT DISTINCT
		t3.pkg_id, t3.bin_id, t3.func_addr
		FROM analysis AS t1
		JOIN
		dep_lib_call AS t2
		ON  t1.pkg_id = t2.pkg_id
		AND t1.bin_id = t2.bin_id
		AND t1.func_addr = t2.func_addr
		JOIN
		dep_sym AS t3
		ON  t2.call_hash = t3.symbol_hash
	)
	INSERT INTO bin_call
		SELECT pkg_id, bin_id, func_addr
		FROM analysis;

	time2 := clock_timestamp();
	RAISE NOTICE 'bin_call: %', time2 - time1;
	time1 := time2;

	DELETE FROM executable_call WHERE pkg_id = p AND bin_id = b;
	INSERT INTO executable_call
		SELECT DISTINCT
		p, b, bin_id, func_addr
		FROM bin_call
		WHERE pkg_id = libc;

	time2 := clock_timestamp();
	RAISE NOTICE '%', time2 - time1;
	time1 := time2;

	DELETE FROM executable_api_usage WHERE pkg_id = p AND bin_id = b;
	INSERT INTO executable_api_usage
		SELECT DISTINCT p, b, api_type, api_id
		FROM binary_api_usage
		WHERE pkg_id = p AND bin_id = b
		UNION
		SELECT DISTINCT p, b, t2.api_type, t2.api_id
		FROM bin_call AS t1
		INNER JOIN
		library_api_usage AS t2
		ON  t1.pkg_id = t2.pkg_id
		AND t1.bin_id = t2.bin_id
		AND t1.func_addr = t2.func_addr;

	DELETE FROM executable_opcode_usage WHERE pkg_id = p AND bin_id = b;
	INSERT INTO executable_opcode_usage
	SELECT t3.pkg_id, t3.bin_id, t3.prefix, t3.opcode, t3.size, t3.mnem, SUM(t3.count)
	FROM(
		SELECT pkg_id, bin_id, prefix, opcode, size, mnem, count
		FROM binary_opcode_usage
		WHERE pkg_id = p AND bin_id = b
		--GROUP BY pkg_id, bin_id, prefix, opcode, size, mnem
		UNION
		SELECT t2.pkg_id, t2.bin_id, t2.prefix, t2.opcode, t2.size, t2.mnem, t2.count
		FROM bin_call AS t1
		INNER JOIN
		library_opcode_usage AS t2
		ON  t1.pkg_id = t2.pkg_id
		AND t1.bin_id = t2.bin_id
		AND t1.func_addr = t2.func_addr)
		--GROUP BY t2.pkg_id, t2.bin_id, t2.prefix, t2.opcode, t3.size, t2.mnem)
	AS t3
	GROUP BY t3.pkg_id, t3.bin_id, t3.prefix, t3.opcode, t3.size, t3.mnem;

	time2 := clock_timestamp();
	RAISE NOTICE '%', time2 - time1;
	time1 := time2;

	UPDATE binary_list SET callgraph = True WHERE pkg_id = p AND bin_id = b;
	UPDATE package_id SET footprint = False WHERE id = p;

	TRUNCATE TABLE dep_lib;
	TRUNCATE TABLE dep_sym;
	TRUNCATE TABLE dep_lib_call;
	TRUNCATE TABLE init_call;
	TRUNCATE TABLE bin_call;

	RAISE NOTICE 'binary % of package %: callgraph generated', b, p;
END
$$ LANGUAGE plpgsql;
