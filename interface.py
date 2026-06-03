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
            
        if touch.is_mouse_scrolling:
            factor = 1.1 if touch.button == 'scrollup' else 0.9
            if 0.5 <= self.scale * factor <= 20:
                self.apply_transform(self.transform.scale(factor, factor, 1), post_multiply=True)
            return True
        return super().on_touch_down(touch)


class MyApp(App):
    def __init__(self):
        super().__init__()
        self.load = False
        self.tool_mode = 'view'
        self.selected_layer_key = None
        self.brush_radius = 5
        
        self.menu_btn = Button(text='Меню', size_hint_x=0.45)
        self.tools_menu_btn = Button(text='Режим', size_hint_x=0.3)
        self.exit_btn = Button(text='Exit', size_hint_x=0.1)
        
        self.exit_btn.bind(on_press=self.stop)
        self.active_layers = {}

    def print_file(self):
        content_print = BoxLayout(orientation='vertical', spacing=10, padding=10)
        self.user_input = TextInput(text=str(karta), hint_text="Введите название файла", multiline=False, size_hint_y=None, height='40dp')
        btn_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height='45dp')
        save_btn = Button(text="ОК")
        cancel_btn = Button(text="Отмена")
        
        btn_layout.add_widget(save_btn)
        btn_layout.add_widget(cancel_btn)
        content_print.add_widget(Label(text="Выбор файла карты:", size_hint_y=None, height='30dp'))
        content_print.add_widget(self.user_input)
        content_print.add_widget(btn_layout)
        
        self.popup = Popup(title='Запрос данных', content=content_print, size_hint=(None, None), size=('320dp', '200dp'), auto_dismiss=False)
        save_btn.bind(on_release=self.process_input_data)
        cancel_btn.bind(on_release=self.popup.dismiss)
        self.popup.open()

    def process_input_data(self, instance):
        text_entered = self.user_input.text
        global karta
        if text_entered.strip():
            karta = text_entered
            self.status_bar.text = f"Выбран файл карты: {karta}"
        self.popup.dismiss()

    def proc_start(self):
        if not self.load and karta is not None:
            self.load = True
            main.status_message = "Запуск вычислительного ядра..."
            threading.Thread(target=self.thread_calculations, daemon=True).start()
            Clock.schedule_interval(self.tick_status_check, 0.1)

    def thread_calculations(self):
        try:
            main.main_all(karta)
            Clock.schedule_once(lambda dt: self.on_calculations_success())
        except Exception as e:
            main.status_message = f"Критическая ошибка: {str(e)}"
            Clock.schedule_once(lambda dt: self.on_calculations_failed())

    def tick_status_check(self, dt):
        self.status_bar.text = main.status_message
        if not self.load:
            return False

    def on_calculations_success(self):
        self.load = False
        self.status_bar.text = "Готово! Слои успешно векторизованы."
        self.visual()

    def on_calculations_failed(self):
        self.load = False

    def save_current_project(self):
        main.save_project("geo_session.json")
        self.status_bar.text = "Проект сохранен в geo_session.json"
        
    def load_existing_project(self):
        if main.load_project("geo_session.json"):
            self.visual()
            self.status_bar.text = "Проект успешно восстановлен из JSON"
        else:
            self.status_bar.text = "Ошибка: Файл сессии не найден"



    def open_settings_popup(self):
        # Основной контейнер всплывающего окна
        content = BoxLayout(orientation='vertical', spacing=12, padding=15)
        
        content.add_widget(Label(text="Инструменты рисования", size_hint_y=None, height='25dp', font_size='15sp', color=(0, 1, 0.8, 1)))
        
        # 1. Размер кисти
        brush_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height='40dp', spacing=10)
        self.lbl_brush = Label(text=f"Кисть/Ластик: {self.brush_radius} px", size_hint_x=0.4, halign='left')
        sld_brush = Slider(min=1, max=50, value=self.brush_radius, step=1, size_hint_x=0.6)
        sld_brush.bind(value=lambda inst, val: setattr(self, 'brush_radius', int(val)) or setattr(self.lbl_brush, 'text', f"Кисть/Ластик: {int(val)} px"))
        brush_layout.add_widget(self.lbl_brush)
        brush_layout.add_widget(sld_brush)
        content.add_widget(brush_layout)
        
        content.add_widget(Label(text="Параметры первичной обработки (K-Means & PIL)", size_hint_y=None, height='25dp', font_size='15sp', color=(0, 1, 0.8, 1)))
        
        # 2. Количество кластеров (K)
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
        
        # 3. Радиус размытия (Фильтрация шума изображения)
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
        
        # 4. Порог толерантности цвета (min_d2)
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
        
        # Кнопка закрытия окна
        close_btn = Button(text="Применить настройки", size_hint_y=None, height='45dp', background_color=(0, 0.7, 0.4, 1))
        content.add_widget(close_btn)
        
        settings_popup = Popup(title='Настройки алгоритмов ядра ГИС', content=content, size_hint=(0.85, 0.65), auto_dismiss=True)
        close_btn.bind(on_release=settings_popup.dismiss)
        
        def on_dismiss_callback(instance):
            self.status_bar.text = f"Параметры изменены. K={main.k_clusters}, Blur={main.blur_radius}px, d²={main.min_d2}"
        settings_popup.bind(on_dismiss=on_dismiss_callback)
        
        settings_popup.open()

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
            self.tools_menu_btn.text = "Навигация"
            self.status_bar.text = "Режим: Навигация"
        elif text == 'rejim_karandasha':
            self.tool_mode = 'draw'
            self.tools_menu_btn.text = "Карандаш"
            if self.selected_layer_key:
                self.status_bar.text = f"Режим: Карандаш ({self.brush_radius}px). Слой {self.selected_layer_key}"
            else:
                self.status_bar.text = f"Выберите активный слой справа!"
        elif text == 'rejim_lastika':
            self.tool_mode = 'erase'
            self.tools_menu_btn.text = "Ластик"
            if self.selected_layer_key:
                self.status_bar.text = f"Режим: Ластик ({self.brush_radius}px). Слой {self.selected_layer_key}"
            else:
                self.status_bar.text = "Выберите активный слой справа!"
                
    def popup_add_layer(self):
        """Открывает диалоговое окно для создания нового пользовательского слоя"""
        if not main.x or not main.y:
            self.status_bar.text = "Ошибка: Сначала загрузите карту или проект!"
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
            self.status_bar.text = "Ошибка: Имя слоя не может быть пустым!"
            self.add_layer_popup.dismiss()
            return
            
        try:
            r = max(0, min(255, int(self.r_in.text)))
            g = max(0, min(255, int(self.g_in.text)))
            b = max(0, min(255, int(self.b_in.text)))
            rgb = (r, g, b)
        except ValueError:
            self.status_bar.text = "Ошибка: Некорректные значения цвета RGB!"
            self.add_layer_popup.dismiss()
            return

        # Вызываем ядро для добавления слоя
        success, message = main.add_new_empty_layer(name, rgb)
        self.status_bar.text = message
        
        if success:
            self.visual() # Перерисовываем интерфейс, новый слой появится в списке справа
            
        self.add_layer_popup.dismiss()

    def build(self):
        main_layout = BoxLayout(orientation='vertical')
        
        contral_panel = BoxLayout(orientation='horizontal', size_hint_y=0.06, spacing=5)
        contral_panel.add_widget(self.menu_btn)
        contral_panel.add_widget(self.tools_menu_btn)
        contral_panel.add_widget(self.exit_btn)
        main_layout.add_widget(contral_panel)
        
        dropdown_menu = DropDown()
        
        add_layer_btn = Button(text='Новый пустой слой', size_hint_y=None, height='50dp')
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

    def visual(self):
        # Полная очистка перед перерисовкой
        self.map_scene.clear_widgets()
        self.list_layout.clear_widgets()
        self.active_layers.clear()
        
        self.selected_layer_key = None
        self.tool_mode = 'view'
        self.tools_menu_btn.text = "Навигация"

        for layer_data in main.sp_sloy:
            sp_pix = layer_data.sp_pix
            layer = FastPixelLayer(tex_w=main.x, tex_h=main.y, layer_name=str(layer_data.name))
            layer.fill_pixels(sp_pix, layer_data.rgb)
            
            layer_key = str(layer_data.name)
            self.active_layers[layer_key] = layer
            
            # Добавляем слой на сцену карты
            self.map_scene.add_widget(layer)
            
            row = BoxLayout(orientation='horizontal', size_hint_y=None, height='40dp', spacing=5)
            
            # Убран параметр group! Кнопки теперь работают как независимые чекбоксы
            btn = ToggleButton(text=f"{layer_data.name} [{layer_data.vozrast}]", state='down', size_hint_x=0.8)
            btn.layer_index = layer_key
            btn.bind(on_press=self.layer_click_manage)
            
            btn_del = Button(text='x', size_hint_x=0.2)
            btn_del.layer_index = layer_key
            btn_del.bind(on_release=self.delete_layer)
            
            row.add_widget(btn)
            row.add_widget(btn_del)
            self.list_layout.add_widget(row)

    def layer_click_manage(self, instance):
        # ИСПРАВЛЕНО: Явное управление видимостью слоя без затирания соседа
        layer_key = instance.layer_index
        target_layer = self.active_layers.get(layer_key)
        
        if target_layer:
            if instance.state == 'down':
                target_layer.opacity = 1.0  # Слой становится видимым
                self.selected_layer_key = layer_key
                if self.tool_mode in ['draw', 'erase']:
                    self.status_bar.text = f"Выбран Слой {self.selected_layer_key} ({self.tool_mode})"
                else:
                    self.open_meta_popup(layer_key)
            else:
                target_layer.opacity = 0.0  # Слой полностью скрывается, но не удаляется
                if self.selected_layer_key == layer_key:
                    self.selected_layer_key = None

    def open_meta_popup(self, layer_key):
        target_layer = None
        for s in main.sp_sloy:
            if str(s.name) == layer_key:
                target_layer = s
                break
        if not target_layer: 
            return

        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        self.age_in = TextInput(text=str(target_layer.vozrast), hint_text="Возраст", multiline=False, size_hint_y=None, height='40dp')
        self.info_in = TextInput(text=str(target_layer.description), hint_text="Описание", multiline=True)
        
        content.add_widget(Label(text=f"Атрибуты слоя {layer_key}", size_hint_y=None, height='30dp'))
        content.add_widget(self.age_in)
        content.add_widget(self.info_in)
        
        btn_lay = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height='45dp')
        ok_b = Button(text="Сохранить")
        cncl_b = Button(text="Отмена")
        btn_lay.add_widget(ok_b)
        btn_lay.add_widget(cncl_b)
        content.add_widget(btn_lay)
        
        popup = Popup(title='Свойства объекта', content=content, size_hint=(0.9, 0.5))
        
        def save_data(obj):
            target_layer.vozrast = self.age_in.text if self.age_in.text.strip() else "???"
            target_layer.description = self.info_in.text
            popup.dismiss()
            self.visual()

        ok_b.bind(on_release=save_data)
        cncl_b.bind(on_release=popup.dismiss)
        popup.open()

    def delete_layer(self, instance):
        layer_key = instance.layer_index
        target_layer = self.active_layers.get(layer_key)
        if target_layer and target_layer.parent:
            target_layer.parent.remove_widget(target_layer)
            del self.active_layers[layer_key]
        if instance.parent:
            row_container = instance.parent
            if row_container.parent:
                row_container.parent.remove_widget(row_container)
        main.sp_sloy = [s for s in main.sp_sloy if str(s.name) != layer_key]
        if self.selected_layer_key == layer_key:
            self.selected_layer_key = None

    def unite_layer(self):
        selected_layer_keys = []
        for row in self.list_layout.children:
            for widget in row.children:
                if isinstance(widget, ToggleButton) and widget.state == 'down':
                    selected_layer_keys.append(widget.layer_index)
        
        if len(selected_layer_keys) < 2: 
            self.status_bar.text = "Ошибка: Выберите кнопками справа минимум 2 слоя!"
            return
        
        selected_layers_data = [layer for layer in main.sp_sloy if str(layer.name) in selected_layer_keys]
        base_layer_data = selected_layers_data[0]
        layers_to_merge = selected_layers_data[1:]

        for layer_data in layers_to_merge:
            base_layer_data.sp_pix.update(layer_data.sp_pix)

        main.sp_sloy = [layer for layer in main.sp_sloy if layer not in layers_to_merge]
        self.status_bar.text = f"Слои соединены."
        self.visual()


