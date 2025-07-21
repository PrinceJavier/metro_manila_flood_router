import geopandas as gpd

# Load the shapefile
shapefile_path = "MetroManila_Flood_100year.shp"
gdf = gpd.read_file(shapefile_path)

# 1. Print basic info about the GeoDataFrame
print("="*50)
print("SHAPEFILE METADATA")
print("="*50)
print(f"CRS (Coordinate Reference System): {gdf.crs}")
print(f"Number of features: {len(gdf)}")
print(f"Geometry type: {gdf.geom_type.unique()}")
print(f"Bounds: {gdf.total_bounds}")

# 2. Print attribute table column names and data types
print("\n" + "="*50)
print("ATTRIBUTE TABLE COLUMNS")
print("="*50)
print(gdf.dtypes)

# 3. Print first 5 records with all attributes
print("\n" + "="*50)
print("SAMPLE RECORDS")
print("="*50)
print(gdf.head())

# # 4. Print full contents (caution: might be large)
# print("\n" + "="*50)
# print("FULL CONTENTS")
# print("="*50)
# with pd.option_context('display.max_columns', None, 'display.max_rows', None):
#     print(gdf)