class Sloy():
    def __init__(self, name, rgb, lab, sp_pix, vozrast="???", description="", max_d2=200):
        self.name = name
        self.rgb = tuple(rgb)
        self.lab = tuple(lab)
        # Храним координаты как множество (set) кортежей для моментального поиска и удаления
        self.sp_pix = set(tuple(p) for p in sp_pix)  
        self.vozrast = vozrast
        self.description = description
        self.max_d2 = max_d2

    def to_dict(self):
        return {
            "name": self.name,
            "rgb": list(self.rgb),
            'lab': list(self.lab),  # Переименовали в чистый lab для понятности
            "sp_pix": list(self.sp_pix), 
            "vozrast": self.vozrast,
            "description": self.description,
            "max_d2": self.max_d2
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data["name"],
            rgb=data["rgb"],
            lab=data.get("lab", data.get("rgb_lab")) or [0, 0, 0], # Поддержка обоих ключей для совместимости
            sp_pix=data["sp_pix"],
            vozrast=data.get("vozrast", "???"),
            description=data.get("description", ""),
            max_d2=data.get("max_d2", 200)
        )