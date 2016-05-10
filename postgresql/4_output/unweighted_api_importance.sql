CREATE OR REPLACE VIEW package_count AS
	SELECT count(DISTINCT pkg_id) AS count
	FROM binary_list
	WHERE type = 'exe';

CREATE OR REPLACE VIEW linux_syscalls_unweighted_api_importance AS
	SELECT t2.id AS syscall_number,
	t2.name AS syscall_name,
	COALESCE(t1.unweighted_importance, 0.0::FLOAT) AS unweighted_importance
	FROM (
		SELECT api_id,
		count(pkg_id)::FLOAT / (SELECT count FROM package_count)::FLOAT AS unweighted_importance
		FROM package_api_usage
		WHERE api_type = 1
		GROUP BY api_id
		ORDER BY unweighted_importance DESC
	) AS t1
	RIGHT JOIN
	api_list AS t2
	ON t1.api_id = t2.id
	WHERE t2.type = 1
	ORDER BY unweighted_importance DESC;

CREATE OR REPLACE VIEW linux_fcntl_opcodes_unweighted_api_importance AS
	SELECT t2.id AS opcode,
	t2.name AS opcode_name,
	COALESCE(t1.unweighted_importance, 0.0::FLOAT) AS unweighted_importance
	FROM (
		SELECT api_id,
		count(pkg_id)::FLOAT / (SELECT count FROM package_count)::FLOAT AS unweighted_importance
		FROM package_api_usage
		WHERE api_type = 2
		GROUP BY api_id
		ORDER BY unweighted_importance DESC
	) AS t1
	RIGHT JOIN
	api_list AS t2
	ON t1.api_id = t2.id
	WHERE t2.type = 2
	ORDER BY unweighted_importance DESC;

CREATE OR REPLACE VIEW linux_ioctl_opcodes_unweighted_api_importance AS
	SELECT t2.id AS opcode,
	t2.name AS opcode_name,
	COALESCE(t1.unweighted_importance, 0.0::FLOAT) AS unweighted_importance
	FROM (
		SELECT api_id,
		count(pkg_id)::FLOAT / (SELECT count FROM package_count)::FLOAT AS unweighted_importance
		FROM package_api_usage
		WHERE api_type = 3
		GROUP BY api_id
		ORDER BY unweighted_importance DESC
	) AS t1
	RIGHT JOIN
	api_list AS t2
	ON t1.api_id = t2.id
	WHERE t2.type = 3
	ORDER BY unweighted_importance DESC;

CREATE OR REPLACE VIEW linux_prctl_opcodes_unweighted_api_importance AS
	SELECT t2.id AS opcode,
	t2.name AS opcode_name,
	COALESCE(t1.unweighted_importance, 0.0::FLOAT) AS unweighted_importance
	FROM (
		SELECT api_id,
		count(pkg_id)::FLOAT / (SELECT count FROM package_count)::FLOAT AS unweighted_importance
		FROM package_api_usage
		WHERE api_type = 4
		GROUP BY api_id
		ORDER BY unweighted_importance DESC
	) AS t1
	RIGHT JOIN
	api_list AS t2
	ON t1.api_id = t2.id
	WHERE t2.type = 4
	ORDER BY unweighted_importance DESC;

CREATE OR REPLACE VIEW linux_pseudo_files_unweighted_api_importance AS
	SELECT t2.name AS file_name,
	COALESCE(t1.unweighted_importance, 0.0::FLOAT) AS unweighted_importance
	FROM (
		SELECT api_id,
		count(pkg_id)::FLOAT / (SELECT count FROM package_count)::FLOAT AS unweighted_importance
		FROM package_api_usage
		WHERE api_type = 5
		GROUP BY api_id
		ORDER BY unweighted_importance DESC
	) AS t1
	RIGHT JOIN
	api_list AS t2
	ON t1.api_id = t2.id
	WHERE t2.type = 5
	ORDER BY unweighted_importance DESC;

CREATE OR REPLACE VIEW libc_functions_unweighted_api_importance AS
	SELECT t2.name AS symbol_name,
	COALESCE(t1.unweighted_importance, 0.0::FLOAT) AS unweighted_importance
	FROM (
		SELECT api_id,
		count(pkg_id)::FLOAT / (SELECT count FROM package_count)::FLOAT AS unweighted_importance
		FROM package_api_usage
		WHERE api_type = 6
		GROUP BY api_id
		ORDER BY unweighted_importance DESC
	) AS t1
	RIGHT JOIN
	api_list AS t2
	ON t1.api_id = t2.id
	WHERE t2.type = 6
	ORDER BY unweighted_importance DESC;
