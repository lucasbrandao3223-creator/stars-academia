@echo off
title STARS Academia
cd /d "%~dp0"
echo Instalando as bibliotecas (so demora na primeira vez)...
python -m pip install -r requirements.txt
echo.
echo Ligando o site... NAO feche esta janela enquanto estiver usando.
start "" /min cmd /c "timeout /t 5 >nul & start http://127.0.0.1:5000"
python sistema\app.py
echo.
echo O site parou. Se apareceu erro acima, tire um print desta janela.
pause
