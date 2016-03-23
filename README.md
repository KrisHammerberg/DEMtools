DEMtools
========

A repository for the QGIS plugin suite DEM Tools

DEMTools a plugin for QGIS. It is a suite of tools for doing (hopefully) interesting things with Digital Elevation Models (DEMs). At the moment it contains three tools described below. This is my first attempt at a QGIS plugin and came about as a result of my masters thesis work at the Vienna University of Technology. 

ShaDEM
=======

ShaDEM calculates a "shadow volume" from a given DEM with a solar altitude and azimuth angle. The shadow volume is another DEM that records the upper height of the volume in shadow (as well the height of any objects in the original DEM). This is an implementation of the algorithm originally developed by Paul Richens for NIH Image (Ratti & Richens 1999).

Additionally the user can specify the band to use from the selected DEM layer. If the maximum value in the DEM doesn't correspond to the maximum height in the map units (e.g. values encoded from 0 to 255), the user can specify the maximum height in map units.

SVF
=======

The SVF tool calculates a continuous map of the sky view factor (SVF) for the given DEM. Using a cosine weighted distribution of vectors across the sky hemisphere, the plugin repeatedly calls the ShaDEM algorithm (Note: these vectors can be thought of as hypothetical light sources as they are not associated with sun position). The results from these runs are composited. The SVF of a pixel is then the number of times it is visible to the sky hemisphere along a vector (i.e. not shaded) divided by the total number of vectors. In other words, if the algorithm is run with 100 vectors and a pixel is lit 100 times it has a sky view factor of 1.

As with ShaDEM, the user has the ability to set the band to use from the input DEM and the maximum height, if different from the maximum value. Additionally, the user can specify the height of the virtual sensor where SVF is calculated. This is useful for comparison to measured values from hemispherical photography.

Most importantly, the user can specify the number of vectors to use. This is the primary trade off between precision and computation time. Low angled vectors can take several minutes to calculate (depending on the size of the area, the resolution of the DEM, and your hardware), therefore running the calculation hundreds of times can take hours.

For more on view factors see: View Factor For more information on the algorithm see: Richens 1997 or Ratti & Richens 1999

Solar Access
=============

Rather than using a distribution of hypothetical light sources, the Solar Access tool allows the user to specify a time range and calculate the sun position and corresponding vectors at equal intervals (the number is specified by the user) throughout the time period. Using these vectors, it calls the ShaDEM tool to produce a shading map for the given time period. 

Citations:
============ 
Ratti, C., & Richens, P. (1999). Urban texture analysis with image processing techniques. In Computers in Building (pp. 49-64). Springer US.

Richens, P. (1997). Image processing for urban scale environmental modelling. In Proc 5th Intemational IBPSA Conference: Building Simulation 97 (pp. 163-171). University of Bath.
