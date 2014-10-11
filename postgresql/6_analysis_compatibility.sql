CREATE OR REPLACE FUNCTION analysis_compatibility(
	support_syscalls SMALLINT[]
)
RETURNS FLOAT AS $$

DECLARE
	compat FLOAT;
	total_compat FLOAT;

BEGIN
	compat := (
		SELECT sum(popularity) FROM package_syscall_array AS t
		WHERE t.syscalls <@ support_syscalls
	);
	
	total_compat := (
		SELECT sum(popularity) FROM package_syscall_array
	);

	RAISE NOTICE '% %', compat, total_compat;

	RETURN compat / total_compat;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analysis_syscall_compatibility()
RETURNS SETOF FLOAT AS $$

DECLARE
	syscalls SMALLINT[];
	s SMALLINT;

BEGIN
	FOR s IN (
		SELECT syscall FROM syscall_popularity
		ORDER BY popularity_with_libc DESC
	) LOOP
		RAISE NOTICE 'analyze %', s;
		syscalls := syscalls || s;
		RETURN NEXT (
			SELECT analysis_compatibility(syscalls)
		);
	END LOOP;
	RETURN;
END
$$ LANGUAGE plpgsql;
