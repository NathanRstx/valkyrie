import exifread
import math
import rasterio
from PIL import Image


class GeoImage:

    def __init__(self, tiff_path, dem_path):

        self.tiff_path = tiff_path
        self.dem_path = dem_path

        self.lat, self.lon, self.alt_drone, self.focale_mm = self._extract_exif()

        if None in [self.lat, self.lon, self.alt_drone, self.focale_mm]:
            raise ValueError("Métadonnées EXIF insuffisantes.")

        self.alt_sol = self._get_altitude_sol()

        self.alt_rel = self.alt_drone - self.alt_sol

        self.sensor_width_mm = 6.3
        self.sensor_height_mm = 4.7

        im = Image.open(self.tiff_path)
        self.img_width, self.img_height = im.size

        self.gsd_x = (self.alt_rel * self.sensor_width_mm) / (self.focale_mm * self.img_width) / 1000
        self.gsd_y = (self.alt_rel * self.sensor_height_mm) / (self.focale_mm * self.img_height) / 1000

        self.cx = self.img_width / 2
        self.cy = self.img_height / 2

    def _extract_exif(self):

        with open(self.tiff_path, 'rb') as f:
            tags = exifread.process_file(f)

        def dms_to_dd(dms):
            d = float(dms.values[0].num) / float(dms.values[0].den)
            m = float(dms.values[1].num) / float(dms.values[1].den)
            s = float(dms.values[2].num) / float(dms.values[2].den)
            return d + (m / 60.0) + (s / 3600.0)

        try:

            lat_tag = tags.get('GPS GPSLatitude')
            lat_ref_tag = tags.get('GPS GPSLatitudeRef')

            lon_tag = tags.get('GPS GPSLongitude')
            lon_ref_tag = tags.get('GPS GPSLongitudeRef')

            alt_tag = tags.get('GPS GPSAltitude')

            focale_tag = tags.get('EXIF FocalLength')

            if not all([lat_tag, lat_ref_tag, lon_tag, lon_ref_tag, alt_tag, focale_tag]):
                return None, None, None, None

            lat = dms_to_dd(lat_tag)
            if lat_ref_tag.printable != 'N':
                lat = -lat

            lon = dms_to_dd(lon_tag)
            if lon_ref_tag.printable != 'E':
                lon = -lon

            alt = float(alt_tag.values[0].num) / float(alt_tag.values[0].den)

            focale = float(focale_tag.values[0].num) / float(focale_tag.values[0].den)

            return lat, lon, alt, focale

        except Exception as e:
            print("Erreur lecture EXIF :", e)
            return None, None, None, None

    def _get_altitude_sol(self):

        try:
            with rasterio.open(self.dem_path) as dem:
                for val in dem.sample([(self.lon, self.lat)]):
                    return float(val[0])

        except Exception as e:
            print("Erreur lecture DEM :", e)

        return 0

    def pixel_to_gps(self, x, y):

        dx = x - self.cx
        dy = y - self.cy

        mx = dx * self.gsd_x
        my = -dy * self.gsd_y

        dlat = my / 111320
        cos_lat = math.cos(math.radians(self.lat))
        if abs(cos_lat) < 1e-6:
            raise ValueError("Latitude trop proche des pôles pour une conversion GPS locale fiable.")
        dlon = mx / (111320 * cos_lat)

        lat_p = self.lat + dlat
        lon_p = self.lon + dlon

        return lat_p, lon_p

    def gps_to_local(self, lat, lon):
        cos_lat = math.cos(math.radians(self.lat))
        if abs(cos_lat) < 1e-6:
            raise ValueError("Latitude trop proche des pôles pour une conversion GPS locale fiable.")

        x = (lon - self.lon) * 111320 * cos_lat
        y = (lat - self.lat) * 111320

        return x, y

    def compute_area(self, gps_points):

        if len(gps_points) < 3:
            return 0

        pts = [self.gps_to_local(lat, lon) for lat, lon in gps_points]

        area = 0
        n = len(pts)

        for i in range(n):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % n]
            area += x1 * y2 - x2 * y1

        return abs(area) / 2

import sys

if __name__ == "__main__":

    tiff = sys.argv[1]
    dem = sys.argv[2]
    command = sys.argv[3]

    geo = GeoImage(tiff, dem)

    if command == "pixel_to_gps":
        x = float(sys.argv[4])
        y = float(sys.argv[5])

        lat, lon = geo.pixel_to_gps(x, y)
        print(f"{lon},{lat}")

    elif command == "compute_area":
        gps_points = []
        for p in sys.argv[4:]:
            lat, lon = map(float, p.split(","))
            gps_points.append((lat, lon))

        area = geo.compute_area(gps_points)
        print(f"Aire: {area} m²")
