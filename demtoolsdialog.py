# -*- coding: utf-8 -*-
"""
/***************************************************************************
 DemToolsDialog
                                 A QGIS plugin
 A suite of tools for doing neat things with DEMs
                             -------------------
        begin                : 2014-05-15
        copyright            : (C) 2014 by Kris Hammerberg
        email                : kris.hammerberg@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from PyQt4 import QtCore, QtGui

from ui_shadowvol import Ui_ShadowVol
from ui_svf import Ui_SVF
from ui_solaraccess import Ui_SolarAccess


class ShadowVolDialog(QtGui.QDialog, Ui_ShadowVol):
    def __init__(self):
        QtGui.QDialog.__init__(self)
        self.name = "shaDEM dialog"
        # Set up the user interface from Designer.
        self.setupUi(self)

class SVFdialog(QtGui.QDialog,  Ui_SVF):
    def __init__(self):
        QtGui.QDialog.__init__(self)
        self.name = "svf dialog"
        # Set up the user interface from Designer.
        self.setupUi(self)
    
class SolarAccessDialog(QtGui.QDialog, Ui_SolarAccess):
    def __init__(self):
        QtGui.QDialog.__init__(self)
        self.name = "solar access"
        # Set up the user interface from Designer.
        self.setupUi(self)

