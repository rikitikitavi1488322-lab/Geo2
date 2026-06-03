class Sloy():
    def __init__(self, name, rgb, sp_pix, vozrast="???", description="", max_d2=850):
        self.name = name
        self.rgb = tuple(rgb)
        # Храним координаты как множество (set) кортежей для моментального поиска и удаления
        self.sp_pix = set(tuple(p) for p in sp_pix)  
        self.vozrast = vozrast
        self.description = description
        self.max_d2 = max_d2

    def to_dict(self):
        return {
            "name": self.name,
            "rgb": list(self.rgb),
            "sp_pix": list(self.sp_pix), # Для JSON конвертируем обратно в список
            "vozrast": self.vozrast,
            "description": self.description,
            "max_d2": self.max_d2
        }

    @classmethod
    def from_dict(cls, data):
        """Создает объект Sloy на основе словаря из JSON"""
        return cls(
            name=data["name"],
            rgb=data["rgb"],
            sp_pix=data["sp_pix"],
            vozrast=data.get("vozrast", "???"),
            description=data.get("description", ""),
            max_d2=data.get("max_d2", 850)
        )