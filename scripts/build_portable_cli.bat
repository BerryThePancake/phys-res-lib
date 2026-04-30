@echo off
setlocal EnableExtensions
cd /d "%~dp0.."

set "DIST=%CD%\dist"
if not exist "%DIST%" mkdir "%DIST%"

set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if not exist "%VSWHERE%" (
    echo [ERROR] vswhere.exe not found. Install "Desktop development with C++" or Build Tools.
    exit /b 1
)

for /f "usebackq tokens=*" %%i in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "VSINSTALL=%%i"
if not defined VSINSTALL (
    echo [ERROR] MSVC toolset not found via vswhere.
    exit /b 1
)

call "%VSINSTALL%\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] vcvars64.bat failed.
    exit /b 1
)

echo Building portable physresidual_cli.exe (static CRT /MT, single exe)...
cl /nologo /O2 /W3 /DPHYSRESIDUAL_STATIC /MT /I include ^
    tools\physresidual_cli.c src\physresidual.c ^
    /Fe"%DIST%\physresidual_cli.exe" /Fo"%DIST%\\" /link /SUBSYSTEM:CONSOLE
if errorlevel 1 exit /b 1

echo OK: "%DIST%\physresidual_cli.exe"
"%DIST%\physresidual_cli.exe" version
exit /b 0
