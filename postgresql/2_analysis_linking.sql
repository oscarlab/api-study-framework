CREATE TABLE IF NOT EXISTS analysis_linking (
	bin_id INT NOT NULL,
	dep_id INT NOT NULL,
	dep_name VARCHAR NOT NULL,
	PRIMARY KEY (bin_id, dep_id));

CREATE OR REPLACE FUNCTION analysis_linking()
RETURNS void AS $$

DECLARE
	b INT;
	d VARCHAR;
	resolved BOOLEAN;

BEGIN
	CREATE TEMP TABLE IF NOT EXISTS bin_id (
		bin_id INT NOT NULL PRIMARY KEY);
	INSERT INTO bin_id
		SELECT id AS bin_id FROM binary_id
		WHERE linking_generated = False;
	INSERT INTO bin_id
		SELECT t1.bin_id FROM
		analysis_linking AS t1 INNER JOIN bin_id AS t2
		ON t1.dep_id = t2.bin_id AND
		NOT EXISTS (
			SELECT * FROM bin_id WHERE bin_id = t1.bin_id
		);

	CREATE TEMP TABLE IF NOT EXISTS bin_dep (
		bin_id INT NOT NULL,
		dependency VARCHAR NOT NULL,
		PRIMARY KEY (bin_id, dependency));
	INSERT INTO bin_dep
		SELECT DISTINCT bin_id, dependency FROM binary_dependency AS t
		WHERE EXISTS (
			SELECT * FROM bin_id WHERE bin_id = t.bin_id
		);

	CREATE TEMP TABLE IF NOT EXISTS bin_dep_id (
		bin_id INT NOT NULL,
		dep_id INT NOT NULL,
		dep_name VARCHAR NOT NULL,
		PRIMARY KEY (bin_id, dep_id));
	INSERT INTO bin_dep_id
		SELECT DISTINCT t1.bin_id, t2.id, t2.file_name FROM
		bin_dep AS t1 INNER JOIN binary_id AS t2
		ON t1.dependency = t2.file_name
		UNION
		SELECT DISTINCT t3.link_id, t3.target_id, t4.file_name FROM
		binary_link AS t3
		INNER JOIN
		binary_id AS t4
		ON t3.target_id = t4.id AND
		EXISTS (
			SELECT * FROM bin_id WHERE bin_id = t3.link_id
		);

	DELETE FROM analysis_linking AS t WHERE EXISTS (
		SELECT * FROM bin_id WHERE bin_id = t.bin_id
	);

	WITH RECURSIVE
	analysis(bin_id, dep_id, dep_name)
	AS (
		SELECT * FROM bin_dep_id
		UNION
		SELECT t1.bin_id, t2.dep_id, t2.dep_name FROM
		analysis AS t1 INNER JOIN (
			SELECT * FROM bin_dep_id
			UNION
			SELECT * FROM analysis_linking
		) AS t2
		ON t1.dep_id = t2.bin_id
	) INSERT INTO analysis_linking SELECT * FROM analysis;

	FOR b in (SELECT * FROM bin_id) LOOP
		resolved := True;

		FOR d IN (
			SELECT dependency FROM binary_dependency
			WHERE bin_id = b
		) LOOP
			IF NOT EXISTS (
				SELECT * FROM analysis_linking
				WHERE bin_id = b AND dep_name = d
			) THEN
				resolved := False;
				RAISE NOTICE 'dependency not resolved for %: %', b, d;
			END IF;
		END LOOP;

		UPDATE binary_id SET
			linking_generated = resolved, footprint_generated = False
			WHERE id = b;
	END LOOP;

	TRUNCATE TABLE bin_id;
	TRUNCATE TABLE bin_dep;
	TRUNCATE TABLE bin_dep_id;

	RAISE NOTICE 'linking generated';
END
$$ LANGUAGE plpgsql;
