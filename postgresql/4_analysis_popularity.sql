CREATE OR REPLACE FUNCTION analysis_popularity(s INT)
RETURNS FLOAT AS $$

DECLARE
	total INT;
	cnt INT;

BEGIN
	total := COUNT(DISTINCT bin_id) FROM analysis_footprint;
	cnt := COUNT(*) FROM analysis_footprint WHERE syscall = s;

	RETURN 100.0 * cnt / total;
END
$$ LANGUAGE plpgsql;
