@echo off
REM Windows Batch Script for Merging Test Results
REM Equivalent to merge-test-results.sh for Windows environments

setlocal enabledelayedexpansion

REM Default values
set FRONTEND_DIR=frontend
set BACKEND_DIR=backend
set OUTPUT_DIR=coverage
set TEMP_DIR=%TEMP%\test_merge_%RANDOM%

REM Parse command line arguments
:parse_args
if "%~1"=="" goto :main
if "%~1"=="--frontend-dir" (
    set FRONTEND_DIR=%~2
    shift
    shift
    goto :parse_args
)
if "%~1"=="--backend-dir" (
    set BACKEND_DIR=%~2
    shift
    shift
    goto :parse_args
)
if "%~1"=="--output-dir" (
    set OUTPUT_DIR=%~2
    shift
    shift
    goto :parse_args
)
if "%~1"=="--help" (
    goto :show_help
)

echo Unknown argument: %~1
goto :show_help

:main
echo 🔄 Merging Test Results on Windows
echo ================================

REM Create temporary directory
if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

REM Ensure output directory exists
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo 📁 Working directories:
echo   Frontend: %FRONTEND_DIR%
echo   Backend:  %BACKEND_DIR%
echo   Output:   %OUTPUT_DIR%
echo   Temp:     %TEMP_DIR%
echo.

REM Step 1: Merge frontend test results
echo 📋 Processing frontend test results...
set FRONTEND_MERGED=false

if exist "%FRONTEND_DIR%\coverage" (
    echo 🔍 Found frontend coverage directory

    REM Find frontend shard coverage directories
    set SHARD_COUNT=0
    for /d %%d in ("%FRONTEND_DIR%\coverage\shard-*") do (
        set /a SHARD_COUNT+=1
        echo 📊 Found shard: %%d
    )

    if %SHARD_COUNT% gtr 0 (
        echo 🎯 Merging %SHARD_COUNT% frontend coverage shards...

        REM Use PowerShell to merge coverage JSON files
        powershell -ExecutionPolicy Bypass -File "%~dp0merge-coverage-ps1" ^
            --input-dir "%FRONTEND_DIR%\coverage" ^
            --output-dir "%OUTPUT_DIR%\frontend" ^
            --temp-dir "%TEMP_DIR%\frontend"

        if !errorlevel! equ 0 (
            set FRONTEND_MERGED=true
            echo ✅ Frontend coverage merged successfully
        ) else (
            echo ❌ Frontend coverage merge failed
        )
    ) else (
        echo ℹ️  No frontend coverage shards found, copying existing coverage...
        if exist "%FRONTEND_DIR%\coverage\coverage-final.json" (
            copy "%FRONTEND_DIR%\coverage\coverage-final.json" "%OUTPUT_DIR%\frontend\coverage-final.json" >nul
            copy "%FRONTEND_DIR%\coverage\lcov.info" "%OUTPUT_DIR%\frontend\lcov.info" >nul 2>&1
            set FRONTEND_MERGED=true
            echo ✅ Frontend coverage copied
        )
    )
) else (
    echo ⚠️  No frontend coverage directory found
)

echo.

REM Step 2: Merge backend test results
echo 📋 Processing backend test results...
set BACKEND_MERGED=false

if exist "%BACKEND_DIR%\coverage" (
    echo 🔍 Found backend coverage directory

    REM Find backend shard coverage directories
    set SHARD_COUNT=0
    for /d %%d in ("%BACKEND_DIR%\coverage\backend\shard-*") do (
        set /a SHARD_COUNT+=1
        echo 📊 Found shard: %%d
    )

    if %SHARD_COUNT% gtr 0 (
        echo 🎯 Merging %SHARD_COUNT% backend coverage shards...

        REM Use PowerShell to merge backend coverage
        powershell -ExecutionPolicy Bypass -File "%~dp0merge-backend-coverage-ps1" ^
            --input-dir "%BACKEND_DIR%\coverage\backend" ^
            --output-dir "%OUTPUT_DIR%\backend" ^
            --temp-dir "%TEMP_DIR%\backend"

        if !errorlevel! equ 0 (
            set BACKEND_MERGED=true
            echo ✅ Backend coverage merged successfully
        ) else (
            echo ❌ Backend coverage merge failed
        )
    ) else (
        echo ℹ️  No backend coverage shards found, copying existing coverage...
        if exist "%BACKEND_DIR%\coverage.xml" (
            copy "%BACKEND_DIR%\coverage.xml" "%OUTPUT_DIR%\backend\coverage.xml" >nul
            set BACKEND_MERGED=true
            echo ✅ Backend coverage copied
        )
    )
) else (
    echo ⚠️  No backend coverage directory found
)

echo.

