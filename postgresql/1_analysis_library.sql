DO $$
BEGIN
IF NOT table_exists('library_call') THEN
	CREATE TABLE library_call (
		pkg_id INT NOT NULL, bin_id INT NOT NULL,
		func_addr INT NOT NULL,
		call_name VARCHAR NOT NULL,
		PRIMARY KEY (pkg_id, bin_id, func_addr, call_name)
	);
	CREATE INDEX library_call_pkg_id_bin_id_idx
		ON library_call (pkg_id, bin_id);
	CREATE INDEX library_call_pkg_id_bin_id_func_addr_idx
		ON library_call (pkg_id, bin_id, func_addr);
END IF;

IF NOT table_exists('library_syscall') THEN
	CREATE TABLE library_syscall (
		pkg_id INT NOT NULL, bin_id INT NOT NULL,
		func_addr INT NOT NULL,
		syscall SMALLINT NOT NULL,
		PRIMARY KEY (pkg_id, bin_id, func_addr, syscall)
	);
	CREATE INDEX library_syscall_pkg_id_bin_id_func_addr_idx
		ON library_syscall (pkg_id, bin_id, func_addr);
END IF;

IF NOT table_exists('library_vecsyscall') THEN
	CREATE TABLE library_vecsyscall (
		pkg_id INT NOT NULL, bin_id INT NOT NULL,
		func_addr INT NOT NULL,
		syscall SMALLINT NOT NULL,
		request BIGINT NOT NULL,
		PRIMARY KEY (pkg_id, bin_id, func_addr, syscall, request)
	);
	CREATE INDEX library_syscall_pkg_id_bin_id_idx
		ON library_syscall (pkg_id, bin_id, func_addr);
END IF;

IF NOT table_exists('library_fileaccess') THEN
	CREATE TABLE library_fileaccess (
		pkg_id INT NOT NULL, bin_id INT NOT NULL,
		func_addr INT NOT NULL,
		file VARCHAR NOT NULL,
		PRIMARY KEY (pkg_id, bin_id, func_addr, file)
	);
	CREATE INDEX library_fileaccess_pkg_id_bin_id_func_addr_idx
		ON library_fileaccess (pkg_id, bin_id, func_addr);
END IF;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analysis_library(p INT, b INT)
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
		SELECT DISTINCT func_addr FROM binary_symbol
		WHERE pkg_id = p AND bin_id = b
		AND defined = True
		AND func_addr != 0;

	CREATE TEMP TABLE IF NOT EXISTS lib_call (
		func_addr INT NOT NULL,
		call_addr INT NOT NULL,
		PRIMARY KEY (func_addr, call_addr));
	INSERT INTO lib_call
		SELECT DISTINCT func_addr, call_addr FROM binary_call
		WHERE pkg_id = p AND bin_id = b AND call_addr IS NOT NULL
		UNION
		SELECT DISTINCT func_addr, call_addr FROM binary_unknown_call
		WHERE pkg_id = p AND bin_id = b
		AND known = True
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
	SELECT DISTINCT p, b, t1.func_addr, t2.call_name FROM
	lib_callgraph AS t1
	INNER JOIN (
		SELECT DISTINCT func_addr, call_name FROM binary_call
		WHERE pkg_id = p AND bin_id = b AND call_addr IS NULL
		UNION
		SELECT DISTINCT func_addr, call_name FROM binary_unknown_call
		WHERE pkg_id = p AND bin_id = b
		AND known = True
		and call_addr IS NULL
	) AS t2
	ON t1.call_addr = t2.func_addr;

	DELETE FROM library_syscall WHERE pkg_id = p AND bin_id = b;
	INSERT INTO library_syscall
	SELECT DISTINCT p, b, t1.func_addr, t2.syscall FROM
	lib_callgraph AS t1
	INNER JOIN (
		SELECT DISTINCT func_addr, syscall FROM binary_syscall
		WHERE pkg_id = p AND bin_id = b
		UNION
		SELECT DISTINCT func_addr, syscall FROM binary_unknown_syscall
		WHERE pkg_id = p AND bin_id = b
		AND known = True
	) AS t2
	ON t1.call_addr = t2.func_addr;

	DELETE FROM library_vecsyscall WHERE pkg_id = p AND bin_id = b;
	INSERT INTO library_vecsyscall
	SELECT DISTINCT p, b, t1.func_addr, t2.syscall, t2.request FROM
	lib_callgraph AS t1
	INNER JOIN (
		SELECT DISTINCT func_addr, syscall, request
		FROM binary_vecsyscall
		WHERE pkg_id = p AND bin_id = b
		UNION
		SELECT DISTINCT func_addr, syscall, request
		FROM binary_unknown_vecsyscall
		WHERE pkg_id = p AND bin_id = b
		AND known = True
	) AS t2
	ON t1.call_addr = t2.func_addr;

	DELETE FROM library_fileaccess WHERE pkg_id = p AND bin_id = b;
	INSERT INTO library_fileaccess
	SELECT DISTINCT p, b, t1.func_addr, t2.file FROM
	lib_callgraph AS t1
	INNER JOIN (
		SELECT DISTINCT func_addr, file FROM binary_fileaccess
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
