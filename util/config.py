from configparser import ConfigParser
from typing import Optional, List, Dict, Any

def load_config(filename: Optional[str] ='config.ini', section: Optional[str] ='postgresql') -> dict:
    parser = ConfigParser()
    parser.read(filename)
    config = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            # asyncpg vuole 'database' invece di 'dbname' se usi parametri scompattati,
            # oppure passiamo direttamente la DSN string, ma per compatibilità mappiamo:
            key = 'database' if param[0] == 'dbname' else param[0]
            config[key] = param[1]
    else:
        raise Exception(f'Section {section} not found in the {filename} file')
    return config