# georef.py
import numpy as np

class GeoReferencer:
    def __init__(self):
        # Коэффициенты аффинного преобразования
        self.trans_matrix = None  # Из пикселей в географию
        self.inv_matrix = None    # Из географии в пиксели
        self.is_calibrated = False

    def calibrate(self, control_points):
        """
        Калибровка по опорным точкам.
        control_points: список словарей/кортежей вида:
        [
            {"pixel": (x1, y1), "geo": (lat1, lon1)},
            {"pixel": (x2, y2), "geo": (lat2, lon2)},
            {"pixel": (x3, y3), "geo": (lat3, lon3)},
        ]
        Нужно минимум 3 точки. Чем больше точек, тем точнее расчет (МНК).
        """
        if len(control_points) < 3:
            return False, "Необходимо минимум 3 опорные точки для аффинного преобразования."

        # Формируем матрицы для решения системы уравнений:
        # Geo_X = A*Pixel_X + B*Pixel_Y + C
        # Geo_Y = D*Pixel_X + E*Pixel_Y + F
        
        A_mat = []
        B_lon = []
        B_lat = []

        for pt in control_points:
            px, py = pt["pixel"]
            lat, lon = pt["geo"]
            A_mat.append([px, py, 1])
            B_lat.append(lat)
            B_lon.append(lon)

        A_mat = np.array(A_mat)
        
        # Решаем метод наименьших квадратов (псевдообратная матрица)
        try:
            # Коэффициенты для широты (Lat)
            coef_lat, _, _, _ = np.linalg.lstsq(A_mat, B_lat, rcond=None)
            # Коэффициенты для долготы (Lon)
            coef_lon, _, _, _ = np.linalg.lstsq(A_mat, B_lon, rcond=None)
            
            # Сохраняем матрицу преобразования вперед
            self.trans_matrix = {
                'lat': coef_lat, # [A, B, C]
                'lon': coef_lon  # [D, E, F]
            }
            
            # Строим обратную матрицу преобразования (из Гео в Пиксели)
            # Для простоты вычисляем ее аналогично через МНК, меняя местами X и Y
            A_geo = []
            B_px = []
            B_py = []
            for pt in control_points:
                px, py = pt["pixel"]
                lat, lon = pt["geo"]
                A_geo.append([lat, lon, 1])
                B_px.append(px)
                B_py.append(py)
                
            A_geo = np.array(A_geo)
            coef_px, _, _, _ = np.linalg.lstsq(A_geo, B_px, rcond=None)
            coef_py, _, _, _ = np.linalg.lstsq(A_geo, B_py, rcond=None)
            
            self.inv_matrix = {
                'px': coef_px,
                'py': coef_py
            }

            self.is_calibrated = True
            return True, "Привязка успешно выполнена!"
        except Exception as e:
            return False, f"Ошибка вычислений: {str(e)}"

    def pixel_to_geo(self, px, py):
        """Конвертация: Пиксель карты -> (Lat, Lon)"""
        if not self.is_calibrated:
            return None
        
        A, B, C = self.trans_matrix['lat']
        D, E, F = self.trans_matrix['lon']
        
        lat = A * px + B * py + C
        lon = D * px + E * py + F
        return lat, lon

    def geo_to_pixel(self, lat, lon):
        """Конвертация: (Lat, Lon) -> Пиксель карты"""
        if not self.is_calibrated:
            return None
            
        A, B, C = self.inv_matrix['px']
        D, E, F = self.inv_matrix['py']
        
        px = A * lat + B * lon + C
        py = D * lat + E * lon + F
        return int(round(px)), int(round(py))