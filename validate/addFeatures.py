# -*- coding: utf-8 -*-
from PyQt4 import QtCore, QtGui
from qgis import core, gui, utils
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__),'../'))
from managerQgis.projectQgis import ProjectQgis

class AddFeatures(QtCore.QObject):

    def __init__(self, iface, dataLogin=False):
        super(AddFeatures, self).__init__()
        self.iface = iface
        self.projectQgis = ProjectQgis(self.iface)

    def validate(self):
        if self.iface.activeLayer():
            features_added = self.iface.activeLayer().editBuffer().addedFeatures() if self.iface.activeLayer().editBuffer() else False
            if features_added:
                self.test_add_in_moldura(features_added)

    def test_add_in_moldura(self, features_added):
        variable_name = u'area_trabalho_poligono'
        ewkt = self.projectQgis.getVariableLayer(variable_name)
        if ewkt:
            wkt = ewkt.split(';')[1]
            geom = core.QgsGeometry.fromWkt(wkt)
            feat_key = sorted(list(features_added.keys()))[0]
            feat = features_added[feat_key]
            if geom.intersects(feat.geometry()) == False:
                active_lyr = self.iface.activeLayer()
                QtGui.QMessageBox.critical(
                    self.iface.mainWindow() ,  
                    u'ERRO!' ,  
                    u'''
                    <p style="color:red">
                        Aquisicão da camada {0} está fora do limite de trabalho!
                    </p>
                    '''.format(active_lyr.name())
                )
                active_lyr.undoStack().undo()                  
            self.iface.mapCanvas().refresh()
