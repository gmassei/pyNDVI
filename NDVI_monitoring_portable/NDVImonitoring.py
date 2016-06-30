#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  elaborate NDVI and EVI index from MODIS
#  
#  Copyright 2016 gianluca massei <g_massa@libero.it>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
# 
"""
AAAA.12.19     353 
AAAA.12.03     337 
AAAA.11.17     321 
AAAA.11.01     305 
AAAA.10.16     289 
AAAA.09.30     273 
AAAA.09.14     257 
AAAA.08.29     241 
AAAA.08.13     225 
AAAA.07.28     209 
AAAA.07.12     193 
AAAA.06.26     177 
AAAA.06.10     161 
AAAA.05.25     145 
AAAA.05.09     129 
AAAA.04.23     113 
AAAA.04.07     097 
AAAA.03.22     081 
AAAA.03.06     065 
AAAA.02.18     049 
AAAA.02.02     033 
AAAA.01.17     017 
AAAA.01.01     001 
"""
import os
import pymodis
import subprocess 
from osgeo import gdal
import datetime
import csv
import numpy as np

import plotly.tools as tls
import plotly.plotly as py
from plotly.graph_objs import *

#####plotly credential################
tls.set_credentials_file(username="GianlucaMassei",api_key="ct5xumzsfx")
stream_token_series='ciwtg2uycs'
stream_token_anomaly='y5r7tudz8g'
######################################
########plotly setting################
trace_series = Scatter(x=[],y=[],stream=Stream(token=stream_token_series),yaxis='y',name='NDVI series')
trace_anomaly = Scatter(x=[],y=[],stream=Stream(token=stream_token_anomaly),yaxis='y2',name='NDVI anomaly index')
layout = Layout(title='NDVI MODIS Streaming data for Olea auropea in Umbria region (Italy)',
	yaxis=YAxis(title='NDVI index'),
	yaxis2=YAxis(title='Anomaly',side='right',overlaying="y"
	)
)

fig = Figure(data=[trace_series,trace_anomaly], layout=layout)
print py.plot(fig, filename='NDVI MODIS Streaming data for Olea auropea')
########settings######################
DOWNLOAD_FOLDER='downloadHDF'
OUTPUT_TIFF='outpuTIFF'
CLIP_SHAPEFILE='clip\oliveti_CNAT.shp' #folder for clipper shapefile
CLIPPED_TIFFILE='clipped\_' #foleder for clipped tiff files
END_DATE="2001-01-01" #start data for check download


def connect2MODIS(end_date):
	"""connect to MODIS server"""
	now=datetime.datetime.now().strftime("%Y-%m-%d")
	dm = pymodis.downmodis.downModis(destinationFolder=os.path.abspath(DOWNLOAD_FOLDER),path="MOLT", product="MOD13Q1.005",tiles="h18v04",today = now, enddate = end_date)
	dm.connect() 
	print "Connection Attempts: " + str(dm.nconnection)
	return dm
	
def filesDownloaded():
	"""check files downloaded"""
	existsFiles = [line.strip() for line in open("checkfile.txt", 'r')]
	return existsFiles
	
def filesAvailable(dm):
	"""check files available in MODIS server"""
	downloads = []
	for day in dm.getListDays():
		files = dm.getFilesList(day) 
		for f in files:
			downloads.append((f,day))
	numDownload = len(downloads)
	print "Files to Download: " + str(numDownload)
	return downloads

def download(dm,filename, day):
	"""download files from MODIS server[http://e4ftl01.cr.usgs.gov]"""
	dm.downloadFile(filename,os.path.abspath(DOWNLOAD_FOLDER+filename),day)
	

def convert2Tif(hdfFiles):
	baseName=os.path.splitext(hdfFiles)[0]
	convert = pymodis.convertmodis_gdal.convertModisGDAL(hdfname =os.path.abspath(DOWNLOAD_FOLDER+ str(hdfFiles)), \
		prefix = OUTPUT_TIFF+ baseName, subset = '(1)', res=250, outformat = 'GTiff', \
		epsg=3004, wkt=None,  resampl = 'NEAREST_NEIGHBOR', vrt = False)
	convert.run()
	return str(baseName)+'_250m 16 days NDVI.tif'

