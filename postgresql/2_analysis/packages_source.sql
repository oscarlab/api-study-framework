DO $$
BEGIN
IF NOT table_exists('package_opcode_source') THEN
	CREATE TABLE package_opcode_source (
		pkg_id INT NOT NULL,
		source INT NOT NULL,
		prefix BIGINT NULL,
		opcode BIGINT NOT NULL,
		size INT NOT NULL,
		mnem VARCHAR NOT NULL,
		count INT NOT NULL,
		PRIMARY KEY (pkg_id, source, prefix, opcode, size, mnem)
	);
	CREATE INDEX package_opcode_source_prefix_opcode_size_idx
		ON package_opcode_source (prefix, opcode, size);
END IF;

IF NOT table_exists('package_reg_usage') THEN
	CREATE TABLE package_reg_usage (
		pkg_id INT NOT NULL,
		register VARCHAR NOT NULL,
		count INT NOT NULL,
		PRIMARY KEY (pkg_id, register)
	);
	CREATE INDEX package_reg_usage_pkg_id_idx
		ON package_reg_usage (pkg_id);
	CREATE INDEX package_reg_usage_register_idx
		ON package_reg_usage (register);
END IF;

IF NOT table_exists('package_addressing_mode') THEN
	CREATE TABLE package_addressing_mode (
		pkg_id INT NOT NULL,
		addressing_mode VARCHAR NOT NULL,
		count INT NOT NULL,
		PRIMARY KEY (pkg_id, addressing_mode)
	);
	CREATE INDEX package_addressing_mode_pkg_id_idx
		ON package_addressing_mode (pkg_id);
	CREATE INDEX package_addressing_mode_AM_idx
		ON package_addressing_mode (addressing_mode);
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

	DELETE FROM package_reg_usage WHERE pkg_id = p;
	INSERT INTO package_reg_usage
		SELECT p, t1.register, SUM(count)
		FROM executable_reg_usage AS t1
		INNER JOIN
		pkg_bin AS t2
		ON t1.pkg_id = p AND t1.bin_id = t2.bin_id
		GROUP BY p, t1.register;

	DELETE FROM package_addressing_mode WHERE pkg_id = p;
	INSERT INTO package_addressing_mode
		SELECT p, t1.addressing_mode, SUM(count)
		FROM executable_addressing_mode AS t1
		INNER JOIN
		pkg_bin AS t2
		ON t1.pkg_id = p AND t1.bin_id = t2.bin_id
		GROUP BY p, t1.addressing_mode;

	UPDATE package_id SET footprint = True WHERE id = p;

	TRUNCATE TABLE pkg_bin;

	RAISE NOTICE 'package %: source footprint generated', p;
END
$$ LANGUAGE plpgsql;
