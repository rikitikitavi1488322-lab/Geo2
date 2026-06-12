[app]

# (str) Название твоего приложения в телефоне
title = GeoTelo

# (str) Имя пакета (латиницей, без пробелов)
package.name = geotelo

# (str) Домен пакета (для уникального идентификатора приложения)
package.domain = org.geotelo

# (str) Папка с исходным кодом (текущая директория)
source.dir = .

# (list) Расширения файлов, которые нужно упаковать в APK
# Добавлены json и hgt для твоих карт и высот SRTM
source.include_exts = py, png, jpg, jpeg, kv, atlas, json, hgt

# (list) Список папок, которые нужно включить целиком
source.include_dirs = dem_data

# (str) Версия приложения
version = 0.1

# (list) Все библиотеки, от которых зависит проект.
# Обязательно указываем pillow и numpy для работы с графикой и матрицами
requirements = python3, kivy, pillow, numpy

# (str) Ориентация экрана (выставлена альбомная, как в твоих логах)
orientation = landscape

# (bool) Полноэкранный режим
fullscreen = 1

# ==========================================
# Настройки для Android
# ==========================================

# (num) Версия Android API (33 — стандарт для современных систем)
android.api = 33

# (num) Минимальная поддерживаемая версия Android (24 — это Android 7.0)
android.minapi = 24

# (num) Android NDK API
android.ndk_api = 24

# (list) Архитектуры процессоров. Собираем сразу под оба стандарта (32 и 64 бит)
android.archs = arm64-v8a, armeabi-v7a

# (bool) Использовать AndroidX (необходимо для новых версий Gradle)
android.enable_androidx = True

# (bool) Разрешить резервное копирование данных приложения
android.allow_backup = True

android.permissions = READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE


[buildozer]

# (int) Уровень логов (1 = только важная инфо, чтобы не переполнять память GitHub)
log_level = 1

# (int) Предупреждать, если билд запущен от root
warn_on_root = 1
