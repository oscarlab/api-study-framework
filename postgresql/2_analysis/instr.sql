DO $$
BEGIN
IF NOT table_exists('package_opcode_count') THEN
	CREATE TABLE package_opcode_count (
		pkg_id INT NOT NULL,
		opcode BIGINT NOT NULL,
		count INT NOT NULL,
		PRIMARY KEY (pkg_id, opcode)
	);
	CREATE INDEX package_opcode_count_pkg_id_idx
		ON package_opcode_count (pkg_id);
	CREATE INDEX package_opcode_count_opcode_idx
		ON package_opcode_count (opcode);
END IF;

IF NOT table_exists('package_size_count') THEN
	CREATE TABLE package_size_count (
		pkg_id INT NOT NULL,
		size INT NOT NULL,
		count INT NOT NULL,
		PRIMARY KEY (pkg_id, size)
	);
	CREATE INDEX package_size_count_pkg_id_idx
		ON package_size_count (pkg_id);
	CREATE INDEX package_size_count_size_idx
		ON package_size_count (size);
END IF;

END $$ LANGUAGE plpgsql;

BEGIN
IF NOT table_exists('package_prefix_count') THEN
	CREATE TABLE package_prefix_count (
		pkg_id INT NOT NULL,
		prefix BIGINT NOT NULL,
		count INT NOT NULL,
		PRIMARY KEY (pkg_id, prefix)
	);
	CREATE INDEX package_prefix_count_pkg_id_idx
		ON package_prefix_count (pkg_id);
	CREATE INDEX package_prefix_count_prefix_idx
		ON package_prefix_count (prefix);
END IF;

END $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analyze_opcode(p INT)
RETURNS void AS $$
DECLARE
	time1 TIMESTAMP;
	time2 TIMESTAMP;

BEGIN
	RAISE NOTICE 'analyze opcodes in package %', p;

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
		UPDATE package_id SET instr = True WHERE id = p;
		RETURN;
	END IF;

	IF EXISTS (
		SELECT * FROM pkg_bin WHERE callgraph = False
	) THEN
		RAISE EXCEPTION 'binary not resolved: %', p;
	END IF;


	DELETE FROM package_opcode_count WHERE pkg_id = p;
	DELETE FROM package_size_count WHERE pkg_id = p;
	DELETE FROM package_prefix_count WHERE pkg_id = p;

	INSERT INTO package_opcode_count
		SELECT p, t1.opcode, SUM(t1.count) FROM
		binary_opcode_usage AS t1
		INNER JOIN
		pkg_bin AS t2
		ON t1.pkg_id = p AND t1.bin_id = t2.bin_id
		GROUP BY t1.opcode;


	INSERT INTO package_size_count
		SELECT p, t1.size, SUM(t1.count) FROM
		binary_opcode_usage AS t1
		INNER JOIN
		pkg_bin AS t2
		ON t1.pkg_id = p AND t1.bin_id = t2.bin_id
		GROUP BY t1.size;

	INSERT INTO package_prefix_count
		SELECT p, t1.prefix, SUM(t1.count) FROM
		prefix_counts AS t1
		INNER JOIN
		pkg_bin AS t2
		ON t1.pkg_id = p AND t1.bin_id = t2.bin_id
		GROUP BY t1.prefix;

	time2 := clock_timestamp();
	RAISE NOTICE 'Time: %', time2 - time1;
	time1 := time2;
END
$$ LANGUAGE plpgsql;
