# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SolarAccess
                                 A QGIS plugin
 Finds daily sun shading from DEM
                              -------------------
        begin                : 2013-09-12
        copyright            : (C) 2013 by Kris Hammerberg
        email                : TUWien
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
# Import Math, GDAL libraries and NumPy
from osgeo import gdal, ogr
from osgeo.gdalconst import *
import numpy as np
import math
# Initialize Qt resources from file resources.py
import resources_rc
# Import the code for the dialog
from demtoolsdialog import SolarAccessDialog
# import datetime for date time inputs
import datetime as dt
# Import ShaDEM for single vector calc
from shaDEM import shaDEM 
import sys
#import sys
#sys.path.append("/home/bpi/QGIS_DEV/pysolar")
try:
    from Pysolar import solar
except ImportError:
    #Pysolar not installed try solar
    try:
        import solar
    except ImportError:
        print "You've got to have pysolar installed!"
        sys.exit()


class SolarAccess:

    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        # a reference to our map canvas
        self.canvas = self.iface.mapCanvas()
        
        self.shaDEM = shaDEM(iface,  True)

        # Create the dialog (after translation) and keep reference
        self.dlg = SolarAccessDialog()
        
        #interactive GUI connections:
        self.dlg.comboBox.currentIndexChanged['QString'].connect(self.getParameters)
        self.dlg.spinBox_bands.valueChanged.connect(self.getParameters)
        self.dlg.runButton.clicked.connect(self.initLayer)
        self.dlg.spinBox_maxHt.valueChanged.connect(self.checkInput) 
        self.dlg.start_time.timeChanged.connect(self.checkInput)
        self.dlg.end_time.timeChanged.connect(self.checkInput)

    # run method that performs all the real work
    def start(self):
        #setup comboBox options by finding all raster layers
        #have to access the ui through the dialog - i.e: self.dlg.ui
        self.dlg.runButton.setEnabled(False)
        today = dt.date.today()
        self.dlg.dateEdit.setDate(QDate(today.year,  today.month, today.day))
        #self.dlg.lineEdit_maxHt.setInputMask('009.0;')
