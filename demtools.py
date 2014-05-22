# -*- coding: utf-8 -*-
"""
/***************************************************************************
 DemTools
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
# Import the PyQt and QGIS libraries
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
# Initialize Qt resources from file resources.py
import resources_rc
# Import the code for the dialog
import os.path
import sys

from shaDEM import shaDEM
from svf import svf
from solaraccess import SolarAccess 


class DemTools:

    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        # save reference to tool interfaces
        self.shaDEM = shaDEM(iface)
        self.svf = svf(iface)
        self.SolarAccess = SolarAccess(iface)
        
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value("locale/userLocale")[0:2]
        localePath = os.path.join(self.plugin_dir, 'i18n', 'demtools_{}.qm'.format(locale))

        if os.path.exists(localePath):
            self.translator = QTranslator()
            self.translator.load(localePath)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)
        
        
        
       #check necessary libraries
        try:
            import numpy
            import numexpr
            import Pysolar
            
        except ImportError:
            QMessageBox.critical( self.iface.mainWindow(),"ImportError", "Plugin requires Numpy, Numexpr, and Pysolar libraries.\n\See http://www.numpy.org & https://code.google.com/p/numexpr/ & http://pysolar.org/" )
            sys.exitfunc()
        

    def initGui(self):
        # Create action that will start plugin configuration
        self.shaDEMact = QAction(
            QIcon(":/plugins/demtools/shaDEM.png"),
            u"ShaDEM", self.iface.mainWindow())
        self.SVFact = QAction(
            QIcon(":/plugins/demtools/SVF.png"),
            u"SVF", self.iface.mainWindow())
        self.solaract = QAction(
            QIcon(":/plugins/demtools/solaraccess.png"), 
            u"SolarAccess",  self.iface.mainWindow())
        
        # connect the actions to the run methods
        self.shaDEMact.triggered.connect(self.shaDEM.start)
        self.SVFact.triggered.connect(self.svf.start)
        self.solaract.triggered.connect(self.SolarAccess.start)

        # Add toolbar buttons and menu items
        self.iface.addToolBarIcon(self.shaDEMact)
        self.iface.addPluginToRasterMenu(u"&DEM Tools", self.shaDEMact)
        
        self.iface.addToolBarIcon(self.shaDEMact)
        self.iface.addPluginToRasterMenu(u"&DEM Tools", self.SVFact)        
        
        self.iface.addToolBarIcon(self.solaract)
        self.iface.addPluginToRasterMenu(u"&DEM Tools", self.solaract) 

    def unload(self):
        # Remove the plugin menu items and icons
        
        self.iface.removePluginRasterMenu(u"&DEM Tools", self.shaDEMact)
        self.iface.removeToolBarIcon(self.shaDEMact)
        self.iface.removePluginRasterMenu(u"&DEM Tools", self.SVFact)
        self.iface.removeToolBarIcon(self.SVFact)
        self.iface.removePluginRasterMenu(u"&DEM Tools", self.solaract)
        self.iface.removeToolBarIcon(self.solaract)


