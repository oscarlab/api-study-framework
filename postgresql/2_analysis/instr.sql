DO $$
BEGIN
IF NOT table_exists('package_instr_count') THEN
	CREATE TABLE package_instr_count (
		pkg_id INT NOT NULL,
		instr VARCHAR(15) NOT NULL,
		count INT NOT NULL,
		PRIMARY KEY (pkg_id, instr)
	);
	CREATE INDEX package_instr_count_pkg_id_idx
		ON package_instr_count (pkg_id);
	CREATE INDEX package_instr_count_instr_idx
		ON package_instr_count (instr);
END IF;

END $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analyze_instr(p INT)
RETURNS void AS $$
DECLARE
	time1 TIMESTAMP;
	time2 TIMESTAMP;

BEGIN
	RAISE NOTICE 'analyze instructions in package %', p;

	time1 := clock_timestamp();

	CREATE TEMP TABLE IF NOT EXISTS pkg_bin (
		bin_id INT NOT NULL,
		callgraph BOOLEAN,
		PRIMARY KEY(bin_id));
	INSERT INTO pkg_bin
		SELECT DISTINCT bin_id, callgraph FROM binary_list
		WHERE pkg_id = p AND (type = 'exe' OR type = 'lib');

	IF NOT EXISTS (
		SELECT * FROM pkg_bin
	) THEN
		UPDATE package_id SET footprint = True WHERE id = p;
		RETURN;
	END IF;

	IF EXISTS (
		SELECT * FROM pkg_bin WHERE callgraph = False
	) THEN
		RAISE EXCEPTION 'binary not resolved: %', p;
	END IF;


	DELETE FROM package_instr_count WHERE pkg_id = p;

	INSERT INTO package_instr_count
		SELECT p, t1.instr, SUM(t1.count) FROM
		binary_instr_usage AS t1
		INNER JOIN
		pkg_bin AS t2
		ON t1.pkg_id = p AND t1.bin_id = t2.bin_id
		GROUP BY t1.instr;

	time2 := clock_timestamp();
	RAISE NOTICE 'Time: %', time2 - time1;
	time1 := time2;
END
$$ LANGUAGE plpgsql;
