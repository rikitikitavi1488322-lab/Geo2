import os

from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.filechooser import FileChooserListView
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

from kivy.utils import platform


# Настройка запроса разрешений для Android
if platform == 'android':
    from jnius import autoclass
    from android.permissions import request_permissions, Permission

    def request_android_storage_permission():
        # Подключаем необходимые Java-классы Android
        Environment = autoclass('android.os.Environment')
        Build = autoclass('android.os.Build$VERSION')
        
        # Проверяем: если Android 11 (API 30) и выше
        if Build.SDK_INT >= 30:
            # Если разрешение "Управление всеми файлами" еще не получено
            if not Environment.isExternalStorageManager():
                try:
                    PythonActivity = autoclass('org.kivy.android.PythonActivity')
                    Intent = autoclass('android.content.Intent')
                    Settings = autoclass('android.provider.Settings')
                    Uri = autoclass('android.net.Uri')
                    
                    activity = PythonActivity.mActivity
                    # Создаем намерение (Intent) открыть системные настройки для нашего приложения
                    intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
                    uri = Uri.fromParts("package", activity.getPackageName(), None)
                    intent.setData(uri)
                    # Перенаправляем пользователя в настройки
                    activity.startActivity(intent)
                except Exception as e:
                    print(f"Не удалось открыть настройки разрешений: {e}")
        else:
            # Для старых версий Android (10 и ниже) вызываем обычное всплывающее окно
            request_permissions([
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE
            ])
            
def get_storage_path():
    if platform == 'android':
        try:
            from jnius import autoclass
            Environment = autoclass('android.os.Environment')
            return Environment.getExternalStorageDirectory().getAbsolutePath()
        except Exception:
            return '/storage/emulated/0'
    return os.getcwd()

width = Window.width
height = Window.height

Window.size = (width, height)
Window.clearcolor = (40/255, 43/255, 48/255, 1) 
Window.title = "geotelo"



