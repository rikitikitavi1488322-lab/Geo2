from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.dropdown import DropDown
from kivy.uix.scrollview import ScrollView 
from kivy.uix.scatterlayout import ScatterLayout
from kivy.uix.slider import Slider
from kivy.graphics import Rectangle, Color, Line
from kivy.graphics.texture import Texture
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.clock import Clock

import threading
import main
import clas

width = Window.width
height = Window.height

Window.size = (width, height)
Window.clearcolor = (40/255, 43/255, 48/255, 1) # Темный красивый фон ГИС
Window.title = "geotelo"

karta = 'geo2.jpg'

class CustomMapScene(ScatterLayout):
    def on_touch_down(self, touch):
        app = App.get_running_app()
        if app.tool_mode in ['draw', 'erase']:
            # Если включен инструмент редактирования, передаем тач слоям
            for child in reversed(self.children):
                if isinstance(child, FastPixelLayer):
                    if child.layer_name == app.selected_layer_key:
                        if child.on_touch_down(touch):
                            return True
            return super().on_touch_down(touch)
            
        if self.collide_point(*touch.pos):
            if touch.is_mouse_scrolling:
                if touch.button == 'scrolldown':
                    if self.scale > 0.1:
                        self.scale -= 0.05
                elif touch.button == 'scrollup':
                    if self.scale < 10:
                        self.scale += 0.05
                return True
        return super().on_touch_down(touch)


class FastPixelLayer(Widget):
    def __init__(self, layer_name, layer_data, tex_w, tex_h, **kwargs):
        super().__init__(**kwargs)
        self.layer_name = layer_name
        self.layer_data = layer_data
        self.tex_w = tex_w
        self.tex_h = tex_h
        self.layer_color = layer_data.rgb
        
        self.texture = Texture.create(size=(self.tex_w, self.tex_h), colorfmt='rgba')
        self.texture.mag_filter = 'nearest'
        self.texture.min_filter = 'nearest'
        
        self.buffer = bytearray([0, 0, 0, 0] * (self.tex_w * self.tex_h))
        self.refresh_buffer_from_layer()
        
        with self.canvas:
            Color(1, 1, 1, 1)
            self.rect = Rectangle(texture=self.texture, pos=self.pos, size=(self.tex_w, self.tex_h))
            
        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        self.rect.pos = self.pos

    def refresh_buffer_from_layer(self):
        self.buffer = bytearray([0, 0, 0, 0] * (self.tex_w * self.tex_h))
        r, g, b = self.layer_color
        for (px, py) in self.layer_data.sp_pix:
            kivy_y = self.tex_h - 1 - py
            idx = (kivy_y * self.tex_w + px) * 4
            self.buffer[idx] = r
            self.buffer[idx+1] = g
            self.buffer[idx+2] = b
            self.buffer[idx+3] = 255
        self.texture.blit_buffer(self.buffer, colorfmt='rgba', bufferfmt='ubyte')

    def on_touch_down(self, touch):
        app = App.get_running_app()
        if app.tool_mode in ['draw', 'erase'] and app.selected_layer_key == self.layer_name:
            if self.collide_point(*touch.pos):
                touch.grab(self)
                self.paint_at_touch(touch)
                return True
        return False

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            self.paint_at_touch(touch)
            return True
        return False

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            return True
        return False

    def paint_at_touch(self, touch):
        app = App.get_running_app()
        mode = app.tool_mode
        radius = app.brush_radius
        target_layer_data = self.layer_data
        
        # Перевод экранных координат в локальные координаты текстуры
        local_x, local_y = self.to_local(*touch.pos)
        
        cx = int(local_x)
        cy = self.tex_h - 1 - int(local_y)
        
        changed = False

        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if dx*dx + dy*dy <= radius*radius:
                    px = cx + dx
                    py = cy + dy
                    
                    if 0 <= px < self.tex_w and 0 <= py < self.tex_h:
                        pt = (px, py)
                        kivy_y = self.tex_h - 1 - py
                        idx = (kivy_y * self.tex_w + px) * 4
                        
                        if mode == 'draw':
                            if pt not in target_layer_data.sp_pix:
                                target_layer_data.sp_pix.add(pt)
                                self.buffer[idx] = self.layer_color[0]
                                self.buffer[idx+1] = self.layer_color[1]
                                self.buffer[idx+2] = self.layer_color[2]
                                self.buffer[idx+3] = 255
                                changed = True
                                
                        elif mode == 'erase':
                            if pt in target_layer_data.sp_pix:
                                target_layer_data.sp_pix.remove(pt)
                                self.buffer[idx:idx+4] = [0, 0, 0, 0]
                                changed = True

        if changed:
            self.texture.blit_buffer(self.buffer, colorfmt='rgba', bufferfmt='ubyte')
            self.canvas.ask_update()