def gdalProcessing(tifFiles):
	"""clip and retrieve summary data from raster"""
	command1="gdalwarp -cutline '%s' '%s'  '%s'" % (os.path.abspath(CLIP_SHAPEFILE), os.path.abspath(OUTPUT_TIFF+tifFiles),\
		os.path.abspath(CLIPPED_TIFFILE+tifFiles))
	subprocess.call(command1, shell=True)
	
# the raster should be multiplied by 0.0001 in order to achieve the actual data value
	command2="gdalinfo -stats '%s'"  % (os.path.abspath(CLIPPED_TIFFILE+tifFiles))
	info = subprocess.Popen(command2, stdout=subprocess.PIPE, shell=True)
	(output, err) = info.communicate()
	
def retrieveStats(filename,date):
	# open raster and choose band to find min, max
	raster = '%s' % (os.path.abspath(CLIPPED_TIFFILE+filename))
	gtif = gdal.Open(raster)
	srcband = gtif.GetRasterBand(1)
	# Get raster statistics
	stats = srcband.GetStatistics(True, True)
	stats.insert(0,date)
	stats.append(filename)
	stats.append(date[5:])
	# Print the min, max, mean, stdev based on stats index
	fstats=open('stats.csv','a')
	fstats = csv.writer(file("stats.csv", "a"))
	fstats.writerow(stats)
	print "[ STATS ] =  Date=%s, Minimum=%.3f, Maximum=%.3f, Mean=%.3f, StdDev=%.3f" % \
		(str(stats[0]),stats[1], stats[2], stats[3], stats[4])
	return stats
	
	
def cleaner():
	command1="rm %s\*" % os.path.abspath(DOWNLOAD_FOLDER)
	subprocess.call(command1, shell=True)
	command2="rm %s\*" % os.path.abspath(OUTPUT_TIFF)
	subprocess.call(command2, shell=True)
	command3="rm %s*" % os.path.abspath(CLIPPED_TIFFILE)
	subprocess.call(command3, shell=True)
	

def anomalyNDVI(day):
	f=open('stats.csv')
	statsArray=np.loadtxt(f,dtype={'names':('date','Minimum','Maximum','Mean','StdDev','file','day'),\
		'formats':('S10','f10','f10','f10','f10','S65','S10')},delimiter=',')
	statsDay=statsArray[statsArray['day']==day] #list all data based on day value
	anomaly=(statsDay['Mean'][-1]-statsDay['Mean'].mean())/(statsDay['Mean'].mean())  #find anomaly value
	#print statsDay['Mean'][-1],statsDay['Mean'].mean()
	f.close()
	return anomaly
	
def main():
	stream_series = py.Stream(stream_token_series)
	stream_series.open()
	stream_anomaly = py.Stream(stream_token_anomaly)
	stream_anomaly.open()
	end_date=END_DATE
	while(True):
		checkfile = open("checkfile.txt", 'a')
		dm=connect2MODIS(end_date)
		existsFiles=filesDownloaded()
		availableFiles=filesAvailable(dm)
		downloads=[(f,date) for (f,date) in availableFiles if f not in existsFiles]
		downloads.sort()
		for filename, date in downloads:
			print "DL: " + filename
			download(dm,filename, date)
			if filename.endswith('.hdf'):
				tifFile=convert2Tif(filename)
				gdalProcessing(tifFile)
				stats=retrieveStats(tifFile,date)
				stream_series.write(dict(x=str(stats[0]), y=stats[3]))
				anomaly=anomalyNDVI(date[5:])
				print anomaly,stats[3]
				stream_anomaly.write(dict(x=str(stats[0]), y=anomaly))
				end_date=date
			checkfile.write(filename+"\n")
			cleaner()
		checkfile.close()
	stream_series.close()
	stream_anomaly.close()
	return 0

if __name__ == '__main__':
	main()


