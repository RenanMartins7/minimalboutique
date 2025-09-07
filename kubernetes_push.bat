@echo off
REM Interrompe se algum comando falhar
setlocal enabledelayedexpansion
echo.

echo Applying deploy_backend.yml...
kubectl apply -f deploy_backend.yml
if errorlevel 1 exit /b 1

echo Applying deploy_cart.yml...
kubectl apply -f deploy_cart.yml
if errorlevel 1 exit /b 1

echo Applying deploy_checkout.yml...
kubectl apply -f deploy_checkout.yml
if errorlevel 1 exit /b 1

echo Applying deploy_orders.yml...
kubectl apply -f deploy_orders.yml
if errorlevel 1 exit /b 1

echo Applying deploy_payment.yml...
kubectl apply -f deploy_payment.yml
if errorlevel 1 exit /b 1

echo Applying deploy_products.yml...
kubectl apply -f deploy_products.yml
if errorlevel 1 exit /b 1

echo.
echo All manifests applied successfully!
pause
