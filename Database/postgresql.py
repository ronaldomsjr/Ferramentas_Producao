# -*- coding: utf-8 -*-
import os, sys, psycopg2, base64, pickle, json, copy
from PyQt5 import QtCore


class Postgresql(QtCore.QObject):

    def __init__(self):
        super(Postgresql, self).__init__()
        self.conns = {}
        self.path_data = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data.pickle')

    def dump_data(self, data):
        with open(self.path_data, u"wb") as f:
            pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)

    def load_data(self):
        try:
            with open(self.path_data, u"rb") as f:
                return pickle.load(f)
        except FileNotFoundError:
            return False

    def get_local_alias_db(self):
        conf = QtCore.QSettings().allKeys()
        db_info = [
            s for s in conf 
            if u"PostgreSQL" == s.split("/")[0] and u"connections" == s.split("/")[1]
        ]
        alias_dbs = list(set([
            a.split("/")[-2] for a in db_info 
            if a.split("/")[-2] != u"connections"
        ]))
        return alias_dbs

    def set_connections_data(self, config_conn={}):
        if config_conn:
            self.conns[config_conn['db_name']] = config_conn
        else:
            aliases = self.get_local_alias_db()
            settings = QtCore.QSettings()
            path_conf = u"PostgreSQL/connections/{0}/{1}"
            for alias in aliases:
                if settings.value(path_conf.format(alias, u"database")):
                    self.conns[alias] = {
                        'db_name' : settings.value(path_conf.format(alias, u"database")),
                        'db_user' : settings.value(path_conf.format(alias, u"username")),
                        'db_host' : settings.value(path_conf.format(alias, u"host")),
                        'db_port' : settings.value(path_conf.format(alias, u"port")),
                        'db_password' : settings.value(path_conf.format(alias, u"password"))
                    }

    def get_dbs_name(self):
        return list(self.conns.keys())

    def get_workspaces_name(self, table_name):
        data = self.validate_table(table_name)
        if data:
            sql = u"""SELECT mi FROM {0}.{1};""".format(
                data['schema_name'],
                data['table_name']
            )
            result = self.run_sql(sql)
            return list(set([item[0] for item in result]))
        return []

    def get_styles(self, table_name):
        data = self.validate_table(table_name)
        if data:
            sql = u"""SELECT stylename, id 
                    FROM {0}.{1};""".format(
                        data['schema_name'],
                        data['table_name']
                    )
            result = self.run_sql(sql)
            return { name : i for name, i in result }
        return {}
    
    def get_rules(self, table_name):
        data = self.validate_table(table_name)
        if data:
            sql = u"""SELECT id, tipo_regra, camada, nome, 
            cor_rgb, regra, tipo_estilo, atributo, descricao, ordem
            FROM {0}.{1};""".format(
                data['schema_name'],
                data['table_name']
            )
            result = self.run_sql(sql)
            rules = {
                row[0] : {
                    u"tipo_regra" : row[1],
                    u"camada" : row[2],
                    u"nome" : row[3],
                    u"corRgb" : [
                        int(row[4].split(",")[0]),
                        int(row[4].split(",")[1]),
                        int(row[4].split(",")[2])
                    ],
                    u"cor_rgb" : row[4],
                    u"regra" : row[5],
                    u"tipo_estilo" : row[6],
                    u"atributo" : row[7],
                    u"descricao" : row[8],
                    u"ordem" : row[9] 
                } for row in result
            }
            return rules
        return {}
    
    def save_menu_profile(self, menu_data):
        table_name = menu_data['menu_table_name']
        schema_name = menu_data['menu_schema_name']
        data = self.validate_table(table_name)
        if not data:
            sql = u"""CREATE TABLE {0}.{1} (
                id SERIAL PRIMARY KEY,
                nome_do_perfil text NOT NULL,
                descricao text,
                perfil json NOT NULL,
                ordem_menu json NOT NULL
                ); GRANT ALL ON public.menu_profile TO public;""".format(
                schema_name, table_name
            )
            self.run_sql(sql)
        menu_name = menu_data['menu_name']
        menu_profile = menu_data['menu_profile']
        menu_order = menu_data['menu_order']
        sql = u"SELECT id FROM {0}.{1} WHERE nome_do_perfil = '{2}';".format(
            schema_name, 
            table_name,
            menu_name
        )
        result = self.run_sql(sql)
        if [item[0] for item in result]:
            sql = u"""UPDATE {0}.{1} 
                SET perfil = '{2}', ordem_menu = '{3}'
                WHERE nome_do_perfil = '{4}';""".format(
                    schema_name,
                    table_name,
                    json.dumps(menu_profile),
                    json.dumps(menu_order)
            )
            self.run_sql(sql)
        else:
            sql = u"""INSERT INTO {0}.{1} (
                nome_do_perfil, perfil, ordem_menu
                ) VALUES ('{2}', '{3}', '{4}');""".format(
                schema_name,
                table_name,
                menu_name, 
                menu_profile, 
                menu_order
            )
            self.run_sql(sql)

    def get_menu_profile(self, table_name):
        data = self.validate_table(table_name)
        if data:
            sql = u"""SELECT id, nome_do_perfil, perfil, ordem_menu
                FROM {0}.{1};""".format(
                    data['schema_name'],
                    data['table_name']
                )
            result = self.run_sql(sql)
            profiles = {
                row[0] : {
                    u"nome_do_perfil" : row[1],
                    u"perfil" : row[2],
                    u"orderMenu" : row[3]
                } for row in result
            }
            return profiles
    
    def get_db_json(self):
        db_name = self.current_db_name
        json_template = {
            u"db_name" : db_name,
            u"db_layers" : { 
                u"PONTO" : [],
                u"LINHA" : [],
                u"AREA" : []     
            },
            u"db_connection" : self.conns[db_name],
            u"db_workspaces_name" : self.get_workspaces_name(u"aux_moldura_a"),
            u"db_workspaces_wkt" : self.get_workspaces_wkt(u"aux_moldura_a"),
            u"db_menu" : self.get_menu_profile(u"menu_profile"),
            u"db_rules" : self.get_rules(u"layer_rules"),
            u"db_styles" : self.get_styles(u"layer_styles"),
            u"db_srid" : self.get_layer_srid(u"aux_moldura_a"),
        }
        return json_template

    def load_db_json(self, db_name, layers_name=[]):
        self.current_db_name = db_name
        conn = self.get_connection()
        self.pg_cursor = conn.cursor()
        db_json = self.get_db_json()
        layers_data = self.get_all_layers(layers_name)
        table_with_filter = self.get_tables_by_column('filter')
        for data in layers_data:
            lyr_name = data['layer_name']
            lyr_constraint = self.get_layer_contrains_codes(lyr_name)
            group_geom = self.get_group_geom(data['layer_geom_type'])
            if group_geom:
                lyr_schema = data['layer_schema']
                layer_all_data = copy.deepcopy(data)
                fields = self.get_layer_columns(lyr_name)
                domains = self.get_layer_domains(lyr_name)
                for field in list(set(list(domains.keys()) + fields)):
                    layer_all_data['layer_fields'][field] = {}
                    if ( 
                            table_with_filter 
                            and (field in domains) 
                            and (domains[field] in table_with_filter)
                        ):
                        table = self.get_table(domains[field])
                        layer_all_data['layer_fields']['filter'] = table
                    if field in domains:
                        layer_all_data['layer_fields'][field]['valueMap'] = self.get_fields_values(
                            field, 
                            domains, 
                            lyr_constraint
                        )
                layer_all_data['group_geom'] = group_geom
                group_class = self.get_group_class(lyr_name)
                group_class = group_class if group_class else lyr_schema
                layer_all_data['group_class'] = group_class
                db_json['db_layers'][group_geom].append(layer_all_data)
        self.dump_data( db_json )
        del self.current_db_name
        self.pg_cursor.close()
        return db_json
        
    def get_table(self, table_name):
        data = self.validate_table(table_name)
        sql = u"""SELECT * FROM {}.{};""".format(
            data['schema_name'], data['table_name']
        )
        result = self.run_sql(sql)
        return result

    def get_group_geom(self, layer_geom_type):
        if 'point' in layer_geom_type.lower():
            return u"PONTO"
        elif 'line' in layer_geom_type.lower():
            return u"LINHA"
        elif 'polygon' in layer_geom_type.lower():
            return u"AREA"

    def get_group_class(self, layer_name):
        r = layer_name.split('_')
        if len(r) > 1:
            return r[0]

    def get_all_layers(self, layers_name):
        if layers_name:
            list_names = ", ".join(["'%{}%'".format(name) for name in layers_name])
            sql = u"""SELECT f_table_schema, f_table_name, type 
                FROM geometry_columns 
                WHERE f_table_name LIKE any(array[{}]);""".format(
                list_names
            )
        else:
            sql = u"""SELECT f_table_schema, f_table_name, type 
                FROM geometry_columns;"""
        result = self.run_sql(sql)
        layers = [
            { 
                'layer_schema' : item[0],
                'layer_name' : item[1],
                'layer_geom_type' : item[2],
                'layer_fields' : {}
            } for item in result
        ]
        return layers

    def get_connection(self):
        conn = psycopg2.connect(
            u"dbname='{0}' user='{1}' host='{2}' port='{3}' password='{4}'".format(
                self.conns[self.current_db_name]['db_name'],
                self.conns[self.current_db_name]['db_user'],
                self.conns[self.current_db_name]['db_host'],
                self.conns[self.current_db_name]['db_port'],
                self.conns[self.current_db_name]['db_password']
            )
        )
        conn.set_session(autocommit=True)
        return conn

    def run_sql(self, sql):
        self.pg_cursor.execute(sql)
        result = self.pg_cursor.fetchall()
        return result

    def validate_table(self, table_name):
        sql = u"""SELECT table_schema, table_name 
                    FROM information_schema.tables 
                    WHERE table_name = '{}';""".format(table_name)
        result = self.run_sql(sql)
        return {u"schema_name" : result[0][0], u"table_name" : result[0][1]} if result else {}
        
    def get_tables_by_column(self, column_name):
        sql = u"""SELECT c.relname
            FROM pg_class AS c
            INNER JOIN pg_attribute AS a ON a.attrelid = c.oid
            WHERE a.attname = '{}' AND c.relkind = 'r';""".format(
            column_name
        )
        result = self.run_sql(sql)
        return [item[0] for item in result]

    def get_layer_srid(self, table_name):
        data = self.validate_table(table_name)
        if data:
            sql = u"""SELECT srid 
                FROM geometry_columns 
                WHERE f_table_name = '{}';""".format(
                table_name
            )
            result = self.run_sql(sql)
            return {u"srid" : result[0][0] if result[0][0] else u"31982" }

    def get_layer_columns(self, table_name):
        data = self.validate_table(table_name)
        if data:
            sql = u"""SELECT column_name 
                FROM information_schema.columns
                WHERE table_schema = '{0}'
                AND table_name = '{1}'
                AND column_name !~ 'geom' AND column_name !~ 'id';""".format(
                data['schema_name'],
                data['table_name']
            )
            result = self.run_sql(sql)
            return [item[0] for item in result]
        return []

    def get_layer_domains(self, table_name):
        data = self.validate_table(table_name)
        if data:
            sql = u"""SELECT pg_get_constraintdef(c.oid) AS cdef
                FROM pg_constraint c
                JOIN pg_namespace n
                ON n.oid = c.connamespace
                WHERE contype IN ('f')
                AND n.nspname = '{0}'
                AND conrelid::regclass::text IN ('{0}.{1}');""".format(
                data['schema_name'],
                data['table_name']
            )
            result = self.run_sql(sql)
            return {
                item[0].split('(')[1].split(')')[0].replace(' ', '') :
                item[0].split('(')[1].split('.')[1]
                for item in result
            }
        return {}

    def get_layer_contrains_codes(self, layer_name):
        sql = u"""SELECT d.column_name, c.consrc
            FROM
            (SELECT conname, consrc FROM  pg_constraint) c
            INNER JOIN
            (
                SELECT column_name, constraint_name
                FROM information_schema.constraint_column_usage WHERE table_name = '{0}'
            ) d
            ON (c.conname = d.constraint_name AND not(d.column_name = 'id'));""".format(
            layer_name
        )
        result = self.run_sql(sql)
        codes = {}
        for item in result:
            field = item[0]
            text = item[1]
            code_list = []
            for code in " ".join(" ".join(text.split("(")).split(")")).split(" "):
                try:
                    int(code)
                    code_list.append(code)
                except:
                    pass
            codes[field] = ",".join(code_list)
        return codes

    def get_domain_values(self, table_name, code_list=False):
        data = self.validate_table(table_name)
        if data:
            if code_list:
                sql = u"SELECT code, code_name FROM {0}.{1} WHERE code IN ({2});".format(
                    data['schema_name'], table_name, code_list
                )
            else:
                sql = u"SELECT code, code_name FROM {0}.{1};".format(
                    data['schema_name'], table_name
                )
            result = self.run_sql(sql)
            result2dict = dict(result)
            invert_result2dict = {v : k for k, v in result2dict.items()}
            return invert_result2dict

    def get_fields_values(self, field, domains, constraint):
        if field in constraint:
            values = self.get_domain_values(domains[field], constraint[field])
        else:
            values = self.get_domain_values(domains[field])
        values.update({u"IGNORAR" : 10000})
        return values

    def get_workspaces_wkt(self, table_name):
        data = self.validate_table(table_name)
        if data:
            sql = u"""SELECT mi, st_asewkt(geom)
                FROM {0}.{1};""".format(
                data['schema_name'], data['table_name']
            )
            result = self.run_sql(sql)
            items = {item : value for item, value in result}
            return items
        return {}
        


    
        


    