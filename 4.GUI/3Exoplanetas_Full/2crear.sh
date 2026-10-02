#!/bin/bash

echo "======================================"
echo " CREANDO ENTORNO JUPYTER + MYSQL 8.4"
echo "======================================"

# --------------------------------------------------
# VARIABLES
# --------------------------------------------------

NETWORK="ciencia-net"
MYSQL_CONTAINER="mysql84"
JUPYTER_CONTAINER="jupyter"
MYSQL_VOLUME="mysql84-data"

MYSQL_ROOT_PASSWORD="root"
MYSQL_DATABASE="astronomia"

# --------------------------------------------------
# 1. Crear red
# --------------------------------------------------

echo ""
echo "[1/6] Creando red Docker..."

sudo docker network create "$NETWORK" 2>/dev/null || \
echo "La red $NETWORK ya existe."

# --------------------------------------------------
# 2. Crear volumen MySQL
# --------------------------------------------------

echo ""
echo "[2/6] Creando volumen para MySQL..."

sudo docker volume create "$MYSQL_VOLUME" 2>/dev/null || \
echo "El volumen $MYSQL_VOLUME ya existe."

# --------------------------------------------------
# 3. Crear MySQL 8.4
# --------------------------------------------------

echo ""
echo "[3/6] Creando MySQL 8.4..."

sudo docker run -d \
    --name "$MYSQL_CONTAINER" \
    --network "$NETWORK" \
    -p 3306:3306 \
    -e MYSQL_ROOT_PASSWORD="$MYSQL_ROOT_PASSWORD" \
    -e MYSQL_DATABASE="$MYSQL_DATABASE" \
    -v "$MYSQL_VOLUME:/var/lib/mysql" \
    mysql:8.4

# --------------------------------------------------
# 4. Crear Jupyter
# --------------------------------------------------

echo ""
echo "[4/6] Creando Jupyter..."

sudo docker run -d \
    --name "$JUPYTER_CONTAINER" \
    --network "$NETWORK" \
    -p 8888:8888 \
    quay.io/jupyter/scipy-notebook:latest

# --------------------------------------------------
# 5. Esperar a los contenedores
# --------------------------------------------------

echo ""
echo "[5/6] Esperando a que los servicios arranquen..."

sleep 10

# --------------------------------------------------
# 6. Mostrar información
# --------------------------------------------------

echo ""
echo "[6/6] ESTADO DEL ENTORNO"
echo "======================================"

sudo docker ps

echo ""
echo "======================================"
echo " RED DOCKER"
echo "======================================"

sudo docker network inspect "$NETWORK" \
    --format '{{range .Containers}}{{.Name}}{{"\n"}}{{end}}'

echo ""
echo "======================================"
echo " ACCESO A JUPYTER"
echo "======================================"

sudo docker logs "$JUPYTER_CONTAINER" 2>&1 | \
grep -E "http://127.0.0.1:8888|http://localhost:8888" | tail -1

echo ""
echo "======================================"
echo " MYSQL"
echo "======================================"

echo "Host desde Jupyter : mysql84"
echo "Puerto             : 3306"
echo "Usuario             : root"
echo "Password            : $MYSQL_ROOT_PASSWORD"
echo "Base de datos       : $MYSQL_DATABASE"

echo ""
echo "Desde DBeaver:"
echo "Host     : localhost"
echo "Puerto   : 3306"
echo "Database : $MYSQL_DATABASE"
echo "Usuario  : root"
echo "Password : $MYSQL_ROOT_PASSWORD"

echo ""
echo "======================================"
echo " ENTORNO CREADO"
echo "======================================"