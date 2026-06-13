from PIL import Image, ImageFilter
import random
import math
import json
import os
import raspred
import clas


import georef
geo_system = georef.GeoReferencer()
control_points = []

import numpy as np
elevation_matrix = None

status_message = "Система готова"
karta = 'geo2.jpg'

sample_processed = None

# Настройки вычислений (изменяются через интерфейс)
k_clusters = 20      
blur_radius = 2     
min_d2 = 200        

slovar_pix = {}
slovar_pix_lab = {}
list_of_rgb = []
list_of_lab = []
sp_sloy = []

# Размеры изображения (будут перезаписаны при открытии)
x = 0
y = 0
pixels = None

def open_file(karta_input):
    global pixels, x, y, blur_radius, sample_processed
    sample = Image.open(karta_input)
    sample = sample.convert('RGB')
    
    if blur_radius > 0:
        sample = sample.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    
    pixels = sample.load()
    x, y = sample.size
    sample_processed = sample



def izv():
    print('Извлечение пикселей...')
    list_of_rgb.clear()
    list_of_lab.clear()
    slovar_pix.clear()
    slovar_pix_lab.clear()
    
    img_np = np.array(sample_processed)
    img_lab = rgb2lab(img_np)
    
    for px in range(x):
        for py in range(y):
            color = pixels[px, py]
            color_lab = tuple(img_lab[py, px])
            
            slovar_pix[(px, py)] = color  
            slovar_pix_lab[(px, py)] = color_lab
            list_of_rgb.append(color)
            list_of_lab.append(color_lab)

def run_kmeans(data, k=20, max_iters=10):
    print(f'Запуск K-Means кластеризации (K={k})...')
    if not data:
        return []
    centroids = random.sample(data, min(k, len(data)))
    
    for iteration in range(max_iters):
        global status_message
        status_message = f"Шаг 3/5: Кластеризация K-Means (Итерация {iteration+1}/{max_iters})..."
        
        clusters = [[] for _ in range(len(centroids))]
        sample_data = random.sample(data, min(5000, len(data)))
        
        for color in sample_data:
            l1, a1, b1 = color
            min_dist = float('inf')
            closest_idx = 0
            for idx, cent in enumerate(centroids):
                l2, a2, b2 = cent
                d2 = (l1 - l2)**2 + (a1 - a2)**2 + (b1 - b2)**2
                if d2 < min_dist:
                    min_dist = d2
                    closest_idx = idx
            clusters[closest_idx].append(color)
        
        new_centroids = []
        for idx, cluster in enumerate(clusters):
            if not cluster:
                new_centroids.append(centroids[idx])
                continue
            sum_l = sum(c[0] for c in cluster)
            sum_a = sum(c[1] for c in cluster)
            sum_b = sum(c[2] for c in cluster)
            cnt = len(cluster)
            new_centroids.append((sum_l/cnt, sum_a/cnt, sum_b/cnt))
            
        if centroids == new_centroids:
            break
        centroids = new_centroids
        
    return centroids

def filter_isolated_pixels():
    global sp_sloy, x, y
    print("Фильтрация изолированных пикселей...")
    for s in sp_sloy:
        filtered_pix = set()
        for pt in s.sp_pix:
            px, py = pt
            neighbors = 0
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    if (px + dx, py + dy) in s.sp_pix:
                        neighbors += 1
            if neighbors >= 2:
                filtered_pix.add(pt)
        s.sp_pix = filtered_pix


def rgb2lab(rgb_array):
    """ Полная замена skimage.color.rgb2lab для массивов (H, W, 3) """
    arr = np.array(rgb_array, dtype=np.float64) / 255.0
    
    # sRGB в Linear RGB
    mask = arr > 0.04045
    arr[mask] = ((arr[mask] + 0.055) / 1.055) ** 2.4
    arr[~mask] = arr[~mask] / 12.92
    
    # Linear RGB в XYZ (стандарт D65)
    X = arr[..., 0] * 0.4124564 + arr[..., 1] * 0.3575761 + arr[..., 2] * 0.1804375
    Y = arr[..., 0] * 0.2126729 + arr[..., 1] * 0.7151522 + arr[..., 2] * 0.0721750
    Z = arr[..., 0] * 0.0193339 + arr[..., 1] * 0.1191920 + arr[..., 2] * 0.9503041
    
    # Нормализация для D65
    X /= 0.95047
    Z /= 1.08883
    
    # Функция f(t) для перехода к LAB
    def f(t):
        res = np.empty_like(t)
        m = t > 0.008856
        res[m] = t[m] ** (1.0 / 3.0)
        res[~m] = 7.787 * t[~m] + 16.0 / 116.0
        return res
        
    fx = f(X)
    fy = f(Y)
    fz = f(Z)
    
    L = 116.0 * fy - 16.0
    a = 500.0 * (fx - fy)
    b = 200.0 * (fy - fz)
    
    return np.stack([L, a, b], axis=-1)

