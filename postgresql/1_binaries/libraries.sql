DO $$
BEGIN
IF NOT table_exists('library_call') THEN
	CREATE TABLE library_call (
		pkg_id INT NOT NULL, bin_id INT NOT NULL,
		func_addr INT NOT NULL,
		call_hash INT NOT NULL,
		PRIMARY KEY (pkg_id, bin_id, func_addr, call_hash)
	);
	CREATE INDEX library_call_pkg_id_bin_id_func_addr_idx
		ON library_call (pkg_id, bin_id, func_addr);
	CREATE INDEX library_call_pkg_id_bin_id_idx
		ON library_call (pkg_id, bin_id);
END IF;

IF NOT table_exists('library_api_usage') THEN
	CREATE TABLE library_api_usage (
		pkg_id INT NOT NULL, bin_id INT NOT NULL,
		func_addr INT NOT NULL,
		api_type SMALLINT NOT NULL,
		api_id BIGINT NOT NULL,
		PRIMARY KEY (pkg_id, bin_id, func_addr, api_type, api_id)
	);
	CREATE INDEX library_api_usage_pkg_id_bin_id_func_addr_idx
		ON library_api_usage (pkg_id, bin_id, func_addr);
	CREATE INDEX library_api_usage_pkg_id_bin_id_idx
		ON library_api_usage (pkg_id, bin_id);
	CREATE INDEX library_api_usage_api_type_api_id_idx
		ON library_api_usage (api_type, api_id);
END IF;

IF NOT table_exists('library_instr_usage') THEN
	CREATE TABLE library_instr_usage (
		pkg_id INT NOT NULL, bin_id INT NOT NULL,
		func_addr INT NOT NULL,
		instr VARCHAR(15) NOT NULL,
		PRIMARY KEY (pkg_id, bin_id, func_addr, instr)
	);
	CREATE INDEX library_instr_usage_pkg_id_bin_id_func_addr_idx
		ON library_instr_usage (pkg_id, bin_id, func_addr);
	CREATE INDEX library_instr_usage_pkg_id_bin_id_idx
		ON library_instr_usage (pkg_id, bin_id);
	CREATE INDEX library_instr_usage_instr_idx
		ON library_instr_usage (instr);
END IF;

END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analyze_library(p INT, b INT)
RETURNS void AS $$

BEGIN
	IF NOT EXISTS (
		SELECT * FROM binary_list WHERE pkg_id = p AND bin_id = b
		AND type = 'lib'
	) THEN
		RAISE EXCEPTION 'binary %d in package %d: not a library', b, p;
	END IF;

	CREATE TEMP TABLE IF NOT EXISTS lib_entry (
		func_addr INT NOT NULL PRIMARY KEY);
	INSERT INTO lib_entry
		SELECT DISTINCT func_addr
		FROM binary_symbol
		WHERE pkg_id = p AND bin_id = b
		AND func_addr != 0;

	CREATE TEMP TABLE IF NOT EXISTS lib_call (
		func_addr INT NOT NULL,
		call_addr INT NOT NULL,
		PRIMARY KEY (func_addr, call_addr));
	INSERT INTO lib_call
		SELECT DISTINCT func_addr, call_addr
		FROM binary_call
		WHERE pkg_id = p AND bin_id = b
		AND call_addr IS NOT NULL;

	CREATE TEMP TABLE IF NOT EXISTS lib_callgraph (
		func_addr INT NOT NULL, call_addr INT NOT NULL);

	WITH RECURSIVE
	analysis (func_addr, call_addr)
	AS (
		SELECT func_addr, func_addr FROM lib_entry
		UNION
		SELECT t1.func_addr, t2.call_addr FROM
		analysis AS t1
		INNER JOIN
		lib_call AS t2
		ON t1.call_addr = t2.func_addr
	)
	INSERT INTO lib_callgraph SELECT DISTINCT * FROM analysis;

	DELETE FROM library_call WHERE pkg_id = p AND bin_id = b;
	INSERT INTO library_call
	SELECT DISTINCT p, b, t1.func_addr, hashtext(t2.call_name) FROM
	lib_callgraph AS t1
	INNER JOIN (
		SELECT DISTINCT func_addr, call_name
		FROM binary_call
		WHERE pkg_id = p AND bin_id = b
		AND call_addr IS NULL
	) AS t2
	ON t1.call_addr = t2.func_addr;

	DELETE FROM library_api_usage WHERE pkg_id = p AND bin_id = b;
	INSERT INTO library_api_usage
	SELECT DISTINCT p, b, t1.func_addr, t2.api_type, t2.api_id FROM
	lib_callgraph AS t1
	INNER JOIN (
		SELECT DISTINCT func_addr, api_type, api_id FROM binary_api_usage
		WHERE pkg_id = p AND bin_id = b
	) AS t2
	ON t1.call_addr = t2.func_addr;

	DELETE FROM library_instr_usage WHERE pkg_id = p AND bin_id = b;
	INSERT INTO library_instr_usage
	SELECT DISTINCT p, b, t1.func_addr, t2.instr FROM
	lib_callgraph AS t1
	INNER JOIN (
		SELECT DISTINCT func_addr, api_type, api_id FROM binary_instr_usage
		WHERE pkg_id = p AND bin_id = b
	) AS t2
	ON t1.call_addr = t2.func_addr;

	UPDATE binary_list SET callgraph = True, linking = False
	WHERE pkg_id = p AND bin_id = b;

	TRUNCATE TABLE lib_entry;
	TRUNCATE TABLE lib_call;
	TRUNCATE TABLE lib_callgraph;

	RAISE NOTICE 'library % in package %p: callgraph generated', b, p;
END
$$ LANGUAGE plpgsql;
