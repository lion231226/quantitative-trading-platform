@echo off
REM Windows Batch Script for Frontend Test Sharding
REM Equivalent to run-frontend-shard.sh for Windows environments

setlocal enabledelayedexpansion

REM Default values
set SHARD_INDEX=1
set TOTAL_SHARDS=2
set TEST_PATTERN=**/*.test.{js,jsx,ts,tsx}

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
if "%~1"=="--help" (
    goto :show_help
)

echo Unknown argument: %~1
goto :show_help

:run_tests
echo 🚀 Running Frontend Test Shard %SHARD_INDEX%/%TOTAL_SHARDS% on Windows
echo ===============================================
echo.

REM Check if we're in the correct directory
if not exist "package.json" (
    echo ❌ Error: package.json not found. Please run this script from the frontend directory.
    exit /b 1
)

REM Check Node.js installation
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Node.js not found. Please install Node.js and try again.
    exit /b 1
)

REM Set environment variables for sharding
set CI=true
set NODE_ENV=test
set SHARD_INDEX=%SHARD_INDEX%
set TOTAL_SHARDS=%TOTAL_SHARDS%

REM Calculate test files for this shard
echo 📊 Discovering test files for shard %SHARD_INDEX%...

REM Create temp file for test listing
set TEMP_TEST_LIST=%TEMP%\frontend_test_list_%RANDOM%.txt

REM Use PowerShell to find and distribute test files
powershell -Command ^
    "$testFiles = Get-ChildItem -Path '.' -Recurse -Include '*.test.js','*.test.jsx','*.test.ts','*.test.tsx' | ^
                Where-Object { $_.FullName -notlike '*node_modules*' -and $_.FullName -not_like '*\.next*' -and $_.FullName -not-like '*coverage*' } | ^
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

REM Create Jest configuration file for this shard
set JEST_CONFIG_FILE=jest.config.shard%SHARD_INDEX%.js

echo 📝 Creating Jest configuration for shard %SHARD_INDEX%...

(
echo module.exports = {
echo   // Extend the main Jest configuration
echo   ...require('./jest.config.js'),
echo
echo   // Sharding configuration
echo   testMatch: [
echo     '**/!(*node_modules+*)/+(*.)+(spec|test).[jt]s?(x)'
echo   ],
echo
echo   // Test runner configuration
echo   testRunner: 'jest-circus/runner',
echo   maxWorkers: 1,
echo   verbose: true,
echo
echo   // Coverage configuration
echo   collectCoverage: true,
echo   coverageDirectory: 'coverage/shard-%SHARD_INDEX%',
echo   coverageReporters: ['json', 'lcov', 'text-summary'],
echo
echo   // Custom test sequencer for sharding
echo   testSequencer: class ShardSequencer {
echo     sort(tests) {
echo       const shardIndex = %SHARD_INDEX%;
echo       const totalShards = %TOTAL_SHARDS%;
echo
echo       // Read test files list from temp file
echo       const fs = require('fs');
echo       const path = require('path');
echo
echo       let shardFiles = [];
echo       try {
echo         const content = fs.readFileSync('%TEMP_TEST_LIST%', 'utf8');
echo         shardFiles = content.trim().split('\n').filter(Boolean);
echo       } catch (error) {
echo         console.error('Error reading test list:', error);
echo       }
echo
echo       // Sort tests: files in this shard first, then others
echo       return tests.sort((a, b) => {
echo         const aInShard = shardFiles.includes(path.resolve(a.path));
echo         const bInShard = shardFiles.includes(path.resolve(b.path));
echo
echo         if (aInShard && !bInShard) return -1;
echo         if (!aInShard && bInShard) return 1;
echo         return 0;
echo       });
echo     }
echo   },
echo
echo   // Custom test environment
echo   testEnvironment: 'jsdom',
echo   setupFilesAfterEnv: ['<rootDir>/jest.setup.js']
echo };
) > "%JEST_CONFIG_FILE%"

echo ⚙️  Jest configuration created: %JEST_CONFIG_FILE%
echo.

REM Run the tests
echo 🧪 Executing tests for shard %SHARD_INDEX%...
echo ================================================

REM Set additional environment variables
set CI_SHARD_INDEX=%SHARD_INDEX%
set CI_TOTAL_SHARDS=%TOTAL_SHARDS%
set JEST_CONFIG=%JEST_CONFIG_FILE%

REM Run Jest with the shard configuration
npx jest --config="%JEST_CONFIG_FILE%" --passWithNoTests --detectOpenHandles --forceExit

set JEST_EXIT_CODE=%ERRORLEVEL%

REM Cleanup temporary files
if exist "%TEMP_TEST_LIST%" del "%TEMP_TEST_LIST%"
if exist "%JEST_CONFIG_FILE%" del "%JEST_CONFIG_FILE%"

echo.
echo 📊 Shard %SHARD_INDEX% execution completed with exit code: %JEST_EXIT_CODE%

REM Generate shard summary
if exist "coverage\shard-%SHARD_INDEX%\coverage-summary.json" (
    echo 📈 Coverage report generated for shard %SHARD_INDEX%

    REM Extract coverage metrics
    powershell -Command ^
        "try { ^
            $coverage = Get-Content 'coverage\shard-%SHARD_INDEX%\coverage-summary.json' ^| ConvertFrom-Json; ^
            $total = $coverage.total; ^
            Write-Host '📊 Coverage Summary for Shard %SHARD_INDEX%:'; ^
            Write-Host \"   Lines: $([Math]::Round($total.lines.pct))%% ($($total.lines.covered)/$($total.lines.total))\"; ^
            Write-Host \"   Functions: $([Math]::Round($total.functions.pct))%% ($($total.functions.covered)/$($total.functions.total))\"; ^
            Write-Host \"   Branches: $([Math]::Round($total.branches.pct))%% ($($total.branches.covered)/$($total.branches.total))\"; ^
            Write-Host \"   Statements: $([Math]::Round($total.statements.pct))%% ($($total.statements.covered)/$($total.statements.total))\"; ^
        } catch { ^
            Write-Host '⚠️  Could not parse coverage summary'; ^
        }"
) else (
    echo ⚠️  No coverage report generated for shard %SHARD_INDEX%
)

echo.
if %JEST_EXIT_CODE% equ 0 (
    echo ✅ Frontend test shard %SHARD_INDEX% completed successfully
) else (
    echo ❌ Frontend test shard %SHARD_INDEX% failed with exit code %JEST_EXIT_CODE%
)

exit /b %JEST_EXIT_CODE%

:show_help
echo.
echo Frontend Test Shard Runner (Windows)
echo ===================================
echo.
echo Usage: run-frontend-shard.bat [options]
echo.
echo Options:
echo   --shard-index INDEX     Shard index (1-based, default: 1)
echo   --total-shards COUNT    Total number of shards (default: 2)
echo   --pattern PATTERN       Test file pattern (default: **/*.test.{js,jsx,ts,tsx})
echo   --help                  Show this help message
echo.
echo Examples:
echo   run-frontend-shard.bat
echo   run-frontend-shard.bat --shard-index 1 --total-shards 4
echo   run-frontend-shard.bat --shard-index 2 --total-shards 4
echo.
echo Environment Variables:
echo   CI                      Set to 'true' for CI mode
echo   NODE_ENV                Test environment (default: test)
echo   JEST_CONFIG             Custom Jest configuration file
echo.
exit /b 1