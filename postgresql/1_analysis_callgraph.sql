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

CREATE FUNCTION analysis_callgraph ()
RETURNS void AS $$
DECLARE
	total INT := COUNT(*) FROM lib_id;
	cnt INT := 0;
	b INT;

BEGIN
	FOR b IN (SELECT * FROM lib_id) LOOP
		CREATE TEMP TABLE lib_entry AS
		SELECT DISTINCT func_addr FROM binary_symbol
		WHERE bin_id = b AND defined = True AND func_addr != 0;

		CREATE TEMP TABLE lib_local_call AS
		SELECT DISTINCT func_addr, call_addr FROM binary_call
		WHERE bin_id = b AND call_addr IS NOT NULL
		UNION
		SELECT DISTINCT func_addr, call_addr FROM binary_unknown_call
		WHERE bin_id = b AND call_addr IS NOT NULL;

		CREATE TEMP TABLE lib_exit AS
		SELECT DISTINCT func_addr, call_name FROM binary_call
		WHERE bin_id = b AND call_addr IS NULL
		UNION
		SELECT DISTINCT func_addr, call_name FROM binary_unknown_call
		WHERE bin_id = b AND call_addr IS NULL and call_name IS NOT NULL;

		CREATE TEMP TABLE lib_syscall AS
		SELECT DISTINCT func_addr, syscall FROM binary_syscall
		WHERE bin_id = b
		UNION
		SELECT DISTINCT func_addr, syscall FROM binary_unknown_syscall
		WHERE bin_id = b AND syscall IS NOT NULL;

		CREATE TEMP TABLE lib_callgraph
		(func_addr INT NOT NULL, call_addr INT NOT NULL);

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

		UPDATE binary_id SET callgraph_generated = True
		WHERE id = b;

		DROP TABLE lib_entry;
		DROP TABLE lib_local_call;
		DROP TABLE lib_exit;
		DROP TABLE lib_callgraph;
		DROP TABLE lib_syscall;

		cnt := cnt + 1;
		RAISE NOTICE '% / %', cnt, total;
	END LOOP;
END;
$$ LANGUAGE plpgsql;

SELECT analysis_callgraph();

DROP FUNCTION analysis_callgraph();
