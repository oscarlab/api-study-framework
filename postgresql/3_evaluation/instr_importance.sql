DO $$
BEGIN
IF NOT table_exists('opcode_importance') THEN
	CREATE TABLE opcode_importance (
		opcode BIGINT NOT NULL,
		opcode_importance_order FLOAT NOT NULL,
		PRIMARY KEY(opcode)
	);
END IF;
END $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analyze_opcode_importance()
RETURNS void AS $$

DECLARE
	total INT := (SELECT COUNT(DISTINCT pkg_id) FROM package_opcode_usage);
	count INT := 1;
	pkg INT;
	i BIGINT;
	pkg_order FLOAT;

BEGIN
	PERFORM (SELECT update_package_install());

	CREATE TEMP TABLE IF NOT EXISTS opcode_tmp (
		opcode BIGINT NOT NULL,
		percent_order FLOAT NOT NULL,
		PRIMARY KEY(opcode));

	CREATE TEMP TABLE IF NOT EXISTS pkg_opcode_tmp (
		opcode BIGINT NOT NULL,
		PRIMARY KEY(opcode));

	FOR pkg IN (SELECT DISTINCT pkg_id FROM package_opcode_usage) LOOP

		RAISE NOTICE 'analyze package %/%', count, total;
		count := count + 1;

		INSERT INTO pkg_opcode_tmp
			SELECT opcode FROM package_opcode_usage
			WHERE pkg_id = pkg;

		pkg_order := (SELECT percent_order FROM package_install WHERE pkg_id = pkg);

		for i IN (SELECT * FROM pkg_opcode_tmp) LOOP
			IF EXISTS(
				SELECT * FROM opcode_tmp
				WHERE opcode = i
			) THEN
				UPDATE opcode_tmp
				SET percent_order = percent_order + pkg_order
				WHERE opcode = i;
			ELSE
				INSERT INTO opcode_tmp VALUES (i, pkg_order);
			END IF;
		END LOOP;

		TRUNCATE pkg_opcode_tmp;
	END LOOP;

	TRUNCATE TABLE opcode_importance;
	INSERT INTO opcode_importance
		SELECT opcode, percent_order
		FROM opcode_tmp
		ORDER BY percent_order DESC;

	TRUNCATE TABLE opcode_tmp;
END
$$ LANGUAGE plpgsql;
