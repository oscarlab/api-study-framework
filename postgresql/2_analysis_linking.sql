DO $$
BEGIN
IF NOT table_exists('binary_linking') THEN
	CREATE TABLE binary_linking (
		pkg_id INT NOT NULL, bin_id INT NOT NULL,
		dep_pkg_id INT NOT NULL,
		dep_bin_id INT NOT NULL,
		dep_name VARCHAR,
		PRIMARY KEY (pkg_id, bin_id, dep_pkg_id, dep_bin_id)
	);
	CREATE INDEX binary_linking_pkg_id_bin_id_idx
		ON binary_linking (pkg_id, bin_id);
	CREATE INDEX binary_linking_dep_pkg_id_dep_bin_id_idx
		ON binary_linking (dep_pkg_id, dep_bin_id);
END IF;
END $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analysis_linking(p INT, b INT, is_link BOOLEAN, do_reverse BOOLEAN)
RETURNS void AS $$

DECLARE
	file VARCHAR := (SELECT file_name FROM binary_id WHERE id = b);

BEGIN
	CREATE TEMP TABLE IF NOT EXISTS lnk (
		bin_id INT NOT NULL, dep_name VARCHAR,
		PRIMARY KEY (bin_id));

	IF is_link THEN
		INSERT INTO lnk
			SELECT target, NULL
			FROM binary_link
			WHERE pkg_id = p AND lnk_id = b;
	ELSE
		INSERT INTO lnk
			SELECT t2.id, t2.file_name AS bin_id FROM
			binary_dependency AS t1 INNER JOIN binary_id AS t2
			ON  t1.pkg_id = p
			AND t1.bin_id = b
			AND t1.dependency = t2.file_name
			UNION
			SELECT interp, file_name FROM
			binary_interp INNER JOIN binary_id
			ON pkg_id = p AND bin_id = b AND interp = id;
	END IF;

	DELETE FROM binary_linking WHERE pkg_id = p AND bin_id = b;

	INSERT INTO binary_linking
		SELECT p, b, t2.pkg_id, t1.bin_id, t1.dep_name
		FROM lnk AS t1
		INNER JOIN binary_list AS t2
		ON t1.bin_id = t2.bin_id
		UNION
		SELECT p, b, t2.pkg_id, t1.bin_id, t1.dep_name
		FROM lnk AS t1
		INNER JOIN binary_link AS t2
		ON t1.bin_id = t2.lnk_id;

	IF do_reverse THEN
		DELETE FROM binary_linking
		WHERE dep_pkg_id = p AND dep_bin_id = b;

		INSERT INTO binary_linking
			SELECT pkg_id, bin_id, p, b, file
			FROM binary_dependency
			WHERE dependency = file
			UNION
			SELECT pkg_id, lnk_id, p, b, NULL
			FROM binary_link
			WHERE target = b;
	END IF;

	TRUNCATE TABLE lnk;

	UPDATE binary_list SET linking = True WHERE pkg_id = p AND bin_id = b;
	UPDATE binary_link SET linking = True WHERE pkg_id = p AND lnk_id = b;

	RAISE NOTICE 'linking generated: % in package %', b, p;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_link(p INT, b INT)
RETURNS SETOF binary_linking AS $$
DECLARE
	file VARCHAR := (SELECT file_name FROM binary_id WHERE id = b);

BEGIN
	RETURN QUERY WITH RECURSIVE
		analysis (pkg_id, bin_id)
		AS (
			SELECT dep_pkg_id, dep_bin_id FROM
			binary_linking
			WHERE pkg_id = p AND bin_id = b
			AND dep_name IS NULL
			UNION
			SELECT dep_pkg_id, dep_bin_id FROM
			analysis AS t1 INNER JOIN binary_linking AS t2
			ON  t1.pkg_id = t2.pkg_id
			AND t1.bin_id = t2.bin_id
			AND dep_name IS NULL
		) SELECT p, b, t1.pkg_id, t1.bin_id, file FROM
		analysis AS t1 INNER JOIN binary_list AS t2
		ON  t1.pkg_id = t2.pkg_id
		AND t1.bin_id = t2.bin_id
		AND t2.type = 'lib';
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_dependency(p INT, b INT)
RETURNS SETOF binary_linking AS $$
DECLARE
	p1 INT;
	b1 INT;
	d VARCHAR := '';
	unresolved VARCHAR;
	r binary_linking%ROWTYPE;

