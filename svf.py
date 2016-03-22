# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ShadowVol
                                 A QGIS plugin
 Calculate shading from DEM and single vector
                              -------------------
        begin                : 2013-01-24
        copyright            : (C) 2013 by Kris Hammerberg
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
from qgis.gui import *
import sys
# Import Math, GDAL libraries and NumPy
from osgeo import gdal, ogr
from osgeo.gdalconst import *
import numpy as np
import math
import random
import csv
#numexpr allows for parallel processing
#  e.g.    c = ne.evaluate("2*a+3*b")
import numexpr as ne
import multiprocessing as mp

# Import the code for the dialog 
from demtoolsdialog import SVFdialog

# Import ShaDEM for single vector calc
from shaDEM import shaDEM 

#import time optimization
#import time

#profiling
#import cProfile
#import pstats
#import StringIO
#from line_profiler import LineProfiler

class svf:

    def __init__(self, iface):
        
        # Save reference to the QGIS interface
        self.iface = iface
        # a reference to our map canvas
        self.canvas = self.iface.mapCanvas()
        # a reference to shaDEM with the svfContext set to True
        self.shaDEM = shaDEM(iface,  True)

        # Create the dialog (after translation) and keep reference        
        self.dlg = SVFdialog()
        
        #interactive GUI connections:
        self.dlg.comboBox.layerChanged.connect(self.getParameters) #is it possible to call shaDEM class functions here? 
        self.dlg.spinBox_bands.valueChanged.connect(self.getParameters)
        self.dlg.runButton.clicked.connect(self.initLayer)
        #debug - activate cProdile
        #self.dlg.runButton.clicked.connect(self.tmpProfile)
        self.dlg.spinBox_maxHt.valueChanged.connect(self.checkInput)      
    
#    def tmpProfile(self):
#        runFunction = self.initLayer
#        cProfile.runctx('runFunction()', globals(), locals(),  'restats')
#        stream = StringIO.StringIO()
#        p = pstats.Stats('restats',  stream=stream)
#        p.strip_dirs().sort_stats('time').print_stats(15)
#        statString = stream.getvalue()
#        print stream.getvalue()
#        stream.close()
    
    # run method that performs all the real work
    def start(self):
        #setup comboBox options by finding all raster layers
        #have to access the ui through the dialog - i.e: self.dlg
        self.dlg.runButton.setEnabled(False)
        
#         self.dlg.comboBox.clear()
#         for item in self.shaDEM.listlayers(1): #Raster = 1, Vector = 0
#             self.dlg.comboBox.addItem(item)
        
        #setup Raster Settings Menu
        self.getParameters()
        self.checkInput()
        # show the dialog
        self.dlg.show()

    def getParameters(self):
        selectLayer = self.dlg.comboBox.currentLayer()#QgsMapLayerRegistry.instance().mapLayersByName(self.dlg.comboBox.currentText())[0] #self.getLayerByName(self.dlg.comboBox.currentText())
        if selectLayer is None:
            QMessageBox.critical( self.iface.mainWindow(),"No Raster Layers", "Plugin requires raster layers to be loaded in the project" )
            sys.exitfunc()
        band = self.dlg.spinBox_bands.value()
        unitsPerPixel = selectLayer.rasterUnitsPerPixelX() #assumes square pixels
        bandCount = selectLayer.bandCount()
        maxVal = selectLayer.dataProvider().bandStatistics(band).maximumValue
 
        self.dlg.label_unitsPerPx.setText("%.3f" % unitsPerPixel)
        self.dlg.label_maxValue.setText("%.2f" % maxVal)
       #if type(input).__name__ == 'str':  ##again, why not refresh on each getParameter call? 
        self.dlg.spinBox_bands.setMaximum(bandCount)
        self.dlg.spinBox_maxHt.setValue(maxVal)
    
    def checkInput(self):
        
        if  self.dlg.spinBox_maxHt.value() > 0:
            self.dlg.runButton.setEnabled(True)
    
