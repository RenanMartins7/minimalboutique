@echo off
REM Interrompe se algum comando falhar
setlocal enabledelayedexpansion
echo.

echo Building and pushing momosuke07/backend:latest...
docker build -t momosuke07/backend:latest -f Dockerfile.backend .
if errorlevel 1 exit /b 1
docker push momosuke07/backend:latest
if errorlevel 1 exit /b 1

echo Building and pushing momosuke07/frontend:latest...
docker build -t momosuke07/frontend:latest -f Dockerfile.frontend .
if errorlevel 1 exit /b 1
docker push momosuke07/frontend:latest
if errorlevel 1 exit /b 1

echo Building and pushing momosuke07/products:latest...
docker build -t momosuke07/products:latest -f backend/products/Dockerfile ./backend
if errorlevel 1 exit /b 1
docker push momosuke07/products:latest
if errorlevel 1 exit /b 1

echo Building and pushing momosuke07/orders:latest...
docker build -t momosuke07/orders:latest -f backend/orders/Dockerfile ./backend
if errorlevel 1 exit /b 1
docker push momosuke07/orders:latest
if errorlevel 1 exit /b 1

echo Building and pushing momosuke07/checkout:latest...
docker build -t momosuke07/checkout:latest -f backend/checkout/Dockerfile ./backend
if errorlevel 1 exit /b 1
docker push momosuke07/checkout:latest
if errorlevel 1 exit /b 1

echo Building and pushing momosuke07/payment:latest...
docker build -t momosuke07/payment:latest -f backend/payment/Dockerfile ./backend
if errorlevel 1 exit /b 1
docker push momosuke07/payment:latest
if errorlevel 1 exit /b 1

echo Building and pushing momosuke07/cart:latest...
docker build -t momosuke07/cart:latest -f backend/cart/Dockerfile ./backend
if errorlevel 1 exit /b 1
docker push momosuke07/cart:latest
if errorlevel 1 exit /b 1

echo Building and pushing momosuke07/loadgenerator:latest...
docker build -t momosuke07/loadgenerator:latest -f loadgenerator/Dockerfile ./loadgenerator