REM Step 3: Merge JUnit XML results
echo 📋 Processing JUnit XML results...
set JUNIT_MERGED=false

REM Find all JUnit XML files
set JUNIT_FILES=0
for %%f in ("%FRONTEND_DIR%\junit*.xml" "%BACKEND_DIR%\junit*.xml" "%TEMP_DIR%\**\junit*.xml") do (
    if exist "%%f" (
        copy "%%f" "%TEMP_DIR%\junit_!JUNIT_FILES!.xml" >nul
        set /a JUNIT_FILES+=1
    )
)

if %JUNIT_FILES% gtr 0 (
    echo 🎯 Merging %JUNIT_FILES% JUnit XML files...

    REM Use PowerShell to merge JUnit results
    powershell -ExecutionPolicy Bypass -File "%~dp0merge-junit-ps1" ^
        --input-dir "%TEMP_DIR%" ^
        --output-file "%OUTPUT_DIR%\junit-merged.xml"

    if !errorlevel! equ 0 (
        set JUNIT_MERGED=true
        echo ✅ JUnit XML merged successfully
    ) else (
        echo ❌ JUnit XML merge failed
    )
) else (
    echo ℹ️  No JUnit XML files found
)

echo.

REM Step 4: Generate comprehensive test summary
echo 📊 Generating test summary...

REM Create JSON summary using PowerShell
powershell -ExecutionPolicy Bypass -Command ^
    "$frontendMerged = '%FRONTEND_MERGED%' -eq 'true'; ^
    $backendMerged = '%BACKEND_MERGED%' -eq 'true'; ^
    $junitMerged = '%JUNIT_MERGED%' -eq 'true'; ^
    ^
    $summary = @{ ^
        timestamp = Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ'; ^
        platform = 'windows'; ^
        merge_results = @{ ^
            frontend = @{ merged = $frontendMerged }; ^
            backend = @{ merged = $backendMerged }; ^
            junit = @{ merged = $junitMerged } ^
        }; ^
        output_directory = '%OUTPUT_DIR%' ^
    }; ^
    ^
    $summary | ConvertTo-Json -Depth 10 | Out-File -FilePath '%OUTPUT_DIR%\test-summary.json' -Encoding utf8; ^
    Write-Host '✅ Test summary generated'"

echo.

REM Step 5: Generate HTML report
echo 📄 Generating HTML report...

