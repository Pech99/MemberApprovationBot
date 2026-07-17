import psycopg2

from configparser import ConfigParser
from typing import Optional

# https://neon.tech/postgresql/postgresql-python/update

def load_config(filename='database.ini', section='postgresql'):
    parser = ConfigParser()
    parser.read(filename)
    # get section, default to postgresql
    config = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            config[param[0]] = param[1]
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))
    return config


def connect():
    """ Connect to the PostgreSQL database server """
    try:
        # connecting to the PostgreSQL server
        config = load_config()
        with psycopg2.connect(**config) as conn:
            print('Connected to the PostgreSQL server.')
            return conn
    except (psycopg2.DatabaseError, Exception) as error:
        print(error)
        exit()


def execute(sql, args: Optional[tuple] = None) -> list[dict]:
    try:
        with DB.cursor() as cur:
            if args:
                cur.execute(sql, args)
            else:
                cur.execute(sql)
            rows = cur.fetchall()

            result = []
            for row in rows:
                data = {}
                i = 0
                for cmp in row:
                    data[cur.description[i].name] = cmp
                    i += 1
                result.append(data)

            cur.close()
            DB.commit()
            return result

    except (Exception, psycopg2.DatabaseError) as error:
        DB.rollback()
        raise Exception(f"execute: errore sulla query {sql} args={args}\n{error}")


def perform(sql, args: Optional[tuple] = None) -> int:
    try:
        with DB.cursor() as cur:
            if args:
                cur.execute(sql, args)
            else:
                cur.execute(sql)
            result = cur.rowcount

            cur.close()
            DB.commit()
            if result:
                return result
            return -1
        
    except (Exception, psycopg2.DatabaseError) as error:
        DB.rollback()
        raise Exception(f"perform: errore sulla query {sql} args={args}\n{error}")

try:
    DB = connect()
    perform("SET search_path = MemberApprovationBot")
except (Exception, psycopg2.DatabaseError) as error:
    print(error)
    exit()