BEGIN
	CREATE TEMP TABLE IF NOT EXISTS dep (
		pkg_id INT NOT NULL, bin_id INT NOT NULL,
		dep_name VARCHAR NOT NULL,
		PRIMARY KEY (pkg_id, bin_id));
	WITH RECURSIVE
	analysis (pkg_id, bin_id, dep_name)
	AS (
		SELECT dep_pkg_id, dep_bin_id, dep_name FROM
		binary_linking
		WHERE pkg_id = p AND bin_id = b
		UNION
		SELECT dep_pkg_id, dep_bin_id,
		COALESCE(t2.dep_name, t1.dep_name) FROM
		analysis AS t1 INNER JOIN binary_linking AS t2
		ON  t1.pkg_id = t2.pkg_id
		AND t1.bin_id = t2.bin_id
	) INSERT INTO dep
		SELECT t1.pkg_id, t1.bin_id, t1.dep_name FROM
		analysis AS t1 INNER JOIN binary_list AS t2
		ON  t1.pkg_id = t2.pkg_id
		AND t1.bin_id = t2.bin_id
		AND t2.type = 'lib'
		AND t1.dep_name IS NOT NULL;

	FOR p1, b1 IN (
		VALUES (p, b)
		UNION
		SELECT pkg_id, bin_id FROM dep
	) LOOP
		FOR d IN (
			SELECT dependency FROM binary_dependency WHERE
			pkg_id = p1 AND bin_id = b1
			AND NOT EXISTS (
				SELECT * FROM dep WHERE dep_name = dependency
			)
		) LOOP
			unresolved := concat(unresolved, ' ', d);
		END LOOP;
	END LOOP;

	FOR r in (SELECT DISTINCT p, b, * FROM dep) LOOP
		RETURN NEXT r;
	END LOOP;

	TRUNCATE TABLE dep;

	IF unresolved != '' THEN
		RAISE EXCEPTION '% in package % dependency not resolved: %', b, p, unresolved;
	END IF;

	RETURN;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_interp(p INT, b INT)
RETURNS SETOF binary_linking AS $$
DECLARE
	p1 INT;
	b1 INT;
	r binary_linking%ROWTYPE;

BEGIN
	FOR p1, b1 IN (
		SELECT DISTINCT * FROM binary_interp WHERE pkg_id = p AND bin_id = b
	) LOOP
		FOR r IN (
			SELECT DISTINCT * FROM get_link(p1, b1)
		) LOOP
			RETURN NEXT r;
		END LOOP;
	END LOOP;
	RETURN;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_depends(p INT, b INT)
RETURNS SETOF binary_linking AS $$
DECLARE
	p1 INT;
	b1 INT;
	d VARCHAR := '';
	unresolved VARCHAR;
	r binary_linking%ROWTYPE;

BEGIN
	CREATE TEMP TABLE IF NOT EXISTS dep (
		pkg_id INT NOT NULL, bin_id INT NOT NULL,
		dep_name VARCHAR NOT NULL,
		PRIMARY KEY (pkg_id, bin_id));
	WITH RECURSIVE
	analysis (pkg_id, bin_id)
	AS (
		SELECT pkg_id, bin_id, dep_name FROM
		binary_linking
		WHERE dep_pkg_id = p AND dep_bin_id = b
		UNION
		SELECT t2.pkg_id, t2.bin_id,
		COALESCE(t1.dep_name, t2.dep_name) FROM
		analysis AS t1 INNER JOIN binary_linking AS t2
		ON  t1.pkg_id = t2.dep_pkg_id
		AND t1.bin_id = t2.dep_bin_id
	) INSERT INTO dep
		SELECT t1.pkg_id, t1.bin_id, t1.dep_name FROM
		analysis AS t1 INNER JOIN binary_list AS t2
		ON  t1.pkg_id = t2.pkg_id
		AND t1.bin_id = t2.bin_id
		AND (t2.type = 'lib' OR t2.type = 'exe')
		AND t1.dep_name IS NOT NULL;

	FOR r in (SELECT DISTINCT pkg_id, bin_id, p, b, dep_name FROM dep) LOOP
		RETURN NEXT r;
	END LOOP;

	TRUNCATE TABLE dep;

	RETURN;
END
$$ LANGUAGE plpgsql;