def lab2rgb(lab_matrix):
    """ Полная замена skimage.color.lab2rgb """
    lab = np.array(lab_matrix, dtype=np.float64)
    L = lab[..., 0]
    a = lab[..., 1]
    b = lab[..., 2]
    
    fy = (L + 16.0) / 116.0
    fx = a / 500.0 + fy
    fz = fy - b / 200.0
    
    def f_inv(t):
        res = np.empty_like(t)
        m = t > 0.206897
        res[m] = t[m] ** 3
        res[~m] = (t[~m] - 16.0 / 116.0) / 7.787
        return res
        
    X = f_inv(fx) * 0.95047
    Y = f_inv(fy) * 1.00000
    Z = f_inv(fz) * 1.08883
    
    # XYZ в Linear RGB
    r = X *  3.2404542 + Y * -1.5371385 + Z * -0.4985314
    g = X * -0.9692660 + Y *  1.8760108 + Z *  0.0415560
    b = X *  0.0556434 + Y * -0.2040259 + Z *  1.0572252
    
    rgb = np.stack([r, g, b], axis=-1)
    rgb = np.clip(rgb, 0, 1)
    
    # Linear RGB в sRGB
    m = rgb > 0.0031308
    rgb[m] = 1.055 * (rgb[m] ** (1.0 / 2.4)) - 0.055
    rgb[~m] = rgb[~m] * 12.92
    
    return rgb

def lab_to_rgb_tuple(lab_color):
    # lab2rgb ожидает массив, поэтому оборачиваем в список списков
    rgb_float = lab2rgb([[lab_color]])[0][0]  # Возвращает значения от 0.0 до 1.0
    return tuple(int(c * 255) for c in rgb_float)

def add_new_empty_layer(name, rgb_color):
    global sp_sloy, min_d2
    for layer in sp_sloy:
        if str(layer.name) == str(name):
            return False, "Слой с таким именем уже существует!"


    import numpy as np
    rgb_norm = np.array([[[rgb_color[0] / 255.0, rgb_color[1] / 255.0, rgb_color[2] / 255.0]]])
    lab_color = tuple(rgb2lab(rgb_norm)[0][0])

    raspred.create_custom_layer(name, rgb_color, lab_color, sp_sloy, min_d2)
    return True, "Слой успешно создан"

def main_all(karta_input):
    global status_message, sp_sloy, k_clusters, min_d2, karta # ДОБАВЛЕНО: karta в global
    
    status_message = "Шаг 1/5: Загрузка графического файла..."
    karta = karta_input # ДОБАВЛЕНО: сохраняем актуальный путь к карте
    open_file(karta_input)
    
    status_message = "Шаг 2/5: Анализ цветовой матрицы..."
    izv()
    
    status_message = "Шаг 3/5: Вычисление базовых классов (K-Means)..."
    unique_colors = list(set(list_of_lab))
    centroids = run_kmeans(unique_colors, k=k_clusters, max_iters=8)
    
    status_message = "Шаг 4/5: Генерация векторов слоев..."
    sp_sloy.clear()
    for idx, lab_color in enumerate(centroids):
        
        rgb_color = lab_to_rgb_tuple(lab_color)
        raspred.detect_clas(idx + 1, rgb_color, lab_color, sp_sloy)
        sp_sloy[-1].max_d2 = min_d2
        
    print(f'Создано базовых слоев: {len(sp_sloy)}')
    
    status_message = "Шаг 5/5: Распределение пикселей по дистанции..."
    for c1, c2_lab in slovar_pix_lab.items():
        raspred.detect_d(c1, c2_lab, sp_sloy)
        
    status_message = "Пост-обработка: Очистка геометрии от шума..."
    filter_isolated_pixels()
    
    status_message = "Система готова"


def save_project(project_name="project_save.json"):
    global karta, sp_sloy, control_points
    project_data = {
        "karta": karta,
        "control_points": control_points,
        "layers": [layer.to_dict() for layer in sp_sloy]
    }
    with open(project_name, "w", encoding="utf-8") as f:
        json.dump(project_data, f, ensure_ascii=False, indent=4)
    print("Проект успешно сохранен!")
    return True # ДОБАВЛЕНО: чтобы интерфейс Kivy понимал, что сохранение прошло успешно


