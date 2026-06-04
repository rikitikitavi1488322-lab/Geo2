from PIL import Image, ImageFilter
import random
import math
import json
import os
import raspred
import clas

status_message = "Система готова"
karta = 'geo2.jpg'

# Настройки вычислений (изменяются через интерфейс)
k_clusters = 20      
blur_radius = 2     
min_d2 = 850        

slovar_pix = {}
list_of_rgb = []
sp_sloy = []

# Размеры изображения (будут перезаписаны при открытии)
x = 0
y = 0
pixels = None

def open_file(karta_input):
    global pixels, x, y, blur_radius
    sample = Image.open(karta_input)
    sample = sample.convert('RGB')
    
    if blur_radius > 0:
        sample = sample.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    
    pixels = sample.load()
    x, y = sample.size

def izv():
    print('Извлечение пикселей...')
    list_of_rgb.clear()
    slovar_pix.clear()
    for px in range(x):
        for py in range(y):
            color = pixels[px, py]
            slovar_pix[(px, py)] = color  
            list_of_rgb.append(color)

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
            r1, g1, b1 = color
            min_dist = float('inf')
            closest_idx = 0
            for idx, cent in enumerate(centroids):
                r2, g2, b2 = cent
                d2 = (r1 - r2)**2 + (g1 - g2)**2 + (b1 - b2)**2
                if d2 < min_dist:
                    min_dist = d2
                    closest_idx = idx
            clusters[closest_idx].append(color)
        
        new_centroids = []
        for idx, cluster in enumerate(clusters):
            if not cluster:
                new_centroids.append(centroids[idx])
                continue
            sum_r = sum(c[0] for c in cluster)
            sum_g = sum(c[1] for c in cluster)
            sum_b = sum(c[2] for c in cluster)
            cnt = len(cluster)
            new_centroids.append((int(sum_r/cnt), int(sum_g/cnt), int(sum_b/cnt)))
            
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

def save_project(project_name="project_save.json"):
    global karta, sp_sloy
    project_data = {
        "karta": karta,
        "layers": [layer.to_dict() for layer in sp_sloy]
    }
    with open(project_name, "w", encoding="utf-8") as f:
        json.dump(project_data, f, ensure_ascii=False, indent=4)
    print("Проект успешно сохранен!")

def load_project(project_name="project_save.json"):
    global karta, sp_sloy
    if not os.path.exists(project_name):
        print(f"Файл проекта {project_name} не найден!")
        return False
        
    print(f"Загрузка проекта {project_name}...")
    with open(project_name, "r", encoding="utf-8") as f:
        project_data = json.load(f)
        
    karta = project_data["karta"]
    open_file(karta)
    
    sp_sloy.clear()
    for layer_dict in project_data["layers"]:
        sp_sloy.append(clas.Sloy.from_dict(layer_dict))
    print(f"Успешно загружено слоев: {len(sp_sloy)}")
    return True

def add_new_empty_layer(name, rgb_color):
    global sp_sloy, min_d2
    for layer in sp_sloy:
        if str(layer.name) == str(name):
            return False, "Слой с таким именем уже существует!"
            
    raspred.create_custom_layer(name, rgb_color, sp_sloy, min_d2)
    return True, "Слой успешно создан"

def main_all(karta_input):
    global status_message, sp_sloy, k_clusters, min_d2
    
    status_message = "Шаг 1/5: Загрузка графического файла..."
    open_file(karta_input)
    
    status_message = "Шаг 2/5: Анализ цветовой матрицы..."
    izv()
    
    status_message = "Шаг 3/5: Вычисление базовых классов (K-Means)..."
    unique_colors = list(set(list_of_rgb))
    centroids = run_kmeans(unique_colors, k=k_clusters, max_iters=8)
    
    status_message = "Шаг 4/5: Генерация векторов слоев..."
    sp_sloy.clear()
    for idx, color in enumerate(centroids):
        raspred.detect_clas(idx + 1, color, sp_sloy)
        sp_sloy[-1].max_d2 = min_d2
        
    print(f'Создано базовых слоев: {len(sp_sloy)}')
    
    status_message = "Шаг 5/5: Распределение пикселей по дистанции..."
    for c1, c2 in slovar_pix.items():
        raspred.detect_d(c1, c2, sp_sloy)
        
    status_message = "Пост-обработка: Очистка геометрии от шума..."
    filter_isolated_pixels()
    
    status_message = "Система готова"