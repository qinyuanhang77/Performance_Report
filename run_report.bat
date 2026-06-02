@echo off
chcp 65001 >nul
cd /d %~dp0
echo ============================================
echo JMeter 报告一键生成器
echo ============================================
echo.
if not exist batch_generator.py (
    echo [Error] Cannot find batch_generator.py
    pause
    exit /b 1
)
python batch_generator.py
echo.
echo Done.
pause