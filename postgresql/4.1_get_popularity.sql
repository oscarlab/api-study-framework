CREATE OR REPLACE FUNCTION get_pop(pop FLOAT)
RETURNS FLOAT AS $$
BEGIN
       IF pop > 6 THEN
               RETURN 1.0;
       ELSE
               RETURN 1.0 - 10.0 ^ (-pop);
       END IF;
END
$$ LANGUAGE plpgsql;
