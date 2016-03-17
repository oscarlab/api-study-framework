CREATE OR REPLACE FUNCTION analysis_syscall_compatibility(
	support_syscalls SMALLINT[]
)
RETURNS FLOAT AS $$

DECLARE
	compat FLOAT;
	total_compat FLOAT;

BEGIN
	compat := (
		SELECT sum(get_pop(t2.inst)) FROM package_syscall_array AS t1
		JOIN package_inst AS t2 ON t1.pkg_id = t2.pkg_id
		WHERE t1.syscalls <@ support_syscalls
	);
	
	total_compat := (
		SELECT sum(get_pop(t2.inst)) FROM package_syscall_array AS t1
		JOIN package_inst AS t2 ON t1.pkg_id = t2.pkg_id
	);

	compat := (SELECT COALESCE(MAX(compat), 0));

	RAISE NOTICE '%', compat / total_compat;

	RETURN compat / total_compat;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analysis_syscall_progress()
RETURNS SETOF FLOAT AS $$

DECLARE
	syscalls SMALLINT[];
	s SMALLINT;

BEGIN
	FOR s IN (
		SELECT syscall FROM syscall_popularity
		ORDER BY popularity_with_libc DESC
	) LOOP
		syscalls := syscalls || s;
		RAISE NOTICE 'analyze % (%)', s, array_length(syscalls, 1);
		RETURN NEXT (
			SELECT analysis_syscall_compatibility(syscalls)
		);
	END LOOP;
	RETURN;
END
$$ LANGUAGE plpgsql;
