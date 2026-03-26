import exifread

def ratio_to_float(ratio):
    return float(ratio.num) / float(ratio.den)

def dms_to_string(dms, ref):
    deg = ratio_to_float(dms[0])
    minutes = ratio_to_float(dms[1])
    seconds = ratio_to_float(dms[2])
    return f"{int(deg)}° {int(minutes)}′ {seconds:.2f}″ {ref}"

with open("DJI_0230.JPG", "rb") as f:
    tags = exifread.process_file(f)

lat = tags.get("GPS GPSLatitude")
lat_ref = tags.get("GPS GPSLatitudeRef")

lon = tags.get("GPS GPSLongitude")
lon_ref = tags.get("GPS GPSLongitudeRef")

alt = tags.get("GPS GPSAltitude")
alt_ref = tags.get("GPS GPSAltitudeRef")

if lat and lon:
    lat_str = dms_to_string(lat.values, lat_ref.values)
    lon_str = dms_to_string(lon.values, lon_ref.values)
    altitude = ratio_to_float(alt.values[0])

    print(lat_str)
    print(lon_str)
    print(f"Altitude : {altitude:.1f} m")
else:
    print("Aucune donnée GPS trouvée.")