class FastPixelLayer(Widget):
    def __init__(self, tex_w, tex_h, layer_name, **kwargs):
        super().__init__(**kwargs)
        self.tex_w = tex_w
        self.tex_h = tex_h
        self.layer_name = layer_name
        
        # Создаем прозрачную текстуру RGBA
        self.texture = Texture.create(size=(self.tex_w, self.tex_h), colorfmt='rgba')
        self.texture.min_filter = 'nearest'
        self.texture.mag_filter = 'nearest'
        
        self.buffer = bytearray(self.tex_w * self.tex_h * 4)
        
        with self.canvas:
            # ИСПРАВЛЕНО: Явно задаем белый цвет подложки с поддержкой альфа-канала,
            # чтобы Kivy не закрашивал текстуру сплошным черным или монопольным цветом.
            Color(1, 1, 1, 1)
            self.rect = Rectangle(texture=self.texture, pos=self.pos, size=(0, 0))
            
        with self.canvas.after:
            self.marker_color = Color(1, 0, 0, 0)
            self.marker_circle = Line(circle=(0, 0, 0), width=1.5)
            
        self.bind(size=self._update_rect, pos=self._update_rect)
        
    def _update_rect(self, *args):
        if self.tex_w == 0 or self.tex_h == 0 or self.width == 0 or self.height == 0:
            return
        widget_aspect = self.width / self.height
        texture_aspect = self.tex_w / self.tex_h

        if widget_aspect > texture_aspect:
            self.new_h = self.height
            self.new_w = self.new_h * texture_aspect
        else:
            self.new_w = self.width
            self.new_h = self.new_w / texture_aspect

        self.new_x = self.x + (self.width - self.new_w) / 2
        self.new_y = self.y + (self.height - self.new_h) / 2
        self.rect.pos = (self.new_x, self.new_y)
        self.rect.size = (self.new_w, self.new_h)

    def fill_pixels(self, sp_pix, color):
        self.layer_color = color
        # ИСПРАВЛЕНО: Буфер всегда инициализируется нулями (абсолютно прозрачный фон)
        self.buffer = bytearray(self.tex_w * self.tex_h * 4)
        
        for xy in sp_pix:
            if 0 <= xy[0] < self.tex_w and 0 <= xy[1] < self.tex_h:
                kivy_y = self.tex_h - 1 - xy[1]
                idx = (kivy_y * self.tex_w + xy[0]) * 4
                self.buffer[idx] = color[0]
                self.buffer[idx+1] = color[1]
                self.buffer[idx+2] = color[2]
                self.buffer[idx+3] = 255 # Задаем полную видимость только заполненным точкам
                
        self.texture.blit_buffer(self.buffer, colorfmt='rgba', bufferfmt='ubyte')
        self.canvas.ask_update()

    def screen_to_image_coords(self, touch):
        if not hasattr(self, 'new_w') or self.new_w == 0:
            return None
        local_x, local_y = self.to_local(*touch.pos)
        norm_x = local_x - (self.width - self.new_w) / 2
        norm_y = local_y - (self.height - self.new_h) / 2
        img_x = int((norm_x / self.new_w) * self.tex_w)
        img_y = int(((self.new_h - norm_y) / self.new_h) * self.tex_h)
        
        if 0 <= img_x < self.tex_w and 0 <= img_y < self.tex_h:
            return img_x, img_y
        return None

    def update_visual_marker(self, touch):
        app = App.get_running_app()
        if app.tool_mode in ['draw', 'erase'] and app.selected_layer_key == self.layer_name:
            if app.tool_mode == 'erase':
                self.marker_color.rgba = (1, 0, 0, 0.8)
            else:
                self.marker_color.rgba = (0, 1, 0.2, 0.8)
                
            scale_factor = self.new_w / self.tex_w
            screen_radius = app.brush_radius * scale_factor
            self.marker_circle.circle = (touch.x, touch.y, screen_radius)
        else:
            self.marker_color.rgba = (1, 0, 0, 0)

    def hide_visual_marker(self):
        self.marker_color.rgba = (1, 0, 0, 0)

    def on_touch_down(self, touch):
        app = App.get_running_app()
        if app.tool_mode in ['draw', 'erase'] and app.selected_layer_key == self.layer_name:
            self.update_visual_marker(touch)
            coords = self.screen_to_image_coords(touch)
            if coords:
                self.modify_area_data(coords, app.tool_mode, app.brush_radius)
                return True
        return False

    def on_touch_move(self, touch):
        app = App.get_running_app()
        if app.tool_mode in ['draw', 'erase'] and app.selected_layer_key == self.layer_name:
            self.update_visual_marker(touch)
            coords = self.screen_to_image_coords(touch)
            if coords:
                self.modify_area_data(coords, app.tool_mode, app.brush_radius)
                return True
        return False

    def on_touch_up(self, touch):
        self.hide_visual_marker()
        return False

    def modify_area_data(self, center_coords, mode, radius):
        target_layer_data = None
        for s in main.sp_sloy:
            if str(s.name) == self.layer_name:
                target_layer_data = s
                break
                
        if not target_layer_data:
            return

        cx, cy = center_coords
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


if __name__ == "__main__":
    MyApp().run()