# This file creates custom IPython magics for querying WMF databases.
# For more details, see http://ipython.readthedocs.io/en/stable/config/custommagics.html

import pandas as pd
import pymysql
from impala.dbapi import connect as impala_conn
from impala.util import as_pandas
from IPython.core.magic import register_cell_magic

# Strings are stored in MariaDB as BINARY rather than CHAR/VARCHAR, so they need to be converted.
def try_decode(cell):
    try:
        return cell.decode(encoding = "utf-8")
    except AttributeError:
        return cell

def decode_data(d):
    return [{try_decode(key): try_decode(val) for key, val in item.items()} for item in d]

# To-do: figure out how to use the `fmt` parameter when calling a magic
@register_cell_magic
def run_mariadb(line, cell, fmt = "pandas"):
    """Used to run an SQL query or command on the `analytics-store` MariaDB replica."""
    cmd = cell

    if fmt not in ["pandas", "raw"]:
        raise ValueError("The format should be either `pandas` or `raw`.")

    try:
        conn = pymysql.connect(
            host = "analytics-store.eqiad.wmnet",
            read_default_file = '/etc/mysql/conf.d/research-client.cnf',
            charset = 'utf8mb4',
            db='staging',
            cursorclass=pymysql.cursors.DictCursor,
            autocommit = True
        )
        if fmt == "pandas":
            result = pd.read_sql_query(cmd, conn)
            # Turn any binary data into strings
            result = result.applymap(try_decode)
        elif fmt == "raw":
            cursor = conn.cursor()
            cursor.execute(query)
            result = cursor.fetchall()
            result = decode_data(result)
        return result

    finally:
        conn.close()
            

# To-do: figure out how to use the `fmt` parameter when calling a magic
@register_cell_magic
def run_hive(line, cell, fmt = "pandas"):
    """Used to run a Hive query or command on the Data Lake stored on the Analytics cluster."""
    cmd = cell
    
    if fmt not in ["pandas", "raw"]:
        raise ValueError("The format should be either `pandas` or `raw`.")
    
    try:
        hive_conn = impala_conn(host='analytics1003.eqiad.wmnet', port=10000, auth_mechanism='PLAIN')
        hive_cursor = hive_conn.cursor()
        hive_cursor.execute(cmd)
        if fmt == "pandas":
            try:
                result = as_pandas(hive_cursor)
            # Happens if there are no results (as with an INSERT INTO query)
            except TypeError:
                pass
        else:
            result = hive_cursor.fetchall()
        return result
    
    finally:
        hive_conn.close()
