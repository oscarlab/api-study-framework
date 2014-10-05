DO $$
BEGIN
IF NOT table_exists('package_call') THEN
	CREATE TABLE package_call (
		pkg_id INT NOT NULL,
		dep_pkg_id INT NOT NULL,
		dep_bin_id INT NOT NULL,
		call INT NOT NULL,
		PRIMARY KEY(pkg_id, dep_pkg_id, dep_bin_id, call)
	);
	CREATE INDEX package_call_pkg_id_idx
		ON package_call (pkg_id);
	CREATE INDEX package_call_dep_pkg_id_dep_bin_id_idx
		ON package_call (dep_pkg_id, dep_bin_id);
	CREATE INDEX package_call_call_idx
		ON package_call (call);
END IF;

IF NOT table_exists('package_syscall') THEN
	CREATE TABLE package_syscall (
		pkg_id INT NOT NULL,
		syscall SMALLINT NOT NULL,
		PRIMARY KEY (pkg_id, syscall)
	);
	CREATE INDEX package_syscall_pkg_id_idx
		ON package_syscall (pkg_id);
END IF;

IF NOT table_exists('package_vecsyscall') THEN
	CREATE TABLE package_vecsyscall (
		pkg_id INT NOT NULL,
		syscall SMALLINT NOT NULL,
		request BIGINT NOT NULL,
		PRIMARY KEY (pkg_id, syscall, request)
	);
	CREATE INDEX package_vecsyscall_pkg_id_idx
		ON package_vecsyscall (pkg_id);
END IF;

IF NOT table_exists('package_fileaccess') THEN
	CREATE TABLE package_fileaccess (
		pkg_id INT NOT NULL,
		file VARCHAR NOT NULL,
		PRIMARY KEY (pkg_id, file)
	);
	CREATE INDEX package_fileaccess_pkg_id_idx
		ON package_fileaccess (pkg_id);
END IF;
END $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analysis_package(p INT)
RETURNS void AS $$

DECLARE
	b INT;

BEGIN
	RAISE NOTICE 'analyze package: %', p;

	CREATE TEMP TABLE IF NOT EXISTS pkg_bin (
		bin_id INT NOT NULL,
		callgraph BOOLEAN,
		PRIMARY KEY(bin_id));
	INSERT INTO pkg_bin
		SELECT DISTINCT bin_id, callgraph FROM binary_list
		WHERE pkg_id = p AND type = 'exe';

	IF NOT EXISTS (
		SELECT * FROM pkg_bin
	) THEN
		UPDATE package_id SET footprint = True WHERE id = p;
		RETURN;
	END IF;

	IF EXISTS (
		SELECT * FROM pkg_bin WHERE callgraph = False
	) THEN
		RAISE EXCEPTION 'binary not resolved: %', p;
	END IF;

	FOR b IN (SELECT bin_id FROM pkg_bin) LOOP
		RAISE NOTICE 'executable: %', b;
	END LOOP;

	DELETE FROM package_call WHERE pkg_id = p;
	INSERT INTO package_call
		SELECT DISTINCT p, t1.dep_pkg_id, t1.dep_bin_id, t1.call
		FROM executable_call AS t1
		INNER JOIN
		pkg_bin AS t2
		ON t1.pkg_id = p AND t1.bin_id = t2.bin_id;

	DELETE FROM package_syscall WHERE pkg_id = p;
	INSERT INTO package_syscall
		SELECT DISTINCT p, t1.syscall
		FROM executable_syscall AS t1
		INNER JOIN
		pkg_bin AS t2
		ON t1.pkg_id = p AND t1.bin_id = t2.bin_id;

	DELETE FROM package_vecsyscall WHERE pkg_id = p;
	INSERT INTO package_vecsyscall
		SELECT DISTINCT p, t1.syscall, t1.request
		FROM executable_vecsyscall AS t1
		INNER JOIN
		pkg_bin AS t2
		ON t1.pkg_id = p AND t1.bin_id = t2.bin_id;

	DELETE FROM package_fileaccess WHERE pkg_id = p;
	INSERT INTO package_fileaccess
		SELECT DISTINCT p, t1.file
		FROM executable_fileaccess AS t1
		INNER JOIN
		pkg_bin AS t2
		ON t1.pkg_id = p AND t1.bin_id = t2.bin_id;

	UPDATE package_id SET footprint = True WHERE id = p;

	TRUNCATE TABLE pkg_bin;

	RAISE NOTICE 'package %: footprint generated', p;
END
$$ LANGUAGE plpgsql;
