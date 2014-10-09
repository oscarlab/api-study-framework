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
