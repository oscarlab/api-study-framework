DO $$
BEGIN
IF NOT table_exists('binary_linking') THEN
	CREATE TABLE binary_linking (
		pkg_id INT NOT NULL, bin_id INT NOT NULL,
		dep_id INT NOT NULL,
		dep_name VARCHAR NOT NULL,
		by_link BOOLEAN NOT NULL,
		PRIMARY KEY (pkg_id, bin_id, dep_id)
	);
	CREATE INDEX binary_linking_pkg_id_bin_id_idx
		ON binary_linking (pkg_id, bin_id);
	CREATE INDEX binary_linking_bin_id_idx
		ON binary_linking (bin_id);
	CREATE INDEX binary_linking_dep_id_idx
		ON binary_linking (dep_id);
	CREATE INDEX binary_linking_dep_name_idx
		ON binary_linking (dep_name);
END IF;
END $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analysis_linking()
RETURNS void AS $$

DECLARE
	p INT;
	b INT;
	d VARCHAR;
	resolved BOOLEAN;

BEGIN
	CREATE TEMP TABLE IF NOT EXISTS bin_id (
		pkg_id INT NOT NULL,
		bin_id INT NOT NULL,
		PRIMARY KEY (pkg_id, bin_id));
	INSERT INTO bin_id
		SELECT pkg_id, bin_id FROM binary_list WHERE linking = False
		UNION
		SELECT pkg_id, lnk_id FROM binary_link WHERE linking = False;
	INSERT INTO bin_id
		SELECT DISTINCT t1.pkg_id, t1.bin_id FROM
		binary_linking AS t1 INNER JOIN bin_id AS t2
		ON t1.dep_id = t2.bin_id AND
		NOT EXISTS (
			SELECT * FROM bin_id WHERE
			pkg_id = t1.pkg_id AND bin_id = t1.bin_id
		);

	IF NOT table_exists('bin_dep') THEN
		CREATE TEMP TABLE bin_dep (
			pkg_id INT NOT NULL,
			bin_id INT NOT NULL,
			dep_id INT NOT NULL,
			dep_name VARCHAR NOT NULL,
			by_link BOOLEAN NOT NULL,
			PRIMARY KEY (pkg_id, bin_id, dep_id));
		create index bin_dep_pkg_id_idx on bin_dep(pkg_id);
		create index bin_dep_bin_id_idx on bin_dep(bin_id);
		create index bin_dep_dep_id_idx on bin_dep(dep_id);
		create index bin_dep_name_idx on bin_dep (dep_name);
	END IF;

	FOR p, b in (SELECT * FROM bin_id) LOOP
		RAISE NOTICE 'update linking: % in package %', b, p;

		INSERT INTO bin_dep
			SELECT p, b, t2.id, t1.dependency, False FROM (
				SELECT dependency FROM binary_dependency
				WHERE pkg_id = p AND bin_id = b
			) AS t1
			INNER JOIN
			binary_id AS t2
			ON t1.dependency = t2.file_name
			UNION
			SELECT p, b, t3.id, t4.file_name, t3.by_link FROM (
				SELECT interp AS id, False AS by_link
				FROM binary_interp
				WHERE pkg_id = p AND bin_id = b
				UNION
				SELECT target AS id, True  AS by_link
				FROM binary_link
				WHERE pkg_id = p AND lnk_id = b
			) AS t3
			INNER JOIN
			binary_id AS t4
			ON t3.id = t4.id;

		DELETE FROM binary_linking WHERE pkg_id = p AND bin_id = b;
	END LOOP;

	WITH RECURSIVE
	analysis(pkg_id, bin_id, dep_id, dep_name, by_link)
	AS (
		SELECT * FROM bin_dep
		UNION
		SELECT
		t1.pkg_id, t1.bin_id, t2.dep_id, t2.dep_name,
		t1.by_link AND t2.by_link
		FROM
		analysis AS t1 INNER JOIN (
			SELECT * FROM bin_dep
			UNION
			SELECT * FROM binary_linking
		) AS t2
		ON t1.dep_id = t2.bin_id
	) INSERT INTO binary_linking SELECT * FROM analysis;

	FOR p, b in (SELECT * FROM bin_id) LOOP
		resolved := True;

		FOR d IN (
			SELECT dependency FROM
			binary_dependency
			WHERE pkg_id = p AND bin_id = b
		) LOOP
			IF NOT EXISTS (
				SELECT * FROM binary_linking
				WHERE pkg_id = p AND bin_id = b AND dep_name = d
			) THEN
				resolved := False;
				RAISE NOTICE 'dependency not resolved for binary % in package %: %', b, p, d;
			END IF;
		END LOOP;

		UPDATE binary_list SET linking = resolved
		WHERE pkg_id = p AND bin_id = b;
		UPDATE binary_link SET linking = resolved
		WHERE pkg_id = p AND lnk_id = b;
	END LOOP;

	TRUNCATE TABLE bin_id;
	TRUNCATE TABLE bin_dep;

	RAISE NOTICE 'linking generated';
END
$$ LANGUAGE plpgsql;
