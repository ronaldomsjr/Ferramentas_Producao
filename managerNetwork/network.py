# -*- coding: utf-8 -*-
from PyQt4 import QtCore
from qgis import core, gui
from platform   import system as system_name
from auth_smb import Auth_Smb
import os, requests, sys, re, subprocess, json, socket


class Network:
    def __init__(self, parent=None):
        self.parent = parent

    def server_on(self, server):
        try:
            session = requests.Session()
            session.trust_env = False
            session.get(server, timeout=8)
            return True
        except: 
            return False

    def check_conn(self, data):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((
                data['host'],
                int(data['port'])
            ))
            return True
        except Exception as e:
            return False
    
    def POST(self, host, url, post_data={}, header={}):
        header['content-type'] = 'application/json'
        session = requests.Session()
        session.trust_env = False
        response = session.post(url, data=json.dumps(post_data), headers=header)
        return response

    def GET(self, host, url, header={}):
        try:
            session = requests.Session()
            session.trust_env = False
            response = session.get(url,  headers=header)
            return response
        except requests.exceptions.InvalidURL:
            return 1
        except requests.exceptions.ConnectionError:
            return 2
        
    def download(self, pathOrigin, pathDest, login_remote={}):
        if system_name() == u"Windows":
            try:
                command = u"copy {0} {1}".format(
                    pathOrigin,
                    pathDest
                )
                os.popen(command)
                name_file = pathOrigin.split(u"\\")[-1]
                if os.path.exists(u"{0}/{1}".format(pathDest, name_file)):
                    return True
                return False
            except:
                return False
        elif system_name() == u"Linux":
            try:
                auth_smb = Auth_Smb(self.parent)
                r = auth_smb.exec_()
                if r:
                    pathOrigin = pathOrigin.replace("\\", os.sep)
                    name_file = pathOrigin.split(u"/")[-1]
                    path_file_dest = u"{0}/{1}".format(pathDest, name_file)
                    scrip_path = os.path.join(
                        os.path.dirname(__file__),
                        'get_file_smb.py'
                    )
                    cmdline = "{6} {0} {1} {2} {3} {4} {5}".format(
                        scrip_path,
                        "smb:{0}".format(pathOrigin),
                        path_file_dest,
                        auth_smb.user, 
                        auth_smb.passwd,
                        auth_smb.domain,
                        self.get_py_version()
                    )
                    process = os.popen(cmdline)
                    process.read()
                    process.close()
                    if os.path.exists(path_file_dest):
                        return True
            except:
                return False

    def get_py_version(self):
        try:
            import smbc
            return "python"
        except:
            return "python3"