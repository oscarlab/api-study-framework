CREATE OR REPLACE FUNCTION analysis_call_compatibility(
	lib INT,
	support_calls VARCHAR[]
)
RETURNS FLOAT AS $$

DECLARE
	compat FLOAT;
	total_compat FLOAT;

BEGIN
	compat := (
		SELECT sum(get_pop(t2.inst)) FROM package_call_array AS t1
		JOIN package_inst AS t2 ON t1.pkg_id = t2.pkg_id
		WHERE t1.dep_bin_id = lib AND t1.calls <@ support_calls
	);
	
	total_compat := (
		SELECT sum(get_pop(t2.inst)) FROM package_call_array AS t1
		JOIN package_inst AS t2 ON t1.pkg_id = t2.pkg_id
		WHERE t1.dep_bin_id = lib
	);

	compat := (SELECT COALESCE(MAX(compat), 0));

	RAISE NOTICE '%', compat / total_compat;

	RETURN compat / total_compat;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analysis_call_progress(lib INT)
RETURNS SETOF FLOAT AS $$

DECLARE
	calls VARCHAR[];
	c VARCHAR;

BEGIN
	FOR c IN (
		SELECT call FROM call_popularity
		WHERE bin_id = lib
		ORDER BY popularity DESC
	) LOOP
		calls := calls || c;
		RAISE NOTICE 'analyze % (%)', c, array_length(calls, 1);
		RETURN NEXT (
			SELECT analysis_call_compatibility(lib, calls)
		);
	END LOOP;
	RETURN;
END
$$ LANGUAGE plpgsql;
