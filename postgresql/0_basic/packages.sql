DO $$
BEGIN
IF NOT table_exists('package_install') THEN
	CREATE TABLE package_install (
		pkg_id INT,
		percent_order FLOAT,
		PRIMARY KEY(pkg_id)
	);
END IF;
END
$$ LANGUAGE plpgsql;

CREATE or REPLACE FUNCTION update_package_install()
RETURNS void AS $$
DECLARE
	total INT := (SELECT inst FROM package_popularity WHERE package_name = 'Total');
	last INT := (SELECT COALESCE(MAX(pkg_id), 0) FROM package_install);

BEGIN
	INSERT INTO package_install
		SELECT id, log(total / (total - inst)::FLOAT)
		FROM package_popularity AS t1 JOIN package_id AS t2
		ON t1.package_name = t2.package_name
		WHERE t2.id > last;
END
$$ LANGUAGE plpgsql;
