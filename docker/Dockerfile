# Dockerfile para la aplicación de Marketing Automatizado con IA
FROM python:3.11-slim

# Evitar prompts interactivos durante la instalación
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Instalar dependencias del sistema requeridas para MoviePy, OpenCV/PIL y procesamiento multimedia
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1 \
    fonts-dejavu-core \
    fonts-freefont-ttf \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar archivo de requerimientos e instalar dependencias de Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Crear estructura de directorios multimedia requeridos con permisos de lectura/escritura completos
RUN mkdir -p /app/media/uploads \
             /app/media/generated_images \
             /app/media/videos && \
    chmod -R 777 /app/media

# Copiar el código fuente de la aplicación
COPY app/ /app/app/

# Exponer el puerto de la aplicación (8001)
EXPOSE 8001

# Comando de inicio del servidor ASGI Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]

