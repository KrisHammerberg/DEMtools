# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ShadowVol
                                 A QGIS plugin
 Calculate shadow volume from DEM and single vector
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
import numexpr as ne
import math

# Import the code for the dialog 
from demtoolsdialog import ShadowVolDialog
from demtoolsdialog import SVFdialog

#profiling
import cProfile
import pstats
import StringIO
from line_profiler import LineProfiler

class shaDEM:

    def __init__(self, iface,  svfContext = False):
        
        # Save reference to the QGIS interface
        self.iface = iface
        # a reference to our map canvas
        self.canvas = self.iface.mapCanvas()
        
        self.svfContext = svfContext

        # Create the dialog (after translation) and keep reference
        # dependent on which it is context called from - how is solar access tool working without a specific dialog context? CHECK
        if self.svfContext:
            self.dlg = SVFdialog()
        else:
            self.dlg = ShadowVolDialog()
         
        #QMessageBox.information( self.iface.mainWindow(),"Info", "dialog context : " + self.dlg.name )
        #interactive GUI connections:
        self.dlg.comboBox.currentIndexChanged['QString'].connect(self.getParameters) 
        self.dlg.spinBox_bands.valueChanged.connect(self.getParameters)
        #with cProfile:
        #self.dlg.runButton.clicked.connect(self.tmpProfile)
        #without cProfile: 
        self.dlg.runButton.clicked.connect(self.initLayer)
        self.dlg.spinBox_maxHt.valueChanged.connect(self.checkInput)        

    def tmpProfile(self):
        runFunction = self.initLayer
        cProfile.runctx('runFunction()', globals(), locals(),  'restats')
        stream = StringIO.StringIO()
        p = pstats.Stats('restats',  stream=stream)
        p.strip_dirs().sort_stats('time').print_stats(15)
        statString = stream.getvalue()
        print stream.getvalue()
        stream.close()

    # run method that performs all the real work
    def start(self):
        #QMessageBox.information( self.iface.mainWindow(),"Info", "shaDEM 'start' start" )
        #setup comboBox options by finding all raster layers
        #have to access the ui through the dialog - i.e: self.dlg
        
        self.dlg.runButton.setEnabled(False)
       
        self.dlg.comboBox.clear()
        for item in self.listlayers(1): #Raster = 1, Vector = 0
            self.dlg.comboBox.addItem(item)
        
        #setup Raster Settings Menu
        self.getParameters()
        self.checkInput()
        
        # show the dialog
        self.dlg.show()
    
    def getParameters(self): #input parameter removed
        selectLayer = QgsMapLayerRegistry.instance().mapLayersByName(self.dlg.comboBox.currentText())[0] 
        band = self.dlg.spinBox_bands.value()
        unitsPerPixel = selectLayer.rasterUnitsPerPixelX()
        bandCount = selectLayer.bandCount()
        maxVal = selectLayer.dataProvider().bandStatistics(band).maximumValue
        
        #debug
        #QMessageBox.information( self.iface.mainWindow(),"Debug", "bandCount = %s maxVal = %s" % (str(bandCount),str(maxVal) ))
        #QgsMessageLog.logMessage("bandCount = %s maxVal = %s" % (str(bandCount),str(maxVal) ),  "Plugins",  0)
        
        self.dlg.label_unitsPerPx.setText("%.3f" % unitsPerPixel)
        self.dlg.label_maxValue.setText("%.2f" % maxVal)
        #if type(input).__name__ == 'str':  ##Why did I want to limit this functionality with a string input?!
        self.dlg.spinBox_bands.setMaximum(bandCount)
        self.dlg.spinBox_maxHt.setValue(maxVal)

    def checkInput(self):
        
        if  self.dlg.spinBox_maxHt.value() > 0:
            self.dlg.runButton.setEnabled(True)

