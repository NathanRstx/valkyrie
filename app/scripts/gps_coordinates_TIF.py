import rasterio

with rasterio.open("DJI_0232.TIF") as dataset:
    width = dataset.width
    height = dataset.height
    print(f"Largeur: {width}, Hauteur: {height}")

    row, col = 50, 100
    lon, lat = dataset.xy(row, col) 
    print(f"Pixel ({col},{row}) -> Latitude: {lat}, Longitude: {lon}")