#Gets selected layer from GUI & preforms initial checks for validity
    def initLayer(self):
        ne.set_num_threads(mp.cpu_count()) # 1 thread per core
        rlayer=self.dlg.comboBox.currentLayer()#QgsMapLayerRegistry.instance().mapLayersByName(self.dlg.comboBox.currentText())[0]#self.getLayerByName(self.dlg.comboBox.currentText())
        sensorHt = self.dlg.spinBox_sensorHt.value()
        
        #get list of sun vectors
        vectors = self.skyVectors()
        self.dlg.progressBar.setMaximum(len(vectors))
        
        scale = rlayer.rasterUnitsPerPixelX() #assumes square pixels. . . 
        bandNum = self.dlg.spinBox_bands.value()
        maxVal = rlayer.dataProvider().bandStatistics(bandNum).maximumValue
        #QgsMessageLog.logMessage("maxVal = %s" % str(maxVal),  "Plugins",  0)
        maxUsrHeight = self.dlg.spinBox_maxHt.value()
        #QgsMessageLog.logMessage("maxUsrHeight = %s" % str(maxUsrHeight),  "Plugins",  0)
        unitZ = maxVal / maxUsrHeight
        #QgsMessageLog.logMessage("unitZ = %s" % str(unitZ),  "Plugins",  0)
        
        bandCnt = rlayer.bandCount()
        
        data = self.shaDEM.rasterToArray(rlayer, bandNum)
        
        #t = time.time()
        a = data["array"].copy()
        adjSensorHt = (sensorHt / unitZ)
        a = ne.evaluate("a + adjSensorHt")
        #QgsMessageLog.logMessage("Adjusted Sensor Height= %s" % str(adjSensorHt),  "Plugins",  0)
        svfArr = np.zeros(a.shape)
        i = 0
        
        
        for vector in vectors:
            #debug - print solar altitude angles
            #QgsMessageLog.logMessage("Vector[%i] solar alt angle: %.2f" % (i+1, math.degrees(math.atan(vector[2]/math.sqrt(vector[0]**2+vector[1]**2)))),  "Profile",  0)
            
            result = self.shaDEM.ShadowCalc(data,  vector, scale, unitZ,  maxVal)
            b = result[0]
            dz = result[1]
            
            svfArr = ne.evaluate('where((b-a) <= 0, svfArr + 1, svfArr)')

            self.dlg.progressBar.setValue(i)
            i += 1

       # t = time.time() - t
        #QgsMessageLog.logMessage("SVF main loop : " + str(t),  "Profile",  0)
        
        data["array"] = svfArr / self.dlg.spinBox_vectors.value()
        
        self.saveToFile(data)


    def skyVectors(self):
        #populate sky with cosine weighted distribution of vectors according to Ratti & Richens 1999
        vectors = []
        number = self.dlg.spinBox_vectors.value()
        i = 0
        while i < number:
            azimuth = random.vonmisesvariate(math.pi,0)
            radius = math.sqrt(random.random())
            solarElevation = math.acos(radius)
            
            x = math.cos(azimuth) * radius
            y = math.sin(azimuth) * radius
            z = math.sin(solarElevation)
            
            vector = [x, y, z]
            vectors.append(vector)
            i += 1
        
#        with open('vectors_debug.csv',  'wb') as csvfile:
#            writer = csv.writer(csvfile)
#            for line in vectors:
#                writer.writerow(line)
        return vectors

#Select all layers of a given type and return as list
    def listlayers(self,layertype):
        layersmap=QgsMapLayerRegistry.instance().mapLayers()
        layerslist=[]
        for (name,layer) in layersmap.iteritems():
            if (layertype==layer.type()):
                layerslist.append(layer.name())
        return layerslist

    def saveToFile(self, data):
        #Save array as new file 
        #Check file format for GDAL Create capability
        warn = QgsMessageViewer()
        driver = gdal.GetDriverByName( data["fileFormat"] )
        metadata = driver.GetMetadata()
        if metadata.has_key(gdal.DCAP_CREATE) and metadata[gdal.DCAP_CREATE] != 'YES':
            #warn.setMessageAsPlainText('Driver %s supports Create() method.' % format)
            #warn.showMessage()
       # else:
            warn.setMessageAsPlainText('Driver %s does NOT support Create() method. Aborting...')
            sys.exit()
            #TODO : Give user option of converting to a compatible file type.
      
        #Create New Raster file
        newPath = "_svf.".join(data["filePath"].rsplit(".", 1))
        
        if data["fileFormat"] == 'GTiff':
            dst_ds = driver.Create( newPath, data["width"], data["height"], int(1), data["bandType"],  'TFW=YES' ) 
            dst_ds.SetGeoTransform(data["geotransform"])
            dst_ds.SetProjection(data["projection"])
        else:
            dst_ds = driver.Create( newPath, data["width"], data["height"], int(1), data["bandType"] ) 
            dst_ds.SetGeoTransform(data["geotransform"])
            dst_ds.SetProjection(data["projection"])

        #write to array
        dst_ds.GetRasterBand(1).WriteArray( data["array"] )
        
        # Once we're done, close properly the dataset
        dst_ds = None
        
        self.AddAsNewLayer(newPath)

#Takes path of raster file and adds new layer
    def AddAsNewLayer(self,  path):
        #adds the new image as a layer, inverts and sets the contrast
        name = "SVF"
        self.iface.addRasterLayer(path, name)
        rlayer= QgsMapLayerRegistry.instance().mapLayersByName(name)[0] #self.getLayerByName(name)
        rlayer.setContrastEnhancement(1)
        #rlayer.setInvertHistogram(True)
        self.iface.mapCanvas().refresh()
