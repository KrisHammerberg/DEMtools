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
 This script initializes the plugin, making it known to QGIS.
"""

def classFactory(iface):
    # load DemTools class from file DemTools
    from demtools import DemTools
    return DemTools(iface)