class FileLoadDialog(Popup):
    def __init__(self, title="Открыть файл", filters=None, on_success=None, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.size_hint = (0.9, 0.9)
        self.on_success = on_success

        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        
        # Проводник
        self.file_chooser = FileChooserListView(
            path=get_storage_path(), 
            filters=filters if filters else ['*']
        )
        layout.add_widget(self.file_chooser)

        # Нижняя панель с кнопками
        buttons = BoxLayout(size_hint_y=0.15, spacing=10)
        btn_cancel = Button(text="Отмена", on_release=self.dismiss)
        btn_ok = Button(text="Открыть", on_release=self.confirm)
        
        buttons.add_widget(btn_cancel)
        buttons.add_widget(btn_ok)
        layout.add_widget(buttons)
        
        self.content = layout

    def confirm(self, instance):
        if self.file_chooser.selection:
            selected_file = self.file_chooser.selection[0]
            self.dismiss()
            if self.on_success:
                self.on_success(selected_file)


class FileSaveDialog(Popup):
    def __init__(self, title="Сохранить как...", default_name="project.json", on_success=None, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.size_hint = (0.9, 0.9)
        self.on_success = on_success

        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        
        # Проводник для выбора директории сохранения
        self.file_chooser = FileChooserListView(path=get_storage_path())
        layout.add_widget(self.file_chooser)

        # Поле для ввода имени файла
        input_panel = BoxLayout(size_hint_y=0.1, spacing=10)
        input_panel.add_widget(Label(text="Имя файла:", size_hint_x=0.2))
        self.txt_input = TextInput(text=default_name, multiline=False, size_hint_x=0.8)
        input_panel.add_widget(self.txt_input)
        layout.add_widget(input_panel)

        # Нижняя панель с кнопками
        buttons = BoxLayout(size_hint_y=0.15, spacing=10)
        btn_cancel = Button(text="Отмена", on_release=self.dismiss)
        btn_ok = Button(text="Сохранить", on_release=self.confirm)
        
        buttons.add_widget(btn_cancel)
        buttons.add_widget(btn_ok)
        layout.add_widget(buttons)
        
        self.content = layout

    def confirm(self, instance):
        filename = self.txt_input.text.strip()
        if filename:
            # Собираем полный путь из выбранной папки и введенного имени
            full_path = os.path.join(self.file_chooser.path, filename)
            self.dismiss()
            if self.on_success:
                self.on_success(full_path)

class CustomMapScene(ScatterLayout):
    def on_touch_down(self, touch):
        # Если клик вне области виджета (например, на боковой панели или статус-баре),
        # мы ОБЯЗАТЕЛЬНО передаем событие дальше через super(), а не возвращаем False.
        if not Widget.collide_point(self, touch.x, touch.y):
            return super().on_touch_down(touch)
        
        app = App.get_running_app()
        
        # Если активен инструмент рисования или удаления
        if app.tool_mode in ['draw', 'erase']:
            for child in reversed(self.children):
                if isinstance(child, FastPixelLayer) and child.layer_name == app.selected_layer_key:
                    if child.collide_point(*touch.pos):
                        # Передаем touch стандартным элементам Scatter
                        return super().on_touch_down(touch)
            # Если по слою не попали, не блокируем Kivy, даем закрыться меню/попапам
            return super().on_touch_down(touch)

        # Обработка скролла/зума колесиком мыши
        if touch.is_mouse_scrolling:
            factor = 1.1 if touch.button == 'scrollup' else 0.9
            if 0.5 <= self.scale * factor <= 20:
                self.apply_transform(self.transform.scale(factor, factor, 1), post_multiply=True)
            return True
            
        # Во всех остальных случаях (режим 'view' и т.д.) используем стандартное поведение
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if not Widget.collide_point(self, touch.x, touch.y):
            return super().on_touch_move(touch)
            
        app = App.get_running_app()
        if app.tool_mode in ['draw', 'erase']:
            for child in reversed(self.children):
                if isinstance(child, FastPixelLayer) and child.layer_name == app.selected_layer_key:
                    if child.collide_point(*touch.pos):
                        return super().on_touch_move(touch)
            return super().on_touch_move(touch)
            
        return super().on_touch_move(touch)


class MyApp(App):
    def __init__(self):
        super().__init__()
        self.load = False
        
        self.tool_mode = 'view'
        self.selected_layer_key = None
        self.brush_radius = 5
        
        self.menu_btn = Button(text='Меню', size_hint_x=0.55)
        self.tools_menu_btn = Button(text='Навигация', size_hint_x=0.35)
        self.exit_btn = Button(text='x', size_hint_x=0.1)
        
        self.exit_btn.bind(on_press=self.stop)
        self.active_layers = {}
        
    def open_geo_calibration_popup(self, pixel_coords):
        px, py = pixel_coords
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        content.add_widget(Label(text=f"Точка на карте: X={px}, Y={py}\nВведите географические координаты:", size_hint_y=None, height='50dp'))
        
        lat_input = TextInput(hint_text="Широта (Lat), например: 55.7558", multiline=False, size_hint_y=None, height='40dp')
        lon_input = TextInput(hint_text="Долгота (Lon), например: 37.6173", multiline=False, size_hint_y=None, height='40dp')
        
        content.add_widget(lat_input)
        content.add_widget(lon_input)
        
        btn_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height='45dp')
        ok_btn = Button(text="Добавить")
        cancel_btn = Button(text="Отмена")
        btn_layout.add_widget(ok_btn)
        btn_layout.add_widget(cancel_btn)
        content.add_widget(btn_layout)
        
        popup = Popup(title='Привязка координаты', content=content, size_hint=(0.9, 0.4), auto_dismiss=False)
        
        def save_geo_point(instance):
            try:
                lat = float(lat_input.text.strip())
                lon = float(lon_input.text.strip())
                
                # Добавляем точку в глобальное хранилище
                main.control_points.append({"pixel": (px, py), "geo": (lat, lon)})
                
                # Пробуем откалибровать систему
                success, msg = main.geo_system.calibrate(main.control_points)
                self.status_bar.text = f"{msg} Опорных точек: {len(main.control_points)}"
                
                popup.dismiss()
            except ValueError:
                self.status_bar.text = "Ошибка: Введены некорректные числа!"
                
        ok_btn.bind(on_release=save_geo_point)
        cancel_btn.bind(on_release=popup.dismiss)
        popup.open()
        
    def load_elevation_data_clicked(self):
        if not main.geo_system.is_calibrated:
            self.show_popup_message("Ошибка", "Сначала выполните геопривязку карты по точкам!")
            return

        def background_work():
            success = main.compute_all_elevations(hgt_folder="dem_data")
            if success:
                # Обновляем UI по завершению (безопасно для Kivy через Clock)
                Clock.schedule_once(lambda dt: self.show_popup_message("Успех", "Данные высот загружены!"), 0)
            else:
                Clock.schedule_once(lambda dt: self.show_popup_message("Ошибка", "Не удалось загрузить данные высот. Проверьте файлы в dem_data."), 0)

        threading.Thread(target=background_work, daemon=True).start()

    def choose_map_image(self):

        dialog = FileLoadDialog(
            title="Выберите изображение карты",
            filters=['*.jpg', '*.jpeg', '*.png'],
            on_success=self.load_map_success
        )
        dialog.open()

    def load_map_success(self, file_path):
        print(f"Выбрана карта: {file_path}")
        main.karta = file_path
        self.status_bar.text = f"Выбран файл карты: {file_path}"
        
    def save_project_dialog(self):

        dialog = FileSaveDialog(
            title="Сохранение проекта",
            default_name="geo_session.json",
            on_success=self.save_project_success
        )
        dialog.open()

    def save_project_success(self, full_path):
        # Автоматически добавляем расширение json, если пользователь забыл его ввести
        if not full_path.lower().endswith('.json'):
            full_path += '.json'
        
        try:
            # Вызываем функцию сохранения из вашего модуля main.py
            success = main.save_project(full_path)
            if success:
                print(f"Проект сохранен по пути: {full_path}")
        except Exception as e:
            print(f"Ошибка при сохранении: {e}")
            
    def load_project_dialog(self):
        dialog = FileLoadDialog(
            title="Выберите файл проекта JSON",
            filters=['*.json'],
            on_success=self.load_project_success
        )
        dialog.open()

    def load_project_success(self, path):
        # Закрываем попап выбора файла, если он еще открыт
        if hasattr(self, 'load_dialog') and self.load_dialog:
            self.load_dialog.dismiss()
            
        # Запускаем чтение файла проекта
        if main.load_project(path):
            self.status_bar.text = "Проект успешно загружен!"
            # СТРОГО ЧЕРЕЗ CLOCK возвращаем перерисовку интерфейса в главный поток:
            Clock.schedule_once(lambda dt: self.visual(), 0)
        else:
            self.status_bar.text = "Ошибка загрузки проекта!"

    def print_file(self):
        self.choose_map_image()

    def proc_start(self):
        if not self.load and main.karta is not None:
            self.load = True
            main.status_message = "Запуск вычислительного ядра..."
            threading.Thread(target=self.thread_calculations, daemon=True).start()
            Clock.schedule_interval(self.tick_status_check, 0.1)

    def thread_calculations(self):
        try:
            main.main_all(main.karta)
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
        content = BoxLayout(orientation='vertical', spacing=15, padding=15)
        content.add_widget(Label(text="Настройки инструментов редактирования", size_hint_y=None, height='30dp', font_size='16sp'))
        
        # --- Размер кисти ---
        slider_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height='50dp', spacing=10)
        self.settings_slider_label = Label(text=f"Размер кисти/ластика: {self.brush_radius} px", size_hint_x=0.4)
        brush_slider = Slider(min=1, max=50, value=self.brush_radius, step=1, size_hint_x=0.6)
        
        def on_slider_change(instance, value):
            self.brush_radius = int(value)
            self.settings_slider_label.text = f"Размер кисти/ластика: {self.brush_radius} px"
            
        brush_slider.bind(value=on_slider_change)
        slider_layout.add_widget(self.settings_slider_label)
        slider_layout.add_widget(brush_slider)
        content.add_widget(slider_layout)

        # --- Порог расстояния (min_d2) ---
        d2_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height='50dp', spacing=10)
        self.d2_label = Label(text=f"Порог цвета (min_d2): {main.min_d2}", size_hint_x=0.4)
        d2_slider = Slider(min=100, max=5000, value=main.min_d2, step=50, size_hint_x=0.6)

        def on_d2_change(instance, value):
            main.min_d2 = int(value)
            self.d2_label.text = f"Порог цвета (min_d2): {main.min_d2}"

        d2_slider.bind(value=on_d2_change)
        d2_layout.add_widget(self.d2_label)
        d2_layout.add_widget(d2_slider)
        content.add_widget(d2_layout)

        # --- Число кластеров K-Means ---
        k_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height='50dp', spacing=10)
        self.k_label = Label(text=f"Кластеры K-Means: {main.k_clusters}", size_hint_x=0.4)
        k_slider = Slider(min=5, max=60, value=main.k_clusters, step=1, size_hint_x=0.6)

        def on_k_change(instance, value):
            main.k_clusters = int(value)
            self.k_label.text = f"Кластеры K-Means: {main.k_clusters}"

        k_slider.bind(value=on_k_change)
        k_layout.add_widget(self.k_label)
        k_layout.add_widget(k_slider)
        content.add_widget(k_layout)
        
        close_btn = Button(text="Закрыть", size_hint_y=None, height='45dp')
        content.add_widget(close_btn)
        
        settings_popup = Popup(title='Настройки ГИС', content=content, size_hint=(0.8, 0.6), auto_dismiss=True)
        close_btn.bind(on_release=settings_popup.dismiss)
        
        def on_dismiss_callback(instance):
            self.status_bar.text = f"Настройки сохранены: кисть={self.brush_radius}px, min_d2={main.min_d2}, K={main.k_clusters}"
        settings_popup.bind(on_dismiss=on_dismiss_callback)
        
        settings_popup.open()

    def menu_select_handler(self, instance, text):
        instance.dismiss()
        
        if text == 'unite':
            self.unite_layer()
        elif text == 'новый расчет':
            self.proc_start()
        elif text == 'выбрать файл':
            self.choose_map_image()
        elif text == 'сохранить':
            self.save_project_dialog()
        elif text == 'загрузить':
            self.load_project_dialog()
        elif text == 'настройки':
            self.open_settings_popup()

    def tools_select_handler(self, instance, text):
        if text == 'rejim_prosmotra':
            self.tool_mode = 'view'
            self.tools_menu_btn.text = "Навигация"
            self.status_bar.text = "Режим: Навигация"
            
        elif text == 'rejim_geotocki':
            self.tool_mode = 'georef'
            self.tools_menu_btn.text = "Реперные точки"
            self.status_bar.text = f"Режим: Кликните на карту, чтобы добавить опорную точку (Всего: {len(main.control_points)})"
        
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

    def build(self):
        if platform == 'android':
            request_android_storage_permission()

        
        main_layout = BoxLayout(orientation='vertical')
        
        contral_panel = BoxLayout(orientation='horizontal', size_hint_y=0.09, spacing=5)
        contral_panel.add_widget(self.menu_btn)
        contral_panel.add_widget(self.tools_menu_btn)
        contral_panel.add_widget(self.exit_btn)
        main_layout.add_widget(contral_panel)
        
        self.dropdown_menu = DropDown()
        unite_menu_btn = Button(text='Объединить слои', size_hint_y=None, height='50dp')
        unite_menu_btn.bind(on_release=lambda instance: self.dropdown_menu.select('unite'))
        start_btn = Button(text='Новый расчет', size_hint_y=None, height='50dp')
        start_btn.bind(on_release=lambda instance: self.dropdown_menu.select('новый расчет'))
        file_btn = Button(text='Выбрать файл', size_hint_y=None, height='50dp')
        file_btn.bind(on_release=lambda instance: self.dropdown_menu.select('выбрать файл'))
        save_btn = Button(text='Сохранить проект', size_hint_y=None, height='50dp')
        save_btn.bind(on_release=lambda instance: self.dropdown_menu.select('сохранить'))
        load_btn = Button(text='Загрузить проект', size_hint_y=None, height='50dp')
        load_btn.bind(on_release=lambda instance: self.dropdown_menu.select('загрузить'))
        settings_btn = Button(text='Настройки ГИС', size_hint_y=None, height='50dp')
        settings_btn.bind(on_release=lambda instance: self.dropdown_menu.select('настройки'))
        
        self.dropdown_menu.add_widget(unite_menu_btn)
        self.dropdown_menu.add_widget(start_btn)
        self.dropdown_menu.add_widget(file_btn)
        self.dropdown_menu.add_widget(save_btn)
        self.dropdown_menu.add_widget(load_btn)
        self.dropdown_menu.add_widget(settings_btn)
        
        self.menu_btn.bind(on_release=self.dropdown_menu.open)
        self.dropdown_menu.bind(on_select=self.menu_select_handler)
        
        self.dropdown_tools = DropDown()
        mode_view = Button(text='Навигация', size_hint_y=None, height='50dp')
        mode_view.bind(on_release=lambda instance: self.dropdown_tools.select('rejim_prosmotra'))
        mode_draw = Button(text='Карандаш', size_hint_y=None, height='50dp')
        mode_draw.bind(on_release=lambda instance: self.dropdown_tools.select('rejim_karandasha'))
        mode_erase = Button(text='Ластик', size_hint_y=None, height='50dp')
        mode_erase.bind(on_release=lambda instance: self.dropdown_tools.select('rejim_lastika'))
        mode_geo = Button(text='Привязка', size_hint_y=None, height='50dp')
        mode_geo.bind(on_release=lambda instance: self.dropdown_tools.select('rejim_geotocki'))

        self.dropdown_tools.add_widget(mode_view)
        self.dropdown_tools.add_widget(mode_draw)
        self.dropdown_tools.add_widget(mode_erase)
        self.dropdown_tools.add_widget(mode_geo)
        self.tools_menu_btn.bind(on_release=self.dropdown_tools.open)
        self.dropdown_tools.bind(on_select=self.tools_select_handler)
        
        self.status_bar = Label(text="Ожидание действий. Откройте Меню.", size_hint_y=0.04, color=(0.9, 1, 0.9, 1))
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
        if hasattr(self, 'menu') and self.menu:
            self.menu.dismiss()  
            
            
        for child in list(self.map_scene.children):
            if isinstance(child, FastPixelLayer):
                self.map_scene.remove_widget(child)
                
        self.list_layout.clear_widgets()
        self.active_layers.clear()
        
        self.tool_mode = 'view'
        self.selected_layer_key = None
        self.tools_menu_btn.text = "Навигация"
        self.status_bar.text = "Проект загружен. Режим: Навигация"

        for layer_data in main.sp_sloy:
            sp_pix = layer_data.sp_pix
            layer = FastPixelLayer(tex_w=main.x, tex_h=main.y, layer_name=str(layer_data.name))
            layer.fill_pixels(sp_pix, layer_data.rgb)
            
            layer_key = str(layer_data.name)
            self.active_layers[layer_key] = layer
            
            self.map_scene.add_widget(layer)
            
            row = BoxLayout(orientation='horizontal', size_hint_y=None, height='40dp', spacing=3)
            
            btn = ToggleButton(text=f"{layer_data.name} [{layer_data.vozrast}]", state='down', size_hint_x=0.8)
            btn.layer_index = layer_key
            btn.bind(on_press=self.layer_click_manage)
            
            btn_edit = Button(text='i', size_hint_x=0.2)
            btn_edit.layer_index = layer_key
            btn_edit.bind(on_release=lambda instance: self.open_meta_popup(instance.layer_index))
            
            btn_del = Button(text='x', size_hint_x=0.2)
            btn_del.layer_index = layer_key
            btn_del.bind(on_release=self.delete_layer)
            
            row.add_widget(btn)
            row.add_widget(btn_edit)
            row.add_widget(btn_del)
            self.list_layout.add_widget(row)

    def layer_click_manage(self, instance):
        layer_key = instance.layer_index
        target_layer = self.active_layers.get(layer_key)
        
        if target_layer:
            if instance.state == 'down':
                target_layer.opacity = 1.0
                self.selected_layer_key = layer_key
                if self.tool_mode in ['draw', 'erase']:
                    self.status_bar.text = f"Выбран Слой {self.selected_layer_key} ({self.tool_mode})"
                else:
                    self.status_bar.text = f"Слой {layer_key} выбран. Нажмите (i) для редактирования атрибутов."
            else:
                target_layer.opacity = 0.0
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
        
        self.texture = Texture.create(size=(self.tex_w, self.tex_h), colorfmt='rgba')
        self.texture.min_filter = 'nearest'
        self.texture.mag_filter = 'nearest'
        
        self.buffer = bytearray(self.tex_w * self.tex_h * 4)
        
        with self.canvas:
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
        self.buffer = bytearray(self.tex_w * self.tex_h * 4)
        
        for xy in sp_pix:
            if 0 <= xy[0] < self.tex_w and 0 <= xy[1] < self.tex_h:
                kivy_y = self.tex_h - 1 - xy[1]
                idx = (kivy_y * self.tex_w + xy[0]) * 4
                self.buffer[idx] = color[0]
                self.buffer[idx+1] = color[1]
                self.buffer[idx+2] = color[2]
                self.buffer[idx+3] = 255 
                
        self.texture.blit_buffer(self.buffer, colorfmt='rgba', bufferfmt='ubyte')
        self.canvas.ask_update()

    def screen_to_image_coords(self, touch):
        if not hasattr(self, 'new_w') or self.new_w == 0:
            return None
        
        # touch.pos ТЕПЕРЬ УЖЕ локальный благодаря правильному вызову super() в ScatterLayout
        local_x, local_y = touch.pos 
        
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
        coords = self.screen_to_image_coords(touch)
       
        if coords and app.tool_mode == 'georef':
            # Если пользователь кликнул в режиме привязки, открываем диалог
            app.open_geo_calibration_popup(coords)
            return True 
        
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
                                self.buffer[idx] = int(self.layer_color[0] * 255)
                                self.buffer[idx+1] = int(self.layer_color[1] * 255)
                                self.buffer[idx+2] = int(self.layer_color[2] * 255)
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