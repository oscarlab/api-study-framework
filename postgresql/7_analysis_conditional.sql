DO $$
BEGIN
IF NOT table_exists('syscall_join_popularity') THEN
	CREATE TABLE syscall_join_popularity (
		syscall1 SMALLINT NOT NULL,
		syscall2 SMALLINT NOT NULL,
		popularity FLOAT,
		PRIMARY KEY (syscall1, syscall2)
	);
END IF;
END $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analysis_syscall_join_popularity()
RETURNS void AS $$

DECLARE
	total INT := (SELECT COUNT(DISTINCT pkg_id) FROM package_syscall);
	count INT := 1;
	p INT;
	s1 SMALLINT;
	s2 SMALLINT;
	x FLOAT;

BEGIN
	CREATE TEMP TABLE IF NOT EXISTS syscall_join_tmp (
		syscall1 SMALLINT NOT NULL,
		syscall2 SMALLINT NOT NULL,
		popularity FLOAT,
		PRIMARY KEY (syscall1, syscall2));

	CREATE TEMP TABLE IF NOT EXISTS pkg_syscall_tmp2 (
		syscall SMALLINT NOT NULL,
		PRIMARY KEY (syscall));
	CREATE TEMP TABLE IF NOT EXISTS pkg_syscall_join_tmp (
		syscall1 SMALLINT NOT NULL,
		syscall2 SMALLINT NOT NULL,
		PRIMARY KEY (syscall1, syscall2));

	FOR p IN (SELECT DISTINCT pkg_id FROM package_syscall) LOOP

		RAISE NOTICE 'analyze package %/%', count, total;
		count := count + 1;

		INSERT INTO pkg_syscall_tmp2
			SELECT syscall
			FROM package_syscall
			WHERE pkg_id = p AND NOT by_libc;

		INSERT INTO pkg_syscall_join_tmp
			SELECT t1.syscall, t2.syscall
			FROM pkg_syscall_tmp2 AS t1 JOIN pkg_syscall_tmp2 AS t2
			ON t1.syscall < t2.syscall;

		x := (SELECT inst FROM package_inst WHERE pkg_id = p);

		FOR s1, s2 IN (SELECT * FROM pkg_syscall_join_tmp) LOOP
			IF EXISTS (
				SELECT * FROM syscall_join_tmp WHERE
				syscall1 = s1 AND syscall2 = s2
			) THEN
				UPDATE syscall_join_tmp
				SET popularity = popularity + x
				WHERE syscall1 = s1 AND syscall2 = s2;
			ELSE
				INSERT INTO syscall_join_tmp VALUES (s1, s2, x);
			END IF;
		END LOOP;

		TRUNCATE TABLE pkg_syscall_tmp2;
		TRUNCATE TABLE pkg_syscall_join_tmp;
	END LOOP;

	TRUNCATE TABLE syscall_join_popularity;
	INSERT INTO syscall_join_popularity
		SELECT syscall1, syscall2, popularity
		FROM syscall_join_tmp
		ORDER BY popularity DESC, syscall1, syscall2;

	TRUNCATE TABLE syscall_join_tmp;
END
$$ LANGUAGE plpgsql;
