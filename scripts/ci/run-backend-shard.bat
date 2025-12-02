@echo off
REM Windows Batch Script for Backend Test Sharding
REM Equivalent to run-backend-shard.sh for Windows environments

setlocal enabledelayedexpansion

REM Default values
set SHARD_INDEX=1
set TOTAL_SHARDS=2
set TEST_PATTERN=**/test_*.py
set COVERAGE_DIR=coverage\backend\shard-%SHARD_INDEX%

REM Parse command line arguments
:parse_args
if "%~1"=="" goto :run_tests
if "%~1"=="--shard-index" (
    set SHARD_INDEX=%~2
    shift
    shift
    goto :parse_args
)
if "%~1"=="--total-shards" (
    set TOTAL_SHARDS=%~2
    shift
    shift
    goto :parse_args
)
if "%~1"=="--pattern" (
    set TEST_PATTERN=%~2
    shift
    shift
    goto :parse_args
)
if "%~1"=="--coverage-dir" (
    set COVERAGE_DIR=%~2
    shift
    shift
    goto :parse_args
)
if "%~1"=="--help" (
    goto :show_help
)

echo Unknown argument: %~1
goto :show_help

:run_tests
echo 🚀 Running Backend Test Shard %SHARD_INDEX%/%TOTAL_SHARDS% on Windows
echo ===============================================
echo.

REM Check if we're in the correct directory
if not exist "requirements.txt" (
    echo ❌ Error: requirements.txt not found. Please run this script from the backend directory.
    exit /b 1
)

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Python not found. Please install Python and try again.
    exit /b 1
)

REM Set environment variables
set CI=true
set SHARD_INDEX=%SHARD_INDEX%
set TOTAL_SHARDS=%TOTAL_SHARDS%
set PYTEST_SHARD_INDEX=%SHARD_INDEX%
set PYTEST_TOTAL_SHARDS=%TOTAL_SHARDS%

REM Create coverage directory
if not exist "%COVERAGE_DIR%" mkdir "%COVERAGE_DIR%"

echo 📊 Discovering Python test files for shard %SHARD_INDEX%...

REM Use PowerShell to find and distribute test files
set TEMP_TEST_LIST=%TEMP%\backend_test_list_%RANDOM%.txt

powershell -Command ^
    "$testFiles = Get-ChildItem -Path '.' -Recurse -Include 'test_*.py' | ^
                Where-Object { $_.FullName -notlike '*node_modules*' -and $_.FullName -notlike '*\.venv*' -and $_.FullName -not_like '*__pycache__*' -and $_.FullName -not_like '*coverage*' } | ^
                Sort-Object FullName; ^
    $totalFiles = $testFiles.Count; ^
    $filesPerShard = [Math]::Ceiling($totalFiles / %TOTAL_SHARDS%); ^
    $startIndex = (%SHARD_INDEX% - 1) * $filesPerShard; ^
    $endIndex = [Math]::Min($startIndex + $filesPerShard - 1, $totalFiles - 1); ^
    if ($startIndex -lt $totalFiles) { ^
        $testFiles[$startIndex..$endIndex] | ForEach-Object { $_.FullName } | ^
        Out-File -FilePath '%TEMP_TEST_LIST%' -Encoding utf8; ^
    }"

REM Check if we have test files for this shard
if not exist "%TEMP_TEST_LIST%" (
    echo ⚠️  No test files found for shard %SHARD_INDEX%
    exit /b 0
)

REM Count test files in this shard
for /f %%i in ('type "%TEMP_TEST_LIST%" ^| find /c /v ""') do set TEST_COUNT=%%i

if %TEST_COUNT% equ 0 (
    echo ⚠️  No test files assigned to shard %SHARD_INDEX%
    del "%TEMP_TEST_LIST%" 2>nul
    exit /b 0
)

echo 📋 Found %TEST_COUNT% test files for shard %SHARD_INDEX%

REM Create pytest configuration for this shard
set PYTEST_CONFIG_FILE=pytest_shard_%SHARD_INDEX%.ini

echo 📝 Creating pytest configuration for shard %SHARD_INDEX%...