class MyApp(App):
    def __init__(self):
        super().__init__()
        self.load = False
        self.tool_mode = 'view'
        self.selected_layer_key = None
        self.brush_radius = 5
        
        self.menu_btn = Button(text='Меню', size_hint_x=0.57)
        self.tools_menu_btn = Button(text='Режим', size_hint_x=0.33)
        self.exit_btn = Button(text='x', size_hint_x=0.1)
        
        self.exit_btn.bind(on_press=self.stop)
        self.active_layers = {}

    def popup_add_layer(self):
        if not main.x or not main.y:
            self.status_bar.text = "Ошибка: Сначала загрузите карту или проект"
            return

        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        self.layer_name_input = TextInput(hint_text="Имя слоя (например: Пески, Известняки)", multiline=False, size_hint_y=None, height='40dp')
        
        color_layout = BoxLayout(orientation='horizontal', spacing=5, size_hint_y=None, height='40dp')
        self.r_in = TextInput(hint_text="R (0-255)", text="255", multiline=False)
        self.g_in = TextInput(hint_text="G (0-255)", text="0", multiline=False)
        self.b_in = TextInput(hint_text="B (0-255)", text="0", multiline=False)
        color_layout.add_widget(self.r_in)
        color_layout.add_widget(self.g_in)
        color_layout.add_widget(self.b_in)
        
        btn_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height='45dp')
        btn_create = Button(text="Создать", background_color=(0, 0.6, 0.9, 1))
        btn_cancel = Button(text="Отмена")
        btn_layout.add_widget(btn_create)
        btn_layout.add_widget(btn_cancel)
        
        content.add_widget(Label(text="Параметры нового слоя:", size_hint_y=None, height='25dp'))
        content.add_widget(self.layer_name_input)
        content.add_widget(Label(text="Цвет слоя (RGB):", size_hint_y=None, height='25dp'))
        content.add_widget(color_layout)
        content.add_widget(btn_layout)
        
        self.add_layer_popup = Popup(title='Добавление нового слоя ГИС', content=content, size_hint=(None, None), size=('360dp', '260dp'), auto_dismiss=False)
        
        btn_create.bind(on_release=self.process_create_layer)
        btn_cancel.bind(on_release=self.add_layer_popup.dismiss)
        self.add_layer_popup.open()

    def process_create_layer(self, instance):
        name = self.layer_name_input.text.strip()
        if not name:
            self.status_bar.text = "Ошибка: Имя слоя не может быть пустым"
            self.add_layer_popup.dismiss()
            return
            
        try:
            r = max(0, min(255, int(self.r_in.text)))
            g = max(0, min(255, int(self.g_in.text)))
            b = max(0, min(255, int(self.b_in.text)))
            rgb = (r, g, b)
        except ValueError:
            self.status_bar.text = "Ошибка: Некорректные значения цвета RGB"
            self.add_layer_popup.dismiss()
            return

        success, message = main.add_new_empty_layer(name, rgb)
        self.status_bar.text = message
        
        if success:
            self.visual()
            
        self.add_layer_popup.dismiss()

    def menu_select_handler(self, instance, text):
        if text == 'unite':
            self.unite_layer()
        elif text == 'add_layer':
            self.popup_add_layer()
        elif text == 'новый расчет':
            self.proc_start()
        elif text == 'выбрать файл':
            self.print_file()
        elif text == 'сохранить':
            self.save_current_project()
        elif text == 'загрузить':
            self.load_existing_project()
        elif text == 'настройки':
            self.open_settings_popup()

    def tools_select_handler(self, instance, text):
        if text == 'rejim_prosmotra':
            self.tool_mode = 'view'
            self.tools_menu_btn.text = 'Навигация'
        elif text == 'rejim_karandasha':
            if self.selected_layer_key is None:
                self.status_bar.text = "Внимание: Сначала выберите активный слой справа"
                return
            self.tool_mode = 'draw'
            self.tools_menu_btn.text = f"Карандаш (Слой: {self.selected_layer_key})"
        elif text == 'rejim_lastika':
            if self.selected_layer_key is None:
                self.status_bar.text = "Внимание: Сначала выберите активный слой справа"
                return
            self.tool_mode = 'erase'
            self.tools_menu_btn.text = f"Ластик (Слой: {self.selected_layer_key})"

    def open_settings_popup(self):
        content = BoxLayout(orientation='vertical', spacing=12, padding=15)
        
        content.add_widget(Label(text="Инструменты рисования", size_hint_y=None, height='25dp', font_size='15sp', color=(0, 1, 0.8, 1)))
        
        brush_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height='40dp', spacing=10)
        self.lbl_brush = Label(text=f"Кисть/Ластик: {self.brush_radius} px", size_hint_x=0.4, halign='left')
        sld_brush = Slider(min=1, max=50, value=self.brush_radius, step=1, size_hint_x=0.6)
        sld_brush.bind(value=lambda inst, val: setattr(self, 'brush_radius', int(val)) or setattr(self.lbl_brush, 'text', f"Кисть/Ластик: {int(val)} px"))
        brush_layout.add_widget(self.lbl_brush)
        brush_layout.add_widget(sld_brush)
        content.add_widget(brush_layout)
        
        content.add_widget(Label(text="Параметры первичной обработки (K-Means и PIL)", size_hint_y=None, height='25dp', font_size='15sp', color=(0, 1, 0.8, 1)))
        
        k_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height='40dp', spacing=10)
        lbl_k = Label(text=f"Кол-во слоев (K): {main.k_clusters}", size_hint_x=0.4)
        sld_k = Slider(min=5, max=40, value=main.k_clusters, step=1, size_hint_x=0.6)
        def change_k(inst, val):
            main.k_clusters = int(val)
            lbl_k.text = f"Кол-во слоев (K): {main.k_clusters}"
        sld_k.bind(value=change_k)
        k_layout.add_widget(lbl_k)
        k_layout.add_widget(sld_k)
        content.add_widget(k_layout)
        
        blur_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height='40dp', spacing=10)
        lbl_blur = Label(text=f"Размытие шума: {main.blur_radius} px", size_hint_x=0.4)
        sld_blur = Slider(min=0, max=5, value=main.blur_radius, step=1, size_hint_x=0.6)
        def change_blur(inst, val):
            main.blur_radius = int(val)
            lbl_blur.text = f"Размытие шума: {main.blur_radius} px"
        sld_blur.bind(value=change_blur)
        blur_layout.add_widget(lbl_blur)
        blur_layout.add_widget(sld_blur)
        content.add_widget(blur_layout)
        
        d2_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height='40dp', spacing=10)
        lbl_d2 = Label(text=f"Порог цвета (d²): {main.min_d2}", size_hint_x=0.4)
        sld_d2 = Slider(min=200, max=3000, value=main.min_d2, step=50, size_hint_x=0.6)
        def change_d2(inst, val):
            main.min_d2 = int(val)
            lbl_d2.text = f"Порог цвета (d²): {main.min_d2}"
        sld_d2.bind(value=change_d2)
        d2_layout.add_widget(lbl_d2)
        d2_layout.add_widget(sld_d2)
        content.add_widget(d2_layout)
        
        close_btn = Button(text="Применить настройки", size_hint_y=None, height='45dp', background_color=(0, 0.7, 0.4, 1))
        content.add_widget(close_btn)
        
        settings_popup = Popup(title='Настройки алгоритмов ядра ГИС', content=content, size_hint=(0.85, 0.65), auto_dismiss=True)
        close_btn.bind(on_release=settings_popup.dismiss)
        
        def on_dismiss_callback(instance):
            self.status_bar.text = f"Параметры изменены. K={main.k_clusters}, Blur={main.blur_radius}px, d²={main.min_d2}"
        settings_popup.bind(on_dismiss=on_dismiss_callback)
        
        settings_popup.open()

    def build(self):
        main_layout = BoxLayout(orientation='vertical')
        
        contral_panel = BoxLayout(orientation='horizontal', size_hint_y=0.06, spacing=5)
        contral_panel.add_widget(self.menu_btn)
        contral_panel.add_widget(self.tools_menu_btn)
        contral_panel.add_widget(self.exit_btn)
        main_layout.add_widget(contral_panel)
        
        dropdown_menu = DropDown()
        
        add_layer_btn = Button(text='Добавить новый слой', size_hint_y=None, height='50dp')
        add_layer_btn.bind(on_release=lambda instance: dropdown_menu.select('add_layer'))
        unite_menu_btn = Button(text='Объединить слои', size_hint_y=None, height='50dp')
        unite_menu_btn.bind(on_release=lambda instance: dropdown_menu.select('unite'))
        start_btn = Button(text='Новый расчет', size_hint_y=None, height='50dp')
        start_btn.bind(on_release=lambda instance: dropdown_menu.select('новый расчет'))
        file_btn = Button(text='Выбрать файл карты', size_hint_y=None, height='50dp')
        file_btn.bind(on_release=lambda instance: dropdown_menu.select('выбрать файл'))
        save_btn = Button(text='Сохранить проект', size_hint_y=None, height='50dp')
        save_btn.bind(on_release=lambda instance: dropdown_menu.select('сохранить'))
        load_btn = Button(text='Загрузить проект', size_hint_y=None, height='50dp')
        load_btn.bind(on_release=lambda instance: dropdown_menu.select('загрузить'))
        settings_btn = Button(text='Настройки ГИС', size_hint_y=None, height='50dp')
        settings_btn.bind(on_release=lambda instance: dropdown_menu.select('настройки'))
        
        dropdown_menu.add_widget(add_layer_btn)
        dropdown_menu.add_widget(unite_menu_btn)
        dropdown_menu.add_widget(start_btn)
        dropdown_menu.add_widget(file_btn)
        dropdown_menu.add_widget(save_btn)
        dropdown_menu.add_widget(load_btn)
        dropdown_menu.add_widget(settings_btn)
        
        self.menu_btn.bind(on_release=dropdown_menu.open)
        dropdown_menu.bind(on_select=self.menu_select_handler)
        
        self.dropdown_tools = DropDown()
        mode_view = Button(text='Навигация', size_hint_y=None, height='50dp')
        mode_view.bind(on_release=lambda instance: self.dropdown_tools.select('rejim_prosmotra'))
        mode_draw = Button(text='Карандаш', size_hint_y=None, height='50dp')
        mode_draw.bind(on_release=lambda instance: self.dropdown_tools.select('rejim_karandasha'))
        mode_erase = Button(text='Ластик', size_hint_y=None, height='50dp')
        mode_erase.bind(on_release=lambda instance: self.dropdown_tools.select('rejim_lastika'))
        
        self.dropdown_tools.add_widget(mode_view)
        self.dropdown_tools.add_widget(mode_draw)
        self.dropdown_tools.add_widget(mode_erase)
        self.tools_menu_btn.bind(on_release=self.dropdown_tools.open)
        self.dropdown_tools.bind(on_select=self.tools_select_handler)
        
        self.status_bar = Label(text="Ожидание действий. Откройте Меню.", size_hint_y=0.04, color=(0, 1, 0.7, 1))
        with self.status_bar.canvas.before:
            Color(45/255, 50/255, 55/255, 1)
            self.status_bg = Rectangle(pos=self.status_bar.pos, size=self.status_bar.size)
            
        def resize_status_bg(instance, value):
            self.status_bg.pos = instance.pos
            self.status_bg.size = instance.size
        self.status_bar.bind(pos=resize_status_bg, size=resize_status_bg)
        main_layout.add_widget(self.status_bar)
        
        workspace = BoxLayout(orientation='horizontal', size_hint_y=0.90)
        self.map_scene = CustomMapScene(size_hint_x=0.7, do_rotation=False, auto_bring_to_front=False)
        workspace.add_widget(self.map_scene)
        
        scroll_container = ScrollView(size_hint_x=0.3)
        self.list_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=5, padding=5)
        self.list_layout.bind(minimum_height=self.list_layout.setter('height'))
        
        scroll_container.add_widget(self.list_layout)
        workspace.add_widget(scroll_container)
        main_layout.add_widget(workspace)

        return main_layout

    def proc_start(self):
        self.status_bar.text = "Запуск вычислительного потока ядра..."
        threading.Thread(target=self.bg_calculation).start()
        Clock.schedule_interval(self.update_status, 0.2)

    def bg_calculation(self):
        main.main_all(karta)
        self.load = True

    def update_status(self, dt):
        self.status_bar.text = main.status_message
        if self.load:
            self.visual()
            self.load = False
            return False

    def visual(self):
        self.map_scene.clear_widgets()
        self.list_layout.clear_widgets()
        self.active_layers.clear()

        # Базовая растровая карта
        from kivy.uix.image import Image as KivyImage
        img = KivyImage(source=karta, size_hint=(None, None), size=(main.x, main.y))
        self.map_scene.add_widget(img)

        # Отрисовка слоев геометрии
        for s in main.sp_sloy:
            layer_widget = FastPixelLayer(layer_name=str(s.name), layer_data=s, tex_w=main.x, tex_h=main.y, size_hint=(None, None), size=(main.x, main.y))
            self.map_scene.add_widget(layer_widget)
            self.active_layers[str(s.name)] = layer_widget

            # Правая панель управления слоями
            layer_box = BoxLayout(orientation='horizontal', size_hint_y=None, height='45dp', spacing=5)
            
            btn_select = ToggleButton(text=f"Слой {s.name}", group='layers', size_hint_x=0.5)
            if str(s.name) == self.selected_layer_key:
                btn_select.state = 'down'
            btn_select.bind(on_press=lambda inst, k=str(s.name): self.layer_click_manage(k))
            
            btn_visible = ToggleButton(text="Видимость", state='down', size_hint_x=0.3)
            btn_visible.bind(on_press=lambda inst, k=str(s.name): self.layer_visibility_manage(k, inst.state))
            
            color_preview = Widget(size_hint_x=0.2)
            with color_preview.canvas:
                Color(s.rgb[0]/255, s.rgb[1]/255, s.rgb[2]/255, 1)
                self.rect_c = Rectangle(pos=color_preview.pos, size=(30, 30))
            def update_preview_pos(inst, val):
                inst.canvas.clear()
                with inst.canvas:
                    Color(inst.s_rgb[0]/255, inst.s_rgb[1]/255, inst.s_rgb[2]/255, 1)
                    Rectangle(pos=(inst.pos[0] + 5, inst.pos[1] + 7), size=(30, 30))
            color_preview.s_rgb = s.rgb
            color_preview.bind(pos=update_preview_pos, size=update_preview_pos)

            layer_box.add_widget(color_preview)
            layer_box.add_widget(btn_select)
            layer_box.add_widget(btn_visible)
            self.list_layout.add_widget(layer_box)

    def layer_click_manage(self, layer_key):
        self.selected_layer_key = layer_key
        self.status_bar.text = f"Активный рабочий слой: {layer_key}"
        if self.tool_mode == 'draw':
            self.tools_menu_btn.text = f"Карандаш (Слой: {layer_key})"
        elif self.tool_mode == 'erase':
            self.tools_menu_btn.text = f"Ластик (Слой: {layer_key})"

    def layer_visibility_manage(self, layer_key, state):
        if layer_key in self.active_layers:
            if state == 'down':
                self.active_layers[layer_key].opacity = 1.0
            else:
                self.active_layers[layer_key].opacity = 0.0

    def save_current_project(self):
        if not main.sp_sloy:
            self.status_bar.text = "Ошибка: Нет данных для сохранения"
            return
        main.save_project("project_save.json")
        self.status_bar.text = "Проект сохранен в файл project_save.json"

    def load_existing_project(self):
        success = main.load_project("project_save.json")
        if success:
            self.status_bar.text = "Проект успешно загружен"
            self.visual()
        else:
            self.status_bar.text = "Ошибка: Не удалось загрузить проект"

    def print_file(self):
        self.status_bar.text = f"Выбран файл карты: {karta}"

    def unite_layer(self):
        if len(main.sp_sloy) < 2:
            self.status_bar.text = "Ошибка: Для объединения нужно минимум 2 слоя"
            return
        
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        self.input_layer_1 = TextInput(hint_text="Имя первого слоя", multiline=False, size_hint_y=None, height='40dp')
        self.input_layer_2 = TextInput(hint_text="Имя второго слоя", multiline=False, size_hint_y=None, height='40dp')
        
        btn_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height='45dp')
        btn_confirm = Button(text="Объединить", background_color=(0, 0.7, 0.3, 1))
        btn_close = Button(text="Отмена")
        btn_layout.add_widget(btn_confirm)
        btn_layout.add_widget(btn_close)
        
        content.add_widget(Label(text="Введите имена объединяемых слоев:", size_hint_y=None, height='30dp'))
        content.add_widget(self.input_layer_1)
        content.add_widget(self.input_layer_2)
        content.add_widget(btn_layout)
        
        self.unite_popup = Popup(title='Объединение слоев ГИС', content=content, size_hint=(None, None), size=('350dp', '250dp'), auto_dismiss=False)
        
        btn_confirm.bind(on_release=self.process_unite)
        btn_close.bind(on_release=self.unite_popup.dismiss)
        self.unite_popup.open()

    def process_unite(self, instance):
        name1 = self.input_layer_1.text.strip()
        name2 = self.input_layer_2.text.strip()
        
        layer1 = None
        layer2 = None
        
        for s in main.sp_sloy:
            if str(s.name) == name1:
                layer1 = s
            if str(s.name) == name2:
                layer2 = s
                
        if layer1 and layer2 and layer1 != layer2:
            layer1.sp_pix.update(layer2.sp_pix)
            main.sp_sloy.remove(layer2)
            self.status_bar.text = f"Слой {name2} успешно объединен со слоем {name1}"
            self.selected_layer_key = None
            self.tool_mode = 'view'
            self.tools_menu_btn.text = 'Режим навигации'
            self.visual()
        else:
            self.status_bar.text = "Ошибка: Неверно указаны имена слоев"
            
        self.unite_popup.dismiss()


if __name__ == "__main__":
    MyApp().run()