DO $$
BEGIN
IF NOT table_exists('library_compatibility') THEN
	CREATE TABLE library_compatibility (
		target_name VARCHAR NOT NULL,
		lib INT NOT NULL,
		calls VARCHAR[] NOT NULL,
		compatibility FLOAT,
		PRIMARY KEY(target_name, lib)
	);
END IF;

IF NOT table_exists('system_compatibility') THEN
	CREATE TABLE system_compatibility (
		target_name VARCHAR NOT NULL,
		syscalls SMALLINT[] NOT NULL,
		compatibility FLOAT,
		PRIMARY KEY(target_name)
	);
END IF;
END $$ LANGUAGE plpgsql;
