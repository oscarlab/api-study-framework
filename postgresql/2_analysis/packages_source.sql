DO $$
BEGIN
IF NOT table_exists('package_opcode_source') THEN
	CREATE TABLE package_opcode_usage (
		pkg_id INT NOT NULL,
		source INT NOT NULL,
		prefix BIGINT NULL,
		opcode BIGINT NOT NULL,
		size INT NOT NULL,
		mnem VARCHAR NOT NULL,
		count INT NOT NULL,
		PRIMARY KEY (pkg_id, source, prefix, opcode, size, mnem)
	);
	CREATE INDEX package_opcode_usage_prefix_opcode_size_idx
		ON package_opcode_usage (prefix, opcode, size);
END IF;
END $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analyze_package_source(p INT)
RETURNS void AS $$

DECLARE
	b INT;

BEGIN
	RAISE NOTICE 'analyze package: %', p;

	CREATE TEMP TABLE IF NOT EXISTS pkg_bin (
		bin_id INT NOT NULL,
		callgraph BOOLEAN,
		PRIMARY KEY(bin_id));
	INSERT INTO pkg_bin
		SELECT DISTINCT bin_id, callgraph FROM binary_list
		WHERE pkg_id = p AND type = 'exe';

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

	DELETE FROM package_opcode_source WHERE pkg_id = p;
	INSERT INTO package_opcode_source
		SELECT p, t1.source, t1.prefix, t1.opcode, t1.size, t1.mnem, SUM(count)
		FROM executable_opcode_source AS t1
		INNER JOIN
		pkg_bin AS t2
		ON t1.pkg_id = p AND t1.bin_id = t2.bin_id
		GROUP BY p, t1.source, t1.prefix, t1.opcode, t1.size, t1.mnem;

	TRUNCATE TABLE pkg_bin;

	RAISE NOTICE 'package %: source footprint generated', p;
END
$$ LANGUAGE plpgsql;