def load_project(project_name="project_save.json"):
    global karta, sp_sloy, control_points # ИСПРАВЛЕНО: добавлен control_points в список global
    if not os.path.exists(project_name):
        print(f"Файл проекта {project_name} не найден!")
        return False
        
    print(f"Загрузка проекта {project_name}...")
    with open(project_name, "r", encoding="utf-8") as f:
        project_data = json.load(f)
        
    karta = project_data["karta"]
    open_file(karta)
    
    # Теперь это корректно перезапишет глобальную переменную
    control_points = project_data.get("control_points", [])
    if len(control_points) >= 3:
        geo_system.calibrate(control_points)
    
    sp_sloy.clear()
    for layer_dict in project_data["layers"]:
        sp_sloy.append(clas.Sloy.from_dict(layer_dict))
    print(f"Успешно загружено слоев: {len(sp_sloy)}")
    return True
    
    

def compute_all_elevations(hgt_folder="dem_data"):
    """
    Высокооптимизированный расчет высот для каждого пикселя карты.
    Использует meshgrid из numpy для мгновенного вычисления.
    """
    global elevation_matrix, x, y, geo_system
    
    if not geo_system or not geo_system.is_calibrated:
        print("Ошибка: Система координат не откалибрована!")
        return False

    print("Запуск глобального расчета рельефа...")
    
    # 1. Извлекаем коэффициенты аффинного преобразования из вашего georef.py
    A, B, C = geo_system.trans_matrix['lat']
    D, E, F = geo_system.trans_matrix['lon']
    
    # 2. Создаем сетку координат пикселей (векторизация)
    px_indices = np.arange(x)
    py_indices = np.arange(y)
    PX, PY = np.meshgrid(px_indices, py_indices, indexing='ij')
    
    # 3. Мгновенно вычисляем Lat и Lon для каждого пикселя матрицы
    LATS = A * PX + B * PY + C
    LONS = D * PX + E * PY + F
    
    # Инициализируем итоговую матрицу высот (тип int16 экономит память)
    elevation_matrix = np.zeros((x, y), dtype=np.int16)
    
    # 4. Находим, в какие географические квадраты (плитки) попадает карта
    lat_floors = np.floor(LATS).astype(int)
    lon_floors = np.floor(LONS).astype(int)
    unique_tiles = set(zip(lat_floors.ravel(), lon_floors.ravel()))
    
    # 5. Обрабатываем каждую необходимую плитку .hgt
    for lat_floor, lon_floor in unique_tiles:
        lat_char = 'N' if lat_floor >= 0 else 'S'
        lon_char = 'E' if lon_floor >= 0 else 'W'
        filename = f"{lat_char}{abs(lat_floor):02d}{lon_char}{abs(lon_floor):03d}.hgt"
        filepath = os.path.join(hgt_folder, filename)
        
        # Маска для пикселей, которые относятся к текущему файлу .hgt
        tile_mask = (lat_floors == lat_floor) & (lon_floors == lon_floor)
        if not np.any(tile_mask):
            continue
            
        if os.path.exists(filepath):
            # Читаем файл матрицы высот напрямую в массив numpy за пару миллисекунд
            # '>i2' означает Big-Endian 16-bit signed integer (стандарт SRTM)
            hgt_grid = np.fromfile(filepath, dtype='>i2').reshape((1201, 1201))
            
            # Считаем локальное смещение внутри плитки (от 0.0 до 1.0)
            d_lats = LATS[tile_mask] - lat_floor
            d_lons = LONS[tile_mask] - lon_floor
            
            # Переводим в индексы матрицы матрицы SRTM (1201x1201)
            rows = ((1.0 - d_lats) * 1200).astype(int)
            cols = (d_lons * 1200).astype(int)
            
            # Защита от выхода за границы индексов
            rows = np.clip(rows, 0, 1200)
            cols = np.clip(cols, 0, 1200)
            
            # Вытаскиваем высоты для группы пикселей
            heights = hgt_grid[rows, cols]
            # -32768 — стандартный флаг отсутствия данных в SRTM (например, море), меняем на 0
            heights[heights == -32768] = 0
            
            # Записываем высоты обратно в глобальную матрицу
            elevation_matrix[tile_mask] = heights
            print(f"Плитка {filename} успешно наложена на карту.")
        else:
            print(f"Внимание: Файл {filename} отсутствует. Высоты этого сектора сброшены в 0.")
            elevation_matrix[tile_mask] = 0
            
    print("Глобальная матрица высот успешно построена!")
    return True
    
if __name__ == "__main__":

    from interface import MyApp

    MyApp().run()