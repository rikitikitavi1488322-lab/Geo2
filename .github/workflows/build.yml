name: Build APK with Buildozer

on:
  push:
    branches: [ main, master ]
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-22.04

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      # Создаем папку dem_data
      - name: Create dem_data folder
        run: |
          mkdir -p dem_data
          touch dem_data/.gitkeep

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      # ЧЕТКАЯ НАСТРОЙКА JAVA 17 (Это решит проблему с Package the application)
      - name: Setup Java 17
        uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '17'

      # Устанавливаем остальные системные зависимости (уже без openjdk)
      - name: Install system dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y build-essential libffi-dev libssl-dev libltdl-dev
          sudo apt-get install -y zip unzip git autoconf libtool pkg-config zlib1g-dev
          
      - name: Install Buildozer and Cython
        run: |
          pip install --upgrade pip
          pip install buildozer cython virtualenv

      - name: Build APK
        run: yes | buildozer android debug

      - name: Upload APK artifact
        uses: actions/upload-artifact@v4
        with:
          name: geotelo-app
          path: bin/*.apk
