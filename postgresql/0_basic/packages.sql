DO $$
DECLARE
	total INT := inst FROM package_popularity WHERE package_name = 'Total';
BEGIN

IF NOT table_exists('package_install') THEN
	CREATE TABLE package_inst (pkg_id INT, percent_order FLOAT);
END IF;

CREATE or REPLACE FUNCTION update_package_install()
RETURNS void AS $$
DECLARE
	last INT := (SELECT MAX(id) FROM package_id);

BEGIN
	INSERT INTO package_install
		SELECT id, log(total / (total - inst)::FLOAT)
		FROM package_popularity AS t1 JOIN package_id AS t2
		ON t1.package_name = t2.package_name
		WHERE t2.id > last;
END
$$ LANGUAGE plpgsql;


END $$ LANGUAGE plpgsql;