#         self.dlg.comboBox.clear()
#         for item in self.shaDEM.listlayers(1): #Raster = 1, Vector = 0
#             self.dlg.comboBox.addItem(item)
        
        #setup Raster Settings Menu
        self.getParameters('set bands')
        self.checkInput()
        # show the dialog
        self.dlg.show()
        
    
    def getParameters(self, input):
       
        selectLayer = self.dlg.comboBox.currentLayer() #QgsMapLayerRegistry.instance().mapLayersByName(self.dlg.comboBox.currentText())[0]
        if selectLayer is None:
            QMessageBox.critical( self.iface.mainWindow(),"No Raster Layers", "Plugin requires raster layers to be loaded in the project" )
            sys.exitfunc()
        band = self.dlg.spinBox_bands.value()
        unitsPerPixel = selectLayer.rasterUnitsPerPixelX()
        bandCount = selectLayer.bandCount()
        maxVal = selectLayer.dataProvider().bandStatistics(band).maximumValue
        
        self.dlg.label_unitsPerPx.setText("%.3f" % unitsPerPixel)
        self.dlg.label_maxValue.setText("%.2f" % maxVal)
        #if type(input).__name__ == 'str':
        self.dlg.spinBox_bands.setMaximum(bandCount)
        self.dlg.spinBox_maxHt.setValue(maxVal)
        
 
    def checkInput(self):
        
        if  self.dlg.spinBox_maxHt.value() > 0 and self.dlg.start_time.time() < self.dlg.end_time.time():
            self.dlg.runButton.setEnabled(True)
        else:
            self.dlg.runButton.setEnabled(False)
        
    
    def initLayer(self):
        
        layer = self.dlg.comboBox.currentLayer()# QgsMapLayerRegistry.instance().mapLayersByName(self.dlg.comboBox.currentText())[0]
        startTime = self.dlg.start_time.time()  # (h, m, s, ms) 
        endTime = self.dlg.end_time.time()   
        date = self.dlg.dateEdit.date()
        tz = self.dlg.spinBox_tz.value()
        vectors = self.dlg.spinBox_vectors.value()
        
        center = layer.extent().center()
        crsSrc = layer.crs()
        crsDest = QgsCoordinateReferenceSystem(4326)
        xform = QgsCoordinateTransform(crsSrc, crsDest)
        center = xform.transform(center)
        long = center[0]
        lat = center[1]
        
        #correct for Time Zone
        startTime.setHMS(startTime.hour() - tz,  startTime.minute(),  startTime.second())
        endTime.setHMS(endTime.hour() - tz,  endTime.minute(),  endTime.second())
        
        # convert from Qtime to PyTime
        sT = startTime.toPyTime()
        eT = endTime.toPyTime()
        pyDate = date.toPyDate()
        sDT = dt.datetime.combine(pyDate,  sT) #datetime format
        eDT = dt.datetime.combine(pyDate,  eT)
        deltaT = eDT - sDT  #(day,  sec,  microsec)
        
        step = deltaT / vectors
        timeArray = []
        solVectors = []
        
        for i in range(vectors):
            timeArray.append(sDT + (step * i))
        
        for time in timeArray:
            alt = math.radians(solar.GetAltitude(lat,  long,  time))
            azi = math.radians(solar.GetAzimuth(lat,  long,  time))
            
            z = math.sin(alt)
            hyp = math.cos(alt)
            y = - (hyp * math.cos(azi)) #pysolar has south as 0 degrees
            x = hyp * math.sin(azi)
            
            vect = [x, y, z]
            if z > 0 :
                solVectors.append(vect)
            
        
        self.dlg.progressBar.setMaximum(len(solVectors))
        
        scale = layer.rasterUnitsPerPixelX()
        bandNum = self.dlg.spinBox_bands.value()
        maxVal = layer.dataProvider().bandStatistics(bandNum).maximumValue
        QgsMessageLog.logMessage("maxVal = %s" % str(maxVal),  "Plugins",  0)
        maxUsrHeight = self.dlg.spinBox_maxHt.value()
        QgsMessageLog.logMessage("maxUsrHeight = %s" % str(maxUsrHeight),  "Plugins",  0)
        unitZ = maxVal / maxUsrHeight
        QgsMessageLog.logMessage("unitZ = %s" % str(unitZ),  "Plugins",  0)
        

        data = self.shaDEM.rasterToArray(layer, bandNum)

        t = time.time()
        a = data["array"].copy()

        svfArr = np.zeros(a.shape)
        i = 0
        
        for vector in solVectors:
            
            result = self.shaDEM.ShadowCalc(data,  vector, scale, unitZ,  maxVal)
            b = result[0]
            dz = result[1]

            mask = (b - a) <= 0  
           # b = np.zeros(b.shape)  #set b to 0 
            #b[mask] = np.ones(b.shape)[mask] # add 1 where sky vector meets surface
            svfArr += mask #necessary? #Add b to svf total
            
            self.dlg.progressBar.setValue(i)
            i += 1

        #t = time.time() - t
        #QgsMessageLog.logMessage("SVF main loop : " + str(t),  "Profile",  0)
        
        data["array"] = svfArr / self.dlg.spinBox_vectors.value()
        
        self.saveToFile(data)
    
    
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

        newPath = "_solar.".join(data["filePath"].rsplit(".", 1))
        
        if data["fileFormat"] == 'GTiff':
            dst_ds = driver.Create( newPath, data["width"], data["height"], int(1), data["bandType"],  ['TFW=YES'] ) 
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
        orgLayerName = self.dlg.comboBox.currentLayer().name()
        name = orgLayerName + " solar access"
        self.iface.addRasterLayer(path, name)
        rlayer= QgsMapLayerRegistry.instance().mapLayersByName(name)[0]
        rlayer.setContrastEnhancement(1)
        self.iface.mapCanvas().refresh()

