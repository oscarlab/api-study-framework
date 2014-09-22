CREATE TABLE IF NOT EXISTS analysis_call (
bin_id INT NOT NULL, func_addr INT NOT NULL, call_name VARCHAR NOT NULL,
PRIMARY KEY (bin_id, func_addr, call_name));

CREATE TABLE IF NOT EXISTS analysis_syscall (
bin_id INT NOT NULL, func_addr INT NOT NULL, syscall INT NOT NULL,
PRIMARY KEY (bin_id, func_addr, syscall));

CREATE TEMP TABLE lib_id AS
SELECT DISTINCT bin_id FROM binary_list
WHERE type = 'lib' AND
EXISTS (
	SELECT * FROM binary_id
	WHERE id = bin_id AND callgraph_generated = False
);

CREATE TEMP TABLE lib_entry (func_addr INT NOT NULL PRIMARY KEY);
CREATE TEMP TABLE lib_local_call (
	func_addr INT NOT NULL, call_addr INT NOT NULL,
	PRIMARY KEY (func_addr, call_addr));
CREATE TEMP TABLE lib_exit (
	func_addr INT NOT NULL, call_name VARCHAR NOT NULL,
	PRIMARY KEY (func_addr, call_name));
CREATE TEMP TABLE lib_syscall (
	func_addr INT NOT NULL, syscall INT NOT NULL,
	PRIMARY KEY (func_addr, syscall));
CREATE TEMP TABLE lib_callgraph (
	func_addr INT NOT NULL, call_addr INT NOT NULL,
	PRIMARY KEY (func_addr, call_addr));

DO $$
DECLARE
	total INT := COUNT(*) FROM lib_id;
	cnt INT := 0;
	b INT;
	ld_name VARCHAR := '/lib/x86_64-linux-gnu/ld-2.15.so';
	ld_entry INT := 5808;

BEGIN
	FOR b IN (SELECT * FROM lib_id) LOOP
		INSERT INTO lib_entry
		SELECT DISTINCT func_addr FROM binary_symbol
		WHERE bin_id = b AND defined = True AND func_addr != 0
		UNION
		SELECT ld_entry FROM binary_id
		WHERE id = b AND binary_name = ld_name;

		INSERT INTO lib_local_call
		SELECT DISTINCT func_addr, call_addr FROM binary_call
		WHERE bin_id = b AND call_addr IS NOT NULL
		UNION
		SELECT DISTINCT func_addr, call_addr FROM binary_unknown_call
		WHERE bin_id = b AND call_addr IS NOT NULL;

		INSERT INTO lib_exit
		SELECT DISTINCT func_addr, call_name FROM binary_call
		WHERE bin_id = b AND call_addr IS NULL
		UNION
		SELECT DISTINCT func_addr, call_name FROM binary_unknown_call
		WHERE bin_id = b AND call_addr IS NULL and call_name IS NOT NULL;

		INSERT INTO lib_syscall
		SELECT DISTINCT func_addr, syscall FROM binary_syscall
		WHERE bin_id = b
		UNION
		SELECT DISTINCT func_addr, syscall FROM binary_unknown_syscall
		WHERE bin_id = b AND syscall IS NOT NULL;

		WITH RECURSIVE
		analysis (func_addr, call_addr)
		AS (
			SELECT func_addr, func_addr FROM lib_entry
			UNION
			SELECT t1.func_addr, t2.call_addr FROM
			analysis AS t1
			INNER JOIN
			lib_local_call AS t2
			ON t1.call_addr = t2.func_addr
		)
		INSERT INTO lib_callgraph SELECT * FROM analysis;

		DELETE FROM analysis_call WHERE bin_id = b;
		INSERT INTO analysis_call
		SELECT DISTINCT b, t1.func_addr, t2.call_name FROM
		lib_callgraph AS t1 INNER JOIN lib_exit AS t2
		ON t1.call_addr = t2.func_addr;

		DELETE FROM analysis_syscall WHERE bin_id = b;
		INSERT INTO analysis_syscall
		SELECT DISTINCT b, t1.func_addr, t2.syscall FROM
		lib_callgraph AS t1 INNER JOIN lib_syscall AS t2
		on t1.call_addr = t2.func_addr;

		UPDATE binary_id SET
		callgraph_generated = True,
		dep_generated = False
		WHERE id = b;

		TRUNCATE TABLE lib_entry;
		TRUNCATE TABLE lib_local_call;
		TRUNCATE TABLE lib_exit;
		TRUNCATE TABLE lib_callgraph;
		TRUNCATE TABLE lib_syscall;

		cnt := cnt + 1;
		RAISE NOTICE '% / %', cnt, total;
	END LOOP;
END $$;

