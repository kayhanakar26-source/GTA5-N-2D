@echo off
cd /d "%~dp0"
title SOKAKLAR 2D

where python >nul 2>nul
if %errorlevel%==0 (
    python sokaklar_2d.py
) else (
    py sokaklar_2d.py
)

if errorlevel 1 (
    echo.
    echo Oyun baslatilamadi. Pygame kurulu mu kontrol edin:
    echo     python -m pip install "pygame>=2.5.0,<3"
    echo.
    pause
)
