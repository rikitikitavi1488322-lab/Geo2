import clas

def detect_d(c1, c2_lab, sp_sloy):
    """Ищет один самый близкий слой с учетом индивидуального порога этого слоя в LAB"""
    l1, a1, b1 = c2_lab
    best_layer = None
    min_found_d2 = float('inf')

    for s in sp_sloy:
        l0, a0, b0 = s.lab
        d2 = (l1 - l0)**2 + (a1 - a0)**2 + (b1 - b0)**2
        if d2 < min_found_d2:
            min_found_d2 = d2
            best_layer = s

    if best_layer and min_found_d2 < best_layer.max_d2:
        best_layer.sp_pix.add(c1)
            
def detect_clas(c, rgb_color, lab_color, sp_sloy):
    """Создает базовый слой, явно передавая и RGB (для UI) и LAB (для математики)"""
    noviy_sloy = clas.Sloy(name=c, rgb=rgb_color, lab=lab_color, sp_pix=set(), max_d2=200)
    sp_sloy.append(noviy_sloy)

def create_custom_layer(name, rgb_color, lab_color, sp_sloy, min_d2=200):
    """Создает новый пользовательский пустой слой"""
    noviy_sloy = clas.Sloy(name=name, rgb=rgb_color, lab=lab_color, sp_pix=set(), vozrast="???", description="", max_d2=min_d2)
    sp_sloy.append(noviy_sloy)
    return noviy_sloy