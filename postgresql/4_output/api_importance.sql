CREATE OR REPLACE VIEW linux_syscalls_api_importance AS
	SELECT t2.id AS syscall_number,
	t2.name AS syscall_name,
	get_api_importance(COALESCE(t1.api_importance_order, 0.0::FLOAT)) AS api_importance,
	COALESCE(t1.api_importance_order, 0.0::FLOAT) AS api_importance_order
	FROM api_importance AS t1
	RIGHT JOIN
	api_list AS t2
	ON t1.api_type = t2.type AND t1.api_id = t2.id
	WHERE t2.type = 1
	ORDER BY api_importance_order DESC;

CREATE OR REPLACE VIEW linux_fcntl_opcodes_api_importance AS
	SELECT t2.id AS opcode,
	t2.name AS opcode_name,
	get_api_importance(COALESCE(t1.api_importance_order, 0.0::FLOAT)) AS api_importance,
	COALESCE(t1.api_importance_order, 0.0::FLOAT) AS api_importance_order
	FROM api_importance AS t1
	RIGHT JOIN
	api_list AS t2
	ON t1.api_type = t2.type AND t1.api_id = t2.id
	WHERE t2.type = 2
	ORDER BY api_importance_order DESC;

CREATE OR REPLACE VIEW linux_ioctl_opcodes_api_importance AS
	SELECT t2.id AS opcode,
	t2.name AS opcode_name,
	get_api_importance(COALESCE(t1.api_importance_order, 0.0::FLOAT)) AS api_importance,
	COALESCE(t1.api_importance_order, 0.0::FLOAT) AS api_importance_order
	FROM api_importance AS t1
	RIGHT JOIN
	api_list AS t2
	ON t1.api_type = t2.type AND t1.api_id = t2.id
	WHERE t2.type = 3
	ORDER BY api_importance_order DESC;

CREATE OR REPLACE VIEW linux_prctl_opcodes_api_importance AS
	SELECT t2.id AS opcode,
	t2.name AS opcode_name,
	get_api_importance(COALESCE(t1.api_importance_order, 0.0::FLOAT)) AS api_importance,
	COALESCE(t1.api_importance_order, 0.0::FLOAT) AS api_importance_order
	FROM api_importance AS t1
	RIGHT JOIN
	api_list AS t2
	ON t1.api_type = t2.type AND t1.api_id = t2.id
	WHERE t2.type = 4
	ORDER BY api_importance_order DESC;

CREATE OR REPLACE VIEW linux_pseudo_files_api_importance AS
	SELECT t2.name AS file_name,
	get_api_importance(COALESCE(t1.api_importance_order, 0.0::FLOAT)) AS api_importance,
	COALESCE(t1.api_importance_order, 0.0::FLOAT) AS api_importance_order
	FROM api_importance AS t1
	RIGHT JOIN
	api_list AS t2
	ON t1.api_type = t2.type AND t1.api_id = t2.id
	WHERE t2.type = 5
	ORDER BY api_importance_order DESC;

CREATE OR REPLACE VIEW libc_functions_api_importance AS
	SELECT t2.name AS symbol_name,
	get_api_importance(COALESCE(t1.api_importance_order, 0.0::FLOAT)) AS api_importance,
	COALESCE(t1.api_importance_order, 0.0::FLOAT) AS api_importance_order
	FROM api_importance AS t1
	RIGHT JOIN
	api_list AS t2
	ON t1.api_type = t2.type AND t1.api_id = t2.id
	WHERE t2.type = 6
	ORDER BY api_importance_order DESC;
