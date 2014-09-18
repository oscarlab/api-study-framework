DROP TABLE IF EXISTS binary_callgraph;
CREATE TABLE binary_callgraph (
    binary_name CHAR(80) NOT NULL,
    symbol_name CHAR(40) NOT NULL,
    target CHAR(40) NOT NULL,
    PRIMARY KEY (binary_name, symbol_name, target));

CREATE TEMP TABLE binary_name AS
    SELECT DISTINCT binary_name FROM binary_list
    WHERE type = 'lib';

CREATE OR REPLACE FUNCTION analysis_callgraph ()
RETURNS void AS $$
DECLARE
    total INT;
    cnt INT;
    b CHAR(80);

BEGIN
    FOR b IN (SELECT * FROM binary_name) LOOP
        CREATE TEMP TABLE single_binary_call AS
            SELECT DISTINCT func_name, target FROM binary_call
            WHERE binary_name = b AND target IS NOT NULL;

        CREATE TEMP TABLE single_binary_symbol AS
            SELECT DISTINCT symbol_name FROM binary_symbol
            WHERE binary_name = b;

        WITH RECURSIVE
        single_binary_callgraph (symbol_name, target)
        AS (
            SELECT t2.symbol_name, t1.target FROM
                single_binary_call AS t1
                INNER JOIN
                single_binary_symbol AS t2
                ON t1.func_name = t2.symbol_name
            UNION DISTINCT
            SELECT t4.symbol_name, t3.target FROM
                single_binary_call AS t3
                INNER JOIN
                single_binary_callgraph AS t4
                ON t3.func_name = t4.symbol_name
        )
        INSERT INTO binary_callgraph
            SELECT b, symbol_name, target FROM single_binary_callgraph;

        DROP TABLE single_binary_call;
        DROP TABLE single_binary_symbol;

        RAISE NOTICE '%', b;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

SELECT analysis_callgraph();
