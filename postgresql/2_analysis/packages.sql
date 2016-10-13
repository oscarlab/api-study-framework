DO $$
BEGIN
IF NOT table_exists('package_call') THEN
	CREATE TABLE package_call (
		pkg_id INT NOT NULL,
		dep_bin_id INT NOT NULL,
		call_addr INT NOT NULL,
		PRIMARY KEY(pkg_id, dep_bin_id, call_addr)
	);
	CREATE INDEX package_call_pkg_id_idx
		ON package_call (pkg_id);
END IF;

IF NOT table_exists('package_api_usage') THEN
	CREATE TABLE package_api_usage (
		pkg_id INT NOT NULL,
		api_type SMALLINT NOT NULL,
		api_id BIGINT NOT NULL,
		PRIMARY KEY (pkg_id, api_type, api_id)
	);
	CREATE INDEX package_api_usage_pkg_id_idx
		ON package_api_usage (pkg_id);
END IF;

IF NOT table_exists('package_opcode_usage') THEN
	CREATE TABLE package_opcode_usage (
		pkg_id INT NOT NULL,
		prefix BIGINT NULL,
		opcode BIGINT NOT NULL,
		size INT, NOT NULL,
		mnem, VARCHAR, NOT NULL,
		count, INT, NOT NULL,
		PRIMARY KEY (pkg_id, prefix, opcode, size, mnem)
	);
	CREATE INDEX package_opcode_usage_prefix_opcode_size_idx
		ON package_opcode_usage (prefix, opcode, size);
END IF;
END $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analyze_package(p INT)
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

	DELETE FROM package_call WHERE pkg_id = p;
	INSERT INTO package_call
		SELECT DISTINCT p, t1.dep_bin_id, t1.call_addr
		FROM executable_call AS t1
		INNER JOIN
		pkg_bin AS t2
		ON t1.pkg_id = p AND t1.bin_id = t2.bin_id;

	DELETE FROM package_api_usage WHERE pkg_id = p;
	INSERT INTO package_api_usage
		SELECT DISTINCT p, t1.api_type, t1.api_id
		FROM executable_api_usage AS t1
		INNER JOIN
		pkg_bin AS t2
		ON t1.pkg_id = p AND t1.bin_id = t2.bin_id;

	DELETE FROM package_opcode_usage WHERE pkg_id = p;
	INSERT INTO package_opcode_usage
		SELECT p, t1.prefix, t1.opcode, t1.size, t1.mnem, SUM(count)
		FROM executable_opcode_usage AS t1
		INNER JOIN
		pkg_bin AS t2
		ON t1.pkg_id = p AND t1.bin_id = t2.bin_id
		GROUP BY p, t1.prefix, t1.opcode, t1.size, t1.mnem;

	UPDATE package_id SET footprint = True WHERE id = p;

	TRUNCATE TABLE pkg_bin;

	RAISE NOTICE 'package %: footprint generated', p;
END
$$ LANGUAGE plpgsql;
