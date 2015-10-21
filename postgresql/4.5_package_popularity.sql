DO $$
DECLARE
	total INT := inst FROM package_popularity WHERE package_name = 'Total';
BEGIN

IF table_exists('package_inst') THEN
	DROP TABLE package_inst;
END IF;

CREATE TABLE package_inst AS
SELECT id AS pkg_id, log(total/(total-inst)::float) AS inst
FROM package_popularity AS T1 JOIN package_id AS T2
ON T1.package_name = T2.package_name;

IF table_exists('package_vote') THEN
	DROP TABLE package_vote;
END IF;

CREATE TABLE package_vote AS
SELECT id AS pkg_id, log(total/(total-vote)::float) AS vote
FROM package_popularity AS T1 JOIN package_id AS T2
ON T1.package_name = T2.package_name;

END $$ LANGUAGE plpgsql;
