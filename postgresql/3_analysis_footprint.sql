CREATE TABLE IF NOT EXISTS analysis_footprint (
bin_id INT NOT NULL, syscall INT NOT NULL,
PRIMARY KEY(bin_id, syscall));

CREATE TEMP TABLE bin_id AS
SELECT DISTINCT id AS bin_id FROM binary_id AS t
WHERE footprint_generated = False AND
EXISTS (
	SELECT * FROM binary_list WHERE
	bin_id = t.id AND type = 'exe'
);

CREATE TEMP TABLE ld_call (
	call_name VARCHAR NOT NULL PRIMARY KEY);
CREATE TEMP TABLE dep_id (
	dep_id INT NOT NULL PRIMARY KEY);
CREATE TEMP TABLE dep_sym (
	dep_id INT NOT NULL,
	symbol_name VARCHAR NOT NULL,
	func_addr INT NOT NULL);
CREATE TEMP TABLE dep_call (
	dep_id INT NOT NULL,
	symbol_name VARCHAR,
	func_addr INT NOT NULL,
	call_name VARCHAR);

DO $$
DECLARE
	total INT := COUNT(*) FROM bin_id;
	cnt INT := 0;
	b INT;
	s INT;
	ld_id INT := id FROM binary_id WHERE binary_name = '/lib/x86_64-linux-gnu/ld-2.15.so';
	ld_entry INT := 5808;
	dep_on_ld BOOLEAN;

BEGIN
	INSERT INTO ld_call SELECT call_name FROM analysis_call
	WHERE bin_id = ld_id AND func_addr = ld_entry;

	FOR b IN (SELECT * FROM bin_id) LOOP
		RAISE NOTICE 'analyze binary: %', b;

		INSERT INTO dep_id
		SELECT DISTINCT dep_id FROM analysis_dep
		WHERE bin_id = b;

		dep_on_ld := EXISTS (SELECT * FROM dep_id WHERE dep_id = ld_id);

		FOR s IN (SELECT * FROM dep_id) LOOP
			RAISE NOTICE 'import dependency: %', s;
			INSERT INTO dep_sym
			SELECT DISTINCT s, symbol_name, func_addr FROM binary_symbol
			WHERE bin_id = s AND defined = 'True';
		END LOOP;

		TRUNCATE TABLE dep_id;
		RAISE NOTICE 'dep_sym: %', (SELECT COUNT(*) FROM dep_sym);

		INSERT INTO dep_call
		SELECT DISTINCT
		t1.dep_id, t3.symbol_name, t2.func_addr, t2.call_name
		FROM dep_id AS t1
		INNER JOIN
		analysis_call AS t2
		ON t1.dep_id = t2.bin_id
		INNER JOIN
		binary_symbol AS t3
		ON t1.dep_id = t3.bin_id AND t2.func_addr = t3.func_addr
		UNION
		SELECT dep_id, symbol_name, func_addr, NULL FROM dep_sym
		UNION
		SELECT ld_id, NULL, ld_entry, call_name FROM ld_call
		WHERE dep_on_ld = 'True';

		TRUNCATE TABLE dep_sym;
		RAISE NOTICE 'dep_call: %', (SELECT COUNT(*) FROM dep_call);

		DELETE FROM analysis_footprint WHERE bin_id = b;

		WITH RECURSIVE
		analysis(bin_id, func_addr, call_name) AS (
			SELECT 0, 0, symbol_name FROM binary_symbol
			WHERE bin_id = b AND defined = 'False'
			UNION
			VALUES (0, 0, '.init'), (0, 0, '.fini')
			UNION
			SELECT DISTINCT
			t2.dep_id, t2.func_addr, t2.call_name
			FROM analysis AS t1
			INNER JOIN
			dep_call AS t2
			ON t1.call_name = t2.symbol_name
		)
		INSERT INTO analysis_footprint
		SELECT DISTINCT b, t2.syscall
		FROM analysis AS t1
		INNER JOIN
		analysis_syscall AS t2
		ON t1.bin_id != 0 AND t2.func_addr != 0
		AND t1.func_addr = t2.func_addr
		UNION
		SELECT DISTINCT b, syscall FROM binary_syscall
		WHERE bin_id = b
		UNION
		SELECT DISTINCT b, syscall FROM binary_unknown_syscall
		WHERE bin_id = b AND syscall IS NOT NULL;

		UPDATE binary_id SET
		footprint_generated = True
		WHERE id = b;

		TRUNCATE TABLE dep_call;

		cnt := cnt + 1;
		RAISE NOTICE '% / %', cnt, total;
	END LOOP;
END $$;
