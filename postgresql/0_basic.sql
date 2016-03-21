CREATE OR REPLACE FUNCTION table_exists(name VARCHAR)
RETURNS BOOLEAN AS $$
BEGIN
	IF EXISTS (
		SELECT relname FROM pg_class WHERE relname=name
	) THEN
		RETURN True;
	END IF;
	RETURN False;
END
$$ LANGUAGE plpgsql;

CREATE or REPLACE FUNCTION temp_table_exists(name VARCHAR)
RETURNS BOOLEAN AS $$
BEGIN
	/* check the table exist in database and is visible*/
	PERFORM n.nspname, c.relname
	FROM pg_catalog.pg_class c LEFT JOIN pg_catalog.pg_namespace n
	ON n.oid = c.relnamespace
	where n.nspname like 'pg_temp_%'
	AND pg_catalog.pg_table_is_visible(c.oid)
	AND Upper(relname) = Upper(name);

	IF FOUND THEN
		RETURN TRUE;
	ELSE
		RETURN FALSE;
	END IF;
END
$$ LANGUAGE plpgsql;

CREATE or REPLACE FUNCTION get_binary_name(b INT)
RETURNS VARCHAR AS $$
BEGIN
	RETURN (SELECT binary_name FROM binary_id WHERE id = b);
END
$$ LANGUAGE plpgsql;

CREATE or REPLACE FUNCTION get_package_name(p INT)
RETURNS VARCHAR AS $$
BEGIN
	RETURN (SELECT package_name FROM package_id WHERE id = p);
END
$$ LANGUAGE plpgsql;

CREATE or REPLACE FUNCTION get_syscall(s INT)
RETURNS VARCHAR AS $$
BEGIN
	RETURN (SELECT name FROM syscall WHERE number = s);
END
$$ LANGUAGE plpgsql;

CREATE or REPLACE FUNCTION get_syscall_no(n VARCHAR)
RETURNS VARCHAR AS $$
BEGIN
	RETURN (SELECT number FROM syscall WHERE name = n);
END
$$ LANGUAGE plpgsql;
