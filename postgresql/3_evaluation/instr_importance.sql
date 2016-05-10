DO $$
BEGIN
IF NOT table_exists('instr_importance') THEN
	CREATE TABLE instr_importance (
		instr VARCHAR(15) NOT NULL,
		instr_importance_order FLOAT NOT NULL,
		PRIMARY KEY(instr)
	);
END IF;
END $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analyze_instr_importance()
RETURNS void AS $$

DECLARE
	total INT := (SELECT COUNT(DISTINCT pkg_id) FROM package_instr_usage);
	count INT := 1;
	pkg INT;
	i VARCHAR(15);
	pkg_order FLOAT;

BEGIN
	PERFORM (SELECT update_package_install());

	CREATE TEMP TABLE IF NOT EXISTS instr_tmp (
		instr VARCHAR(15) NOT NULL,
		percent_order FLOAT NOT NULL,
		PRIMARY KEY(instr));

	CREATE TEMP TABLE IF NOT EXISTS pkg_instr_tmp (
		instr VARCHAR(15) NOT NULL,
		PRIMARY KEY(instr));

	FOR pkg IN (SELECT DISTINCT pkg_id FROM package_instr_usage) LOOP

		RAISE NOTICE 'analyze package %/%', count, total;
		count := count + 1;

		INSERT INTO pkg_instr_tmp
			SELECT instr FROM package_instr_usage
			WHERE pkg_id = pkg;

		pkg_order := (SELECT percent_order FROM package_install WHERE pkg_id = pkg);

		for i IN (SELECT * FROM pkg_instr_tmp) LOOP
			IF EXISTS(
				SELECT * FROM instr_tmp
				WHERE instr = i
			) THEN
				UPDATE instr_tmp
				SET percent_order = percent_order + pkg_order
				WHERE instr = i;
			ELSE
				INSERT INTO instr_tmp VALUES (type, id, pkg_order);
			END IF;
		END LOOP;

		TRUNCATE pkg_instr_tmp;
	END LOOP;

	TRUNCATE TABLE instr_importance;
	INSERT INTO instr_importance
		SELECT instr, percent_order
		FROM instr_tmp
		ORDER BY percent_order DESC, instr_type, instr_id;

	TRUNCATE TABLE instr_tmp;
END
$$ LANGUAGE plpgsql;
