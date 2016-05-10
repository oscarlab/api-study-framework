DO $$
BEGIN
IF NOT table_exists('package_instr_count') THEN
	CREATE TABLE package_instr_count (
		pkg_id INT NOT NULL,
		instr VARCHAR(15) NOT NULL,
		count INT NOT NULL,
		PRIMARY KEY (pkg_id, bin_id, instr)
	);
	CREATE INDEX package_instr_count_pkg_id_idx
		ON package_instr_count (pkg_id);
	CREATE INDEX package_instr_count_instr_idx
		ON package_instr_count (instr);
END IF;

END $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analyze_instr(p INT)
RETURNS void AS $$

BEGIN
	RAISE NOTICE 'analyze instructions in package %', p;

	time1 := clock_timestamp();

	DELETE FROM package_instr_count WHERE pkg_id = p;

	INSERT INTO package_instr_count
		SELECT instr, SUM(count) FROM binary_instr_usage
		WHERE pkg_id = p
		GROUP BY instr

	time2 := clock_timestamp();
	RAISE NOTICE 'Time: %', time2 - time1;
	time1 := time2;
END
$$ LANGUAGE plpgsql;
