@echo off
REM Archive old NFL model versions

echo Creating archive directory...
if not exist "src\models\archive" mkdir "src\models\archive"

echo.
echo Moving old model versions to archive...

if exist "src\models\model_v0.py" (
    move "src\models\model_v0.py" "src\models\archive\"
    echo ✓ Moved model_v0.py
) else (
    echo - model_v0.py not found
)

if exist "src\models\model_v1.py" (
    move "src\models\model_v1.py" "src\models\archive\"
    echo ✓ Moved model_v1.py
) else (
    echo - model_v1.py not found
)

if exist "src\models\model_v2.py" (
    move "src\models\model_v2.py" "src\models\archive\"
    echo ✓ Moved model_v2.py
) else (
    echo - model_v2.py not found
)

echo.
echo Archiving complete!
echo.
echo Active model: src\models\model_v3.py
echo Archived models: src\models\archive\

pause