(
echo [tool:pytest]
echo # Test discovery
echo testpaths = .
echo python_files = test_*.py *_test.py
echo python_classes = Test*
echo python_functions = test_*
echo.
echo # Shard-specific configuration
echo addopts =
echo     --strict-markers
echo     --strict-config
echo     --verbose
echo     --tb=short
echo     --cov=.
echo     --cov-report=html:%COVERAGE_DIR%
echo     --cov-report=term-missing
echo     --cov-report=json:%COVERAGE_DIR%\coverage.json
echo     --cov-fail-under=70
echo     --durations=10
echo     --maxfail=5
echo     --disable-warnings
echo.
echo # Coverage configuration
echo [coverage:run]
echo source = .
echo omit =
echo     */venv/*
echo     */.venv/*
echo     */site-packages/*
echo     */dist/*
echo     */build/*
echo     */coverage/*
echo     */node_modules/*
echo     test_*.py
echo     *_test.py
echo     __pycache__/*
echo     *.pyc
echo.
echo [coverage:report]
echo exclude_lines =
echo     pragma: no cover
echo     def __repr__
echo     def __str__
echo     raise AssertionError
echo     raise NotImplementedError
echo     if __name__ == .__main__.:
echo     if TYPE_CHECKING:
echo.
echo # Markers
echo markers =
echo     unit: Unit tests
echo     integration: Integration tests
echo     slow: Slow running tests
echo     smoke: Smoke tests
echo     regression: Regression tests
) > "%PYTEST_CONFIG_FILE%"

echo ⚙️  Pytest configuration created: %PYTEST_CONFIG_FILE%
echo.

REM Create test file list for pytest
set TEST_FILE_LIST=%TEMP%\pytest_tests_%SHARD_INDEX%.txt
powershell -Command ^
    "$files = Get-Content '%TEMP_TEST_LIST%'; ^
    $testModules = @(); ^
    foreach ($file in $files) { ^
        if ($file) { ^
            $relativePath = $file.Replace((Get-Location).Path + '\', '').Replace('\', '/'); ^
            $moduleName = $relativePath.Replace('.py', '').Replace('/', '.'); ^
            $testModules += $moduleName; ^
        } ^
    } ^
    $testModules -join ' ' | Out-File -FilePath '%TEST_FILE_LIST%' -Encoding utf8;"

REM Read test modules
set /p TEST_MODULES=<"%TEST_FILE_LIST%"

echo 🧪 Executing Python tests for shard %SHARD_INDEX%...
echo =================================================

if "%TEST_MODULES%"=="" (
    echo ⚠️  No test modules found for shard %SHARD_INDEX%
    goto :cleanup
)

REM Run pytest with shard configuration
echo 📋 Running tests: %TEST_MODULES%
echo.

python -m pytest ^
    %TEST_MODULES% ^
    -c "%PYTEST_CONFIG_FILE%" ^
    --junit-xml=%COVERAGE_DIR%\junit-shard-%SHARD_INDEX%.xml ^
    --html=%COVERAGE_DIR%\report-shard-%SHARD_INDEX%.html ^
    --self-contained-html

set PYTEST_EXIT_CODE=%ERRORLEVEL%

:cleanup
REM Cleanup temporary files
if exist "%TEMP_TEST_LIST%" del "%TEMP_TEST_LIST%"
if exist "%TEST_FILE_LIST%" del "%TEST_FILE_LIST%"
if exist "%PYTEST_CONFIG_FILE%" del "%PYTEST_CONFIG_FILE%"

echo.
echo 📊 Shard %SHARD_INDEX% execution completed with exit code: %PYTEST_EXIT_CODE%

REM Generate shard summary
if exist "%COVERAGE_DIR%\coverage.json" (
    echo 📈 Coverage report generated for shard %SHARD_INDEX%

    REM Extract coverage metrics using PowerShell
    powershell -Command ^
        "try { ^
            $coverage = Get-Content '%COVERAGE_DIR%\coverage.json' ^| ConvertFrom-Json; ^
            $totals = $coverage.totals; ^
            Write-Host '📊 Coverage Summary for Shard %SHARD_INDEX%:'; ^
            Write-Host \"   Lines: $([Math]::Round($totals.percent_covered))%% ($($totals.covered_lines)/$($totals.num_statements))\"; ^
            Write-Host \"   Branches: $([Math]::Round($totals.percent_covered))%% ($($totals.covered_branches)/$($totals.num_statements))\"; ^
            Write-Host \"   Functions: $([Math]::Round($totals.percent_covered))%% ($($totals.covered_functions)/$($totals.num_statements))\"; ^
            Write-Host \"   Statements: $([Math]::Round($totals.percent_covered))%% ($($totals.covered_lines)/$($totals.num_statements))\"; ^
        } catch { ^
            Write-Host '⚠️  Could not parse coverage summary'; ^
        }"
) else (
    echo ⚠️  No coverage report generated for shard %SHARD_INDEX%
)

echo.
if %PYTEST_EXIT_CODE% equ 0 (
    echo ✅ Backend test shard %SHARD_INDEX% completed successfully
) else (
    echo ❌ Backend test shard %SHARD_INDEX% failed with exit code %PYTEST_EXIT_CODE%
)

exit /b %PYTEST_EXIT_CODE%

:show_help
echo.
echo Backend Test Shard Runner (Windows)
echo ==================================
echo.
echo Usage: run-backend-shard.bat [options]
echo.
echo Options:
echo   --shard-index INDEX     Shard index (1-based, default: 1)
echo   --total-shards COUNT    Total number of shards (default: 2)
echo   --pattern PATTERN       Test file pattern (default: **/test_*.py)
echo   --coverage-dir DIR      Coverage output directory
echo   --help                  Show this help message
echo.
echo Examples:
echo   run-backend-shard.bat
echo   run-backend-shard.bat --shard-index 1 --total-shards 4
echo   run-backend-shard.bat --shard-index 2 --total-shards 4 --coverage-dir custom\coverage
echo.
echo Environment Variables:
echo   CI                      Set to 'true' for CI mode
echo   PYTEST_SHARD_INDEX      Current shard index
echo   PYTEST_TOTAL_SHARDS     Total number of shards
echo.
echo Requirements:
echo   - Python 3.8+ with pytest
echo   - pytest-cov for coverage
echo   - pytest-html for HTML reports
echo   - pytest-json-report for JSON reports
echo.
exit /b 1