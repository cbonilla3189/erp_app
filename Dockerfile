# Imagen base liviana
FROM python:3.11-slim

# Establecer directorio de trabajo
WORKDIR /app

# Copiar dependencias
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Crear directorio para el socket
RUN mkdir -p /run/inventario

# Exponer el socket (solo informativo)
EXPOSE 5000

# Lanzar Gunicorn con socket
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
