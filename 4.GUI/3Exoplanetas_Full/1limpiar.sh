#!/bin/bash

echo "======================================"
echo " LIMPIANDO DOCKER"
echo "======================================"

echo "[1/5] Deteniendo todos los contenedores..."
sudo docker stop $(sudo docker ps -aq) 2>/dev/null || true

echo "[2/5] Eliminando todos los contenedores..."
sudo docker rm -f $(sudo docker ps -aq) 2>/dev/null || true

echo "[3/5] Eliminando todas las imágenes..."
sudo docker rmi -f $(sudo docker images -aq) 2>/dev/null || true

echo "[4/5] Eliminando todos los volúmenes..."
sudo docker volume rm $(sudo docker volume ls -q) 2>/dev/null || true

echo "[5/5] Limpiando redes, caché y recursos..."
sudo docker system prune -a --volumes -f

echo ""
echo "======================================"
echo " DOCKER LIMPIO"
echo "======================================"

echo "Contenedores:"
sudo docker ps -a

echo ""
echo "Imágenes:"
sudo docker images

echo ""
echo "Volúmenes:"
sudo docker volume ls