powershell -ExecutionPolicy Bypass -Command ^
    "$summary = Get-Content '%OUTPUT_DIR%\test-summary.json' ^| ConvertFrom-Json; ^
    ^
    $html = @\" ^
    <!DOCTYPE html> ^
    <html> ^
    <head> ^
        <title>Test Results Summary</title> ^
        <style> ^
            body { font-family: Arial, sans-serif; margin: 20px; } ^
            .header { background-color: #f0f0f0; padding: 20px; border-radius: 5px; } ^
            .section { margin: 20px 0; } ^
            .success { color: #28a745; } ^
            .failure { color: #dc3545; } ^
            .warning { color: #ffc107; } ^
            .badge { padding: 4px 8px; border-radius: 3px; color: white; } ^
            .badge-success { background-color: #28a745; } ^
            .badge-failure { background-color: #dc3545; } ^
            .badge-warning { background-color: #ffc107; color: #000; } ^
            table { border-collapse: collapse; width: 100%%; } ^
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; } ^
            th { background-color: #f2f2f2; } ^
        </style> ^
    </head> ^
    <body> ^
        <div class='header'> ^
            <h1>🧪 Test Results Summary</h1> ^
            <p>Generated on: $($summary.timestamp)</p> ^
            <p>Platform: $($summary.platform)</p> ^
        </div> ^
        ^
        <div class='section'> ^
            <h2>📊 Merge Results</h2> ^
            <table> ^
                <tr><th>Component</th><th>Status</th><th>Details</th></tr> ^
                <tr> ^
                    <td>Frontend Coverage</td> ^
                    <td><span class='badge @(if($summary.merge_results.frontend.merged) { 'badge-success' } else { 'badge-failure' })'>@(if($summary.merge_results.frontend.merged) { '✅ Merged' } else { '❌ Failed' })</span></td> ^
                    <td>$(if($summary.merge_results.frontend.merged) { 'Successfully merged frontend coverage reports' } else { 'Failed to merge frontend coverage reports' })</td> ^
                </tr> ^
                <tr> ^
                    <td>Backend Coverage</td> ^
                    <td><span class='badge @(if($summary.merge_results.backend.merged) { 'badge-success' } else { 'badge-failure' })'>@(if($summary.merge_results.backend.merged) { '✅ Merged' } else { '❌ Failed' })</span></td> ^
                    <td>$(if($summary.merge_results.backend.merged) { 'Successfully merged backend coverage reports' } else { 'Failed to merge backend coverage reports' })</td> ^
                </tr> ^
                <tr> ^
                    <td>JUnit Reports</td> ^
                    <td><span class='badge @(if($summary.merge_results.junit.merged) { 'badge-success' } else { 'badge-failure' })'>@(if($summary.merge_results.junit.merged) { '✅ Merged' } else { '❌ Failed' })</span></td> ^
                    <td>$(if($summary.merge_results.junit.merged) { 'Successfully merged JUnit XML reports' } else { 'Failed to merge JUnit XML reports' })</td> ^
                </tr> ^
            </table> ^
        </div> ^
        ^
        <div class='section'> ^
            <h2>📁 Output Files</h2> ^
            <ul> ^
                <li><a href='test-summary.json'>test-summary.json</a> - Test merge summary (JSON)</li> ^
    \" @; ^
    ^
    if (Test-Path '%OUTPUT_DIR%\frontend\coverage-final.json') { $html += \"                <li><a href='frontend/coverage-final.json'>frontend/coverage-final.json</a> - Frontend coverage</li>\n\"; } ^
    if (Test-Path '%OUTPUT_DIR%\backend\coverage.xml') { $html += \"                <li><a href='backend/coverage.xml'>backend/coverage.xml</a> - Backend coverage</li>\n\"; } ^
    if (Test-Path '%OUTPUT_DIR%\junit-merged.xml') { $html += \"                <li><a href='junit-merged.xml'>junit-merged.xml</a> - Merged JUnit results</li>\n\"; } ^
    ^
    $html += @\" ^
            </ul> ^
        </div> ^
    </body> ^
    </html> ^
    \"@; ^
    ^
    $html | Out-File -FilePath '%OUTPUT_DIR%\test-summary.html' -Encoding utf8; ^
    Write-Host '✅ HTML report generated'"

echo.

REM Step 6: Display final summary
echo 🏁 Test Results Merge Complete
echo ==============================

echo 📊 Merge Status:
if "%FRONTEND_MERGED%"=="true" (
    echo   ✅ Frontend: Merged
) else (
    echo   ❌ Frontend: Failed/Not Found
)

if "%BACKEND_MERGED%"=="true" (
    echo   ✅ Backend: Merged
) else (
    echo   ❌ Backend: Failed/Not Found
)

if "%JUNIT_MERGED%"=="true" (
    echo   ✅ JUnit: Merged
) else (
    echo   ❌ JUnit: Failed/Not Found
)

echo.
echo 📁 Generated Files:
if exist "%OUTPUT_DIR%\test-summary.json" (
    echo   📄 test-summary.json
)
if exist "%OUTPUT_DIR%\test-summary.html" (
    echo   🌐 test-summary.html
)
if exist "%OUTPUT_DIR%\frontend\coverage-final.json" (
    echo   📊 frontend\coverage-final.json
)
if exist "%OUTPUT_DIR%\backend\coverage.xml" (
    echo   📊 backend\coverage.xml
)
if exist "%OUTPUT_DIR%\junit-merged.xml" (
    echo   📋 junit-merged.xml
)

echo.
echo 📂 Output Directory: %OUTPUT_DIR%

REM Cleanup
if exist "%TEMP_DIR%" (
    rmdir /s /q "%TEMP_DIR%" 2>nul
)

REM Determine exit code
if "%FRONTEND_MERGED%"=="true" goto :success
if "%BACKEND_MERGED%"=="true" goto :success
if "%JUNIT_MERGED%"=="true" goto :success

echo ⚠️  No test results were successfully merged
exit /b 1

:success
echo ✅ Test results merge completed successfully
exit /b 0

:show_help
echo.
echo Merge Test Results (Windows)
echo ===========================
echo.
echo Usage: merge-test-results.bat [options]
echo.
echo Options:
echo   --frontend-dir DIR     Frontend directory (default: frontend)
echo   --backend-dir DIR      Backend directory (default: backend)
echo   --output-dir DIR       Output directory (default: coverage)
echo   --help                 Show this help message
echo.
echo Description:
echo   This script merges test results from multiple shards into a single report.
echo   It processes frontend Jest coverage, backend pytest coverage, and JUnit XML results.
echo.
echo Examples:
echo   merge-test-results.bat
echo   merge-test-results.bat --frontend-dir src\frontend --backend-dir src\backend
echo   merge-test-results.bat --output-dir reports\coverage
echo.
echo Output Files:
echo   test-summary.json      JSON summary of merge results
echo   test-summary.html      HTML report with test results
echo   frontend/coverage*     Merged frontend coverage files
echo   backend/coverage*      Merged backend coverage files
echo   junit-merged.xml       Merged JUnit XML results
echo.
exit /b 1