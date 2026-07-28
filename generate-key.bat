@echo off
setlocal EnableDelayedExpansion

:: --- НАСТРОЙКИ ---
set "ENV_FILE=.env"
set "KEY_NAME=SECRET_KEY"
set "LENGTH=50"
:: -----------------

set "chars=abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@%+=:/?.,-_"

echo Generating %KEY_NAME%...

set "key="
for /L %%i in (1, 1, %LENGTH%) do (
    set /a "idx=!random! %% 84 + 1"
    
    :: Вызываем подпрограмму для получения одного случайного символа
    call :GetChar !idx!
    set "key=!key!!char!"
)
goto :AfterFunction

:GetChar
:: %1 — это первый аргумент (наш idx), который CMD подставит сюда
:: Используем трюк с расширением подстроки, где имя переменной формируется на лету
call set "char=!chars:~%1,1!"
exit /b

:AfterFunction

if exist "%ENV_FILE%" (
    echo File %ENV_FILE% found. Updating %KEY_NAME%...
    call powershell -Command ^
    "$path = '%ENV_FILE%'; $name = '%KEY_NAME%'; $val = '%key%';" ^
    "(Get-Content $path) | ForEach-Object { if ($_ -match \"^$name=\") { \"$name=$val\" } else { $_ } } | Set-Content $path -Encoding UTF8"
) else (
    echo Creating new file %ENV_FILE%...
    echo %KEY_NAME%=%key% > "%ENV_FILE%"
)

echo Done!
echo New key: %key%
echo.
echo Don't forget to add %ENV_FILE% to .gitignore
endlocal