#Gets selected layer from GUI & preforms initial checks for validity
    def initLayer(self):
        self.orgLayer= QgsMapLayerRegistry.instance().mapLayersByName(self.dlg.comboBox.currentText())[0] 
        rlayer = self.orgLayer
        band = self.dlg.spinBox_bands.value()
        
        azimuth = math.radians(self.dlg.azimuth.value())
        solarElevation = math.radians(self.dlg.solarElevation.value())
        hyp = math.cos(solarElevation)
        x = math.sin(azimuth) * hyp
        y = math.cos(azimuth) * hyp
        z = math.sin(solarElevation)

        if z <= 0:
            z = 1
            #TODO : add a warning about Z <= 0  and prompt for real value... actually specify azimuth and solar elevation > 0 
        
        vector = [x, y, z]
        scale = rlayer.rasterUnitsPerPixelX()
        
        maxVal = rlayer.dataProvider().bandStatistics(band).maximumValue
        #QgsMessageLog.logMessage("maxVal = %s" % str(maxVal),  "Plugins",  0)
        maxUsrHeight = self.dlg.spinBox_maxHt.value()
        #QgsMessageLog.logMessage("maxUsrHeight = %s" % str(maxUsrHeight),  "Plugins",  0)
        unitZ = maxVal / maxUsrHeight
        #QgsMessageLog.logMessage("unitZ = %s" % str(unitZ),  "Plugins",  0)
        
        data = self.rasterToArray(rlayer, band)
        a = data["array"]
        
        #profiler = LineProfiler()
        #profiler.add_function(self.ShadowCalc)
        #profiler.enable_by_count()
        result = self.ShadowCalc(data,  vector, scale, unitZ,  maxVal)
        #profiler.print_stats()
        b = result[0]
        
        data["array"] = b
       
        self.saveToFile(data)
  
    #Begin Vector Calculation
    def ShadowCalc(self, data, vector,  scale,  unitZ,  maxVal):
        #this is the meat of the matter
        a = data["array"]
        #offset holds the results of the shadowvol calculation
        offset = a.copy()
        #sink holds a copy of the original array that will be gradually reduced in height
        sink = a.copy()
        
        #init variables
        #        {increments for each step}
        #     {larger of x and y must be 1 pixel}
        step = 1.0
        dmax = 0
        dx = float(abs(vector[0]))
        dy = float(abs(vector[1]))
        
        if dx > dy:
            step = 1.0 / dx
        elif dy > 0:
            step = 1.0 / dy
        else: 
            step = 1.0
        
        if dx > dy:
            dmax = data["width"]
        else:
            dmax = data["height"]
        
        dx = -step * vector[0]
        dy = -step * vector[1]
        dz = -step * vector[2] * scale / unitZ
        
        xStart = 0
        xEnd = 0
        yStart = 0
        yEnd = 0

        #        {number of iterations}
        imax = int(-maxVal / dz) 
        if imax > dmax:
            imax = dmax
        if imax < 1:
            imax = 1
        
        if not self.svfContext:
            self.dlg.progressBar.setMaximum(imax)
        
        #main loop
        i=1
        while i < imax:

            xOffset = int(round(i*dx))
            yOffset = int(round(i*dy))
            zReduction = dz
           #copy is reduced by dz each iteration
            sink = ne.evaluate('sink + zReduction')
            
            if abs(xOffset) > data["width"] or abs(yOffset) > data["height"]:
                break

            #set bounds for copy operation
            if xOffset >= 0:
                xStart = 0
                xEnd = data["width"] - xOffset
            else: #elif xOffset < 0:
                xStart = abs(xOffset)
                xEnd = data["width"] 

            if yOffset >=0:
                yStart = yOffset
                yEnd = data["height"]
            else:
                yStart=0
                yEnd = data["height"] + yOffset

            x_index = xStart

            #select the portion of 'sink' to compare to the offset
            selArray = sink[yStart:yEnd,  xStart:xEnd]
            #select the offset array
            offArray = offset[yStart-yOffset:yEnd-yOffset,  xStart+xOffset:xEnd+xOffset]
            #use NUMEXPR evaluate
            offset[yStart-yOffset:yEnd-yOffset,  xStart+xOffset:xEnd+xOffset] = ne.evaluate('where(selArray > offArray, selArray, offArray)') 
            
            if not self.svfContext:
                if  i % 3 == 0:
                    self.dlg.progressBar.setValue(i)
            i += 1
        
        return offset, dz


    #converts raster data from a single band to NumPy array 
    #returns dictionary with other relevant info about the target raster
    def rasterToArray(self, rlayer, bandNum):
        warn = QgsMessageViewer()
        #Open Source File and copy to array
        provider = rlayer.dataProvider()
        filePath = str(provider.dataSourceUri())
        dataSet = gdal.Open(filePath)
        if dataSet is None:
            warn.setMessageAsPlainText("Failed to Open Source File at: " + filePath)
            warn.showMessage()
        
        width = rlayer.width()
        height = rlayer.height()
        
        fileFormat = dataSet.GetDriver().ShortName
        projection = dataSet.GetProjection()
        geotransform = dataSet.GetGeoTransform()
        band = dataSet.GetRasterBand(bandNum)
        bandType = band.DataType
       
       #the real magic
        a = dataSet.ReadAsArray().astype(np.float)
        
        data = {"array": a,  "projection": projection,  "geotransform": geotransform,  "filePath":filePath,  "fileFormat":fileFormat, "bandType":bandType,  "width":width,  "height":height}
        return data
    
    def saveToFile(self, data):
        #Save array as new file 
        #Check file format for GDAL Create capability
        warn = QgsMessageViewer()
        driver = gdal.GetDriverByName( data["fileFormat"] )
        metadata = driver.GetMetadata()
        if metadata.has_key(gdal.DCAP_CREATE) and metadata[gdal.DCAP_CREATE] == 'YES':
            #warn.setMessageAsPlainText('Driver %s supports Create() method.' % format)
            #warn.showMessage()
            pass
        else:
            warn.setMessageAsPlainText('Driver %s does NOT support Create() method. Aborting...')
            sys.exit()
            #TODO: Give user option of converting to a compatible file type.
      
        #Create New Raster file
        newPath = "_shadowVol.".join(data["filePath"].rsplit(".", 1))
        
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
        orgLayerName = self.dlg.comboBox.currentText()
        newLayerName = orgLayerName + " Shadow"
        self.iface.addRasterLayer(path, newLayerName)
        newLayer = QgsMapLayerRegistry.instance().mapLayersByName(newLayerName)[0]
        band = self.dlg.spinBox_bands.value()
        maxVal = self.orgLayer.dataProvider().bandStatistics(band).maximumValue
        rend = newLayer.renderer()
        enhancement = QgsContrastEnhancement()
        enhancement.setContrastEnhancementAlgorithm(1, False)
        enhancement.setMaximumValue(maxVal) 
        enhancement.setMinimumValue(0) #Is 0 the correct behaviour? need to accomodate DEM with negative values
        rend.setContrastEnhancement(enhancement)
        self.iface.mapCanvas().refresh()
    
#Select all layers of a given type and return as list
    def listlayers(self,layertype):
        layersmap=QgsMapLayerRegistry.instance().mapLayers()
        layerslist=[]
        for (name,layer) in layersmap.iteritems():
            if (layertype==layer.type()):
                layerslist.append(layer.name())
        return layerslist
