CREATE TABLE IF NOT EXISTS analysis_dep (
bin_id INT NOT NULL, dep_id INT NOT NULL,
PRIMARY KEY (bin_id, dep_id));

CREATE TEMP TABLE bin_name AS
SELECT DISTINCT regexp_replace(binary_name, '^.+[/\\]', '') as name, id
FROM binary_id;

CREATE TEMP TABLE direct_bin_id AS
SELECT id AS bin_id FROM binary_id WHERE dep_generated = False;

CREATE TEMP TABLE bin_id AS
SELECT * FROM direct_bin_id
UNION
SELECT t1.bin_id FROM
analysis_dep AS t1 INNER JOIN direct_bin_id AS t2
ON t1.dep_id = t2.bin_id;

CREATE TEMP TABLE bin_dep AS
SELECT DISTINCT bin_id, dependency FROM binary_dependency AS t
WHERE EXISTS (
	SELECT * FROM bin_id WHERE bin_id = t.bin_id
);

CREATE TEMP TABLE bin_dep_id AS
SELECT t1.bin_id AS bin_id, t2.id AS dep_id FROM
bin_dep AS t1 INNER JOIN bin_name AS t2
ON t1.dependency = t2.name
UNION
SELECT link_id AS bin_id, target_id AS dep_id FROM binary_link AS t3
WHERE EXISTS (
	SELECT * FROM bin_id WHERE bin_id = t3.link_id
);

DELETE FROM analysis_dep AS t WHERE EXISTS (
	SELECT * FROM bin_id WHERE bin_id = t.bin_id
);

WITH RECURSIVE
analysis(bin_id, dep_id)
AS (
	SELECT * FROM bin_dep_id
	UNION
	SELECT t1.bin_id, t2.dep_id FROM
	analysis AS t1 INNER JOIN (
		SELECT * FROM bin_dep_id UNION SELECT * FROM analysis_dep
	) AS t2
	ON t1.dep_id = t2.bin_id
) INSERT INTO analysis_dep SELECT * FROM analysis;

UPDATE binary_id SET dep_generated = 'True', analysis_generated = 'False'
WHERE EXISTS (
	SELECT * FROM bin_id WHERE bin_id = id
);
