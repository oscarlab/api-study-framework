DO $$
BEGIN
IF NOT table_exists('system_compatibility') THEN
	CREATE TABLE system_compatibility (
		target_name VARCHAR NOT NULL,
		syscalls VARCHAR[] NOT NULL,
		compatibility FLOAT,
		PRIMARY KEY(target_name)
	);
END IF;

IF NOT table_exists('library_compatibility') THEN
	CREATE TABLE library_compatibility (
		target_name VARCHAR NOT NULL,
		lib INT NOT NULL,
		calls VARCHAR[] NOT NULL,
		compatibility FLOAT,
		PRIMARY KEY(target_name, lib)
	);
END IF;
END $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION evaluate_system_compatibility(name VARCHAR)
RETURNS FLOAT AS $$

DECLARE
	syscalls SMALLINT[];

BEGIN
	syscalls := (
		SELECT array_agg(t2.number)
		FROM
		(SELECT unnest(system_compatibility.syscalls) as syscall
		FROM system_compatibility
		WHERE target_name = name) AS t1
		JOIN syscall AS t2
		ON t1.syscall = t2.name
	);

	RAISE NOTICE 'syscalls (%): %', array_length(syscalls, 1), syscalls;

	RETURN analysis_syscall_compatibility(syscalls);
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analysis_syscall_improvement(name VARCHAR)
RETURNS SETOF FLOAT AS $$

DECLARE
	syscalls SMALLINT[];
	s SMALLINT;

BEGIN
	syscalls := (
		SELECT array_agg(t2.number)
		FROM
		(SELECT unnest(system_compatibility.syscalls) as syscall
		FROM system_compatibility
		WHERE target_name = name) AS t1
		JOIN syscall AS t2
		ON t1.syscall = t2.name
	);

	RAISE NOTICE 'syscalls (%): %', array_length(syscalls, 1), syscalls;

	FOR s IN (
		SELECT t.syscall FROM syscall_popularity AS t
		WHERE NOT EXISTS (
		SELECT t2.number
		FROM
		(SELECT unnest(system_compatibility.syscalls) as syscall
		FROM system_compatibility
		WHERE target_name = name) AS t1
		JOIN syscall AS t2
		ON t1.syscall = t2.name
		WHERE t2.number = t.syscall)
		ORDER BY popularity_with_libc DESC
	) LOOP
		syscalls := syscalls || s;
		RAISE NOTICE 'analyze % (%)', get_syscall(s), array_length(syscalls, 1);
		RETURN NEXT (
			SELECT analysis_syscall_compatibility(syscalls)
		);
	END LOOP;
	RETURN;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION evaluate_libc_compatibility(name VARCHAR)
RETURNS FLOAT AS $$

DECLARE
	l INT;
	calls VARCHAR[];

BEGIN
	l := (SELECT lib FROM library_compatibility WHERE target_name = name);

	calls := (
		SELECT library_compatibility.calls
		FROM library_compatibility
		WHERE target_name = name
	);

	RAISE NOTICE 'calls: % in total', array_length(calls, 1);

	RETURN analysis_call_compatibility(l, calls);
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION evaluate_libc_compatibility_filtered(name VARCHAR)
RETURNS FLOAT AS $$

DECLARE
	l INT;
	calls VARCHAR[];

BEGIN
	l := (SELECT lib FROM library_compatibility WHERE target_name = name);

	calls := (
		SELECT filter_calls(library_compatibility.calls)
		FROM library_compatibility
		WHERE target_name = name
	);

	RAISE NOTICE 'calls: % in total', array_length(calls, 1);

	RETURN analysis_call_compatibility_filtered(l, calls);
END
$$ LANGUAGE plpgsql;
