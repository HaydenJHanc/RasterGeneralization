import arcpy
import os
import numpy as np
from arcpy import env
from arcpy.sa import *

arcpy.env.overwriteOutput = True

# Insert file of imagery
# Use if raster is saved locally
ImageFile = r'' # Insert Filepath Here

# Use if sourcing from REST server
# getOutput(0) assumes that the raster value is the only value in the raster dataset, change if the value is in a different column
# ImageFile = '' Insert REST server layer here
# ImageFile = arcpy.management.MakeImageServerLayer(ImageFile, "ImageServerLayer").getOutput(0)
# Assumes the value you want is the first field in the raster, change if otherwise

# Where the files will temporarly save the clipped raster
TempFolder = r"" # Insert folder here

# File of Polygon to generalize (has to be local to add field and edit it)
PolygonFeatureFile = r"" # Insert file here

# Add field to the shapefile used in generalization, put that field in this line
with arcpy.da.UpdateCursor(PolygonFeatureFile, ["OID@", "SHAPE@", "FctImp"]) as cursor:
    # For all polygons in your shapefile
    for row in cursor:
        # Doesn't Process raster if the value is already populated
        if row[2] == 0 or row[2] == None:
            arcpy.env.cellSize = None
            print(f"Processing Polygon {row[0]}")
            feature_id, feature_geom = row[0], row[1]
            Extent = feature_geom.extent
       
            # Create filepath for clipped raster
            TempRaster = os.path.join(TempFolder, f"temp_{feature_id}.tif")
       
            # ArcGIS has a limit on the size of rasters clipped. This block reduces the resolution to the limit
            Width = Extent.XMax - Extent.XMin
            Height = Extent.YMax - Extent.YMin

            # Used for optimization of raster cell size, remove if unnessesary
            print(f"Width: {Width}")
            print(f"Height: {Height}")
            print(f"Cell Size: {arcpy.env.cellSize}")
       
            # ArcGIS has a limit on the size of rasters clipped. This block reduces the resolution to the limit
            # Will need a different scaling method for your specific cell-to-polygon size ration
            '''
            if Width > 0.1 or Height > 0.1:
                arcpy.env.cellSize = max(Width * 100, Height * 100)
            elif Width > 0.05 or Height > 0.05:
                arcpy.env.cellSize = max(Width * 50, Height * 50)
            '''
            # Clips, or rather extracts by mask, the raster. The raster is now only within your polygon
            print(arcpy.env.cellSize)
            ClippedRaster = ExtractByMask(ImageFile, feature_geom)
            ClippedRaster.save(TempRaster)

            # Used to check the number of cells in the clippedraster
            Columns = arcpy.management.GetRasterProperties(TempRaster, "COLUMNCOUNT")
            Rows = arcpy.management.GetRasterProperties(TempRaster, "ROWCOUNT")

            print(f"Number of Columns: {Columns}")
            print(f"Number of Rows: {Rows}")
           
            # The molasses and potatoes of the whole operation. The clipped raster is converted
            # to a numpy array, making it a list of numbers. The nodata values are assigned as 1.0
            # The reason it is set to 1 is because it allows us to subtract the number of cells from the total count of cells
            ValueArray = arcpy.RasterToNumPyArray(TempRaster, nodata_to_value=1.0)
       
            # Adds all pixels that are at the extremes of your index
            NoDataPixels = np.sum(ValueArray == 1.0)
       
            # Adds all numbers in array and subtracts the no data values
            ValueSum = ValueArray.sum() - NoDataPixels
       
            # Finds number of all Pixels (or cells) in clipped raster that have data and finds average
            PixelNum = ValueArray.size - NoDataPixels
            AverageRaster = ValueSum / PixelNum
       
            # Updates your shapefile with value
            row[2] = AverageRaster
            cursor.updateRow(row)
       
            # Deletes the clipped raster
            arcpy.management.Delete(TempRaster)
           
        else:
            print(f"Polygon {row[0]} already populated")