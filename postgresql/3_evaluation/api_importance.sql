DO $$
BEGIN
IF NOT table_exists('api_importance') THEN
	CREATE TABLE api_importance (
		api_type SMALLINT NOT NULL,
		api_id BIGINT NOT NULL,
		api_importance_order FLOAT NOT NULL,
		PRIMARY KEY(api_type, api_id)
	);
END IF;

IF NOT table_exists('library_call_api_importance') THEN
	CREATE TABLE library_Call_api_importance (
		bin_id INT NOT NULL,
		call VARCHAR NOT NULL,
		api_importance_order FLOAT,
		PRIMARY KEY (bin_id, call)
	);
END IF;
END $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analysis_library_call_api_importance()
RETURNS void AS $$

DECLARE
	total INT := (SELECT COUNT(DISTINCT pkg_id) FROM package_call);
	count INT := 1;
	p INT;
	dep INT;
	call INT;
	order FLOAT;
BEGIN
	CREATE TEMP TABLE IF NOT EXISTS call_tmp (
		bin_id INT NOT NULL, func_addr INT NOT NULL,
		percent_order FLOAT,
		PRIMARY KEY(bin_id, func_addr));

	CREATE TEMP TABLE IF NOT EXISTS pkg_call_tmp (
		bin_id INT NOT NULL, func_addr INT NOT NULL,
		PRIMARY KEY(bin_id, func_addr));

	FOR p IN (SELECT DISTINCT pkg_id FROM package_call) LOOP

		RAISE NOTICE 'analyze package %/%', count, total;
		count := count + 1;

		INSERT INTO pkg_call_tmp
			SELECT t2.bin_id, t2.func_addr FROM
			package_call AS t1 INNER JOIN libc_symbol AS t2
			ON t1.dep_bin_id = t2.bin_id AND t1.call = t2.func_addr
			WHERE t1.pkg_id = p;

		order := (SELECT percent_order FROM package_install WHERE pkg_id = p);

		FOR dep, call IN (SELECT * FROM pkg_call_tmp) LOOP
			IF EXISTS(
				SELECT * FROM call_tmp WHERE
				bin_id = dep AND func_addr = call
			) THEN
				UPDATE call_tmp
				SET precent_order = precent_order + order
				WHERE bin_id = dep AND func_addr = call;
			ELSE
				INSERT INTO call_tmp VALUES (dep, call, order);
			END IF;
		END LOOP;

		TRUNCATE pkg_call_tmp;
	END LOOP;

	TRUNCATE TABLE call_popularity;
	INSERT INTO call_popularity
		SELECT t1.bin_id, t2,symbol_name,
		t1.popularity
		FROM call_tmp AS t1
		JOIN
		binary_symbol AS t2
		ON
		t1.bin_id = t2.bin_id AND t1.func_addr = t2.func_addr
		ORDER BY t1.popularity DESC, t1.func_addr;

	TRUNCATE TABLE call_tmp;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analysis_api_importance()
RETURNS void AS $$

DECLARE
	total INT := (SELECT COUNT(DISTINCT pkg_id) FROM package_api_usage);
	count INT := 1;
	p INT;
	type SMALLINT;
	id BIGINT;
	order FLOAT;

BEGIN
	CREATE TEMP TABLE IF NOT EXISTS api_tmp (
		api_type SMALLINT NOT NULL,
		api_id BIGINT NOT NULL,
		percent_order FLOAT NOT NULL,
		PRIMARY KEY(api_type, api_id));

	CREATE TEMP TABLE IF NOT EXISTS pkg_api_tmp (
		api_type SMALLINT NOT NULL,
		api_id BIGINT NOT NULL,
		PRIMARY KEY(api_type, api_id));

	FOR p IN (SELECT DISTINCT pkg_id FROM package_api_usage) LOOP

		RAISE NOTICE 'analyze package %/%', count, total;
		count := count + 1;

		INSERT INTO pkg_api_tmp
			SELECT api_type, api_id FROM package_api_usage
			WHERE pkg_id = p;

		order := (SELECT percent_order FROM package_install WHERE pkg_id = p);

		for type, id IN (SELECT * FROM pkg_api_tmp) LOOP
			IF EXISTS(
				SELECT * FROM api_tmp
				WHERE api_type = type AND api_id = id
			) THEN
				UPDATE api_tmp
				SET percent_order = percent_order + order
				WHERE api_type = type
				AND   api_id = id;
			ELSE
				INSERT INTO api_tmp VALUES (type, id, order);
			END IF;
		END LOOP;

		TRUNCATE pkg_api_tmp;
	END LOOP;

	TRUNCATE TABLE api_importance;
	INSERT INTO api_importance
		SELECT api_type, api_id,
		api_importance_order
		FROM api_tmp
		ORDER BY api_importance_order DESC, api_type, api_id;

	TRUNCATE TABLE api_tmp;
END
$$ LANGUAGE plpgsql;
