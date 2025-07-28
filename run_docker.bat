@echo off
echo PDF Outline Extractor
echo =====================

REM Check if Docker is installed
docker --version > nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: Docker is not installed or not in PATH.
    echo Please install Docker Desktop from https://www.docker.com/products/docker-desktop
    exit /b 1
)

echo Building Docker image...
docker build -t pdf-outline-extractor .

if %ERRORLEVEL% neq 0 (
    echo Error: Failed to build Docker image.
    exit /b 1
)

echo.
echo Docker image built successfully!
echo.
echo To process PDF files, place them in the 'input' folder and run:
echo docker run --rm -v "%CD%\input:/app/input" -v "%CD%\output:/app/output" pdf-outline-extractor
echo.
echo Results will be saved in the 'output' folder.

REM Ask if user wants to run the container now
set /p RUN_NOW=Do you want to process PDFs in the input folder now? (y/n): 

if /i "%RUN_NOW%"=="y" (
    echo Processing PDFs in input folder...
    docker run --rm -v "%CD%\input:/app/input" -v "%CD%\output:/app/output" pdf-outline-extractor
    echo Done! Check the output folder for results.
) else (
    echo Exiting without processing.
)

pause