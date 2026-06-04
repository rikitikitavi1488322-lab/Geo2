import clas

def detect_d(c1, c2, sp_sloy):
    """Ищет один самый близкий слой с учетом индивидуального порога этого слоя"""
    r1, g1, b1 = c2
    best_layer = None
    min_found_d2 = float('inf')

    for s in sp_sloy:
        r0, g0, b0 = s.rgb
        d2 = (r1 - r0)**2 + (g1 - g0)**2 + (b1 - b0)**2
        if d2 < min_found_d2:
            min_found_d2 = d2
            best_layer = s

    if best_layer and min_found_d2 < best_layer.max_d2:
        if isinstance(best_layer.sp_pix, set):
            best_layer.sp_pix.add(c1)
        else:
            best_layer.sp_pix.append(c1)
            
def detect_clas(c, rgb_color, sp_sloy):
    noviy_sloy = clas.Sloy(name=c, rgb=rgb_color, sp_pix=[], vozrast="???", description="")
    sp_sloy.append(noviy_sloy)

def create_custom_layer(name, rgb_color, sp_sloy, min_d2=850):
    """Создает новый пользовательский пустой слой"""
    noviy_sloy = clas.Sloy(name=name, rgb=rgb_color, sp_pix=[], vozrast="???", description="", max_d2=min_d2)
    sp_sloy.append(noviy_sloy)
    return noviy_sloy