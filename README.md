# Marketing Automatizado para Empresas con IA, Generación Multimedia y TikTok v2

> **Laboratorio 5 - Pregunta 2**  
> Solución completa, modular y lista para producción para la creación autónoma de campañas de marketing multimedia con IA ultraliviana (Gemini 1.5 Flash), síntesis de imágenes (Pollinations.ai), compilación de video vertical 9:16 (MoviePy / FFmpeg) y despliegue en redes sociales mediante **TikTok Content Posting API v2**.

---

## 🌟 Arquitectura del Sistema

```text
marketing-campaign-app/
├── app/
│   ├── presentation/
│   │   ├── static/             # CSS moderno, JS para drag-and-drop y animaciones
│   │   ├── templates/          # Jinja2: base, index, select_script, view_campaign, history
│   │   └── routes.py           # Endpoints FastAPI y controladores
│   ├── business_logic/
│   │   ├── script_service.py   # LLM Gemini (gemini-1.5-flash) con mínimo consumo de tokens & fallback
│   │   ├── media_service.py    # Pollinations.ai (3 fotos) + MoviePy / FFmpeg (video vertical 9:16)
│   │   └── tiktok_service.py   # OAuth 2.0 y Content Posting API v2 (FILE_UPLOAD + Sandbox Mode)
│   ├── data_access/
│   │   ├── database.py         # Conexión SQLAlchemy y pool de PostgreSQL
│   │   ├── models.py           # Modelos ORM: Campaign, Script, MediaAsset, Publication, TikTokAuth
│   │   └── repositories.py     # Patrón Repository para persistencia desacoplada
│   ├── media/                  # Volumen compartido para uploads, imágenes generadas y videos
│   │   ├── uploads/
│   │   ├── generated_images/
│   │   └── videos/
│   ├── config.py               # Pydantic Settings y resolución de directorios
│   └── main.py                 # Punto de entrada ASGI FastAPI y eventos de ciclo de vida
├── docker/
│   ├── Dockerfile              # Python 3.11-slim + FFmpeg + librerías gráficas
│   └── .dockerignore
├── docker-compose.yml          # Orquestación app (8001:8001) + PostgreSQL 15 con healthcheck
├── .env.example                # Plantilla de variables de entorno
├── requirements.txt            # Dependencias fijadas y compatibles
└── README.md
```

---

## 🚀 Requerimientos Funcionales Implementados

1. **Recepción de Foto y Datos**:
   - Formulario web interactivo con Drag & Drop y previsualización instantánea.
   - Almacena la fotografía original en `/app/media/uploads/original_{timestamp}_{filename}`.
   - Registra la empresa y su rubro en PostgreSQL.

2. **Propuesta de 3 Guiones con IA Económica (`gemini-1.5-flash`)**:
   - Integración con la API oficial de Google Gemini optimizada para el menor consumo posible de tokens (prompt hiperconciso de entrada y salida JSON estricta de máx 900 tokens).
   - Genera simultáneamente 3 variantes comerciales:
     - **Opción A**: *Enfoque dinámico / viral* (humor, gancho visual rápido de 3s).
     - **Opción B**: *Enfoque profesional / valor* (beneficios, diferenciador de mercado).
     - **Opción C**: *Enfoque promocional / urgencia* (oferta flash, escasez, CTA inmediato).
   - **Fallback Local Blindado**: Si la API Key no está configurada o se agota la cuota (429/ResourceExhausted), el sistema activa automáticamente un generador heurístico local garantizando que la aplicación jamás se quede congelada ni arroje error 500.

3. **Selección del Guion**:
   - Pantalla interactiva (`select_script.html`) que presenta las 3 propuestas lado a lado con ganchos, locución, llamada a la acción y visualización de escenas. Selección en un solo clic.

4. **Generación Multimedia (3 Fotos y 1 Video MP4)**:
   - **3 Fotos**: Llama directamente a la API gratuita de **Pollinations.ai** utilizando prompts descriptivos en inglés generados por el guion. Se guardan en `/app/media/generated_images/`.
   - **1 Video MP4 Vertical (9:16)**:
     - Formato vertical nativo para TikTok / Reels (`720x1280` a `24fps`).
     - Renderiza subtítulos y badges de marca de alto contraste en el tercio inferior usando Pillow sobre cada escena.
     - Une las 3 imágenes cronometradas con **MoviePy** y codificación `libx264`.
     - Incluye fallback automático a **FFmpeg CLI nativo**.
     - Guarda el video compilado en `/app/media/videos/campaign_{id}.mp4`.

5. **Despliegue en Red Social (TikTok Content Posting API v2)**:
   - Endpoint `/auth/tiktok/login`: Inicia el flujo OAuth 2.0 redirigiendo con scope `video.publish`.
   - Endpoint `/auth/tiktok/callback`: Recibe el `code`, intercambia por `access_token` y `open_id`, y lo persiste en PostgreSQL.
   - Endpoint `/campaigns/{id}/publish/tiktok`: Ejecuta el protocolo `FILE_UPLOAD` hacia `https://open.tiktokapis.com/v2/post/publish/video/init/` subiendo los bytes binarios del video vertical generado.
   - Flag `TIKTOK_SANDBOX_MODE=true`: En caso de pruebas locales o credenciales no verificadas por TikTok, simula el handshake devolviendo un `publish_id` exitoso y persiste la publicación en PostgreSQL.

6. **Persistencia en Base de Datos**:
   - PostgreSQL 15 gestiona:
     - `campaigns`: Datos de la empresa, rubro, rutas y estados (`CREATED`, `SCRIPTS_GENERATED`, `MEDIA_GENERATED`, `PUBLISHED`).
     - `scripts`: Las 3 propuestas generadas y el guion seleccionado.
     - `media_assets`: Registro de fotos originales, imágenes generadas de Pollinations y videos MP4.
     - `publications`: ID de post en TikTok, fecha, estado `PUBLISHED` y payload de respuesta.
     - `tiktok_auth`: Tokens de acceso OAuth 2.0 y Open ID.

---

## ⚙️ Configuración y Variables de Entorno

Copia el archivo `.env.example` a `.env`:

```bash
cp .env.example .env
```

Contenido de `.env`:

```env
PORT=8001
GEMINI_API_KEY=tu_api_key_de_gemini
GEMINI_MODEL=gemini-1.5-flash
TIKTOK_CLIENT_KEY=tu_client_key_de_tiktok
TIKTOK_CLIENT_SECRET=tu_client_secret_de_tiktok
TIKTOK_REDIRECT_URI=http://localhost:8001/auth/tiktok/callback
TIKTOK_SANDBOX_MODE=true
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=marketing_db
DB_HOST=db
DB_PORT=5432
```

> **Nota sobre el puerto**: La aplicación se ejecuta en el puerto **8001** para convivir sin conflictos con otros servicios locales en el puerto 8000.

---

## 🐳 Ejecución con Docker Compose

Para levantar el entorno completo (Base de datos PostgreSQL + Aplicación FastAPI + FFmpeg + Volúmenes persistentes):

```bash
# Construir y levantar contenedores en segundo plano
docker compose up --build -d

# Ver registros en tiempo real
docker compose logs -f app
```

Una vez levantado, accede desde tu navegador:
👉 **http://localhost:8001**

### Estado de los Servicios
- **Aplicación Web**: [http://localhost:8001](http://localhost:8001)
- **Documentación OpenAPI (Swagger)**: [http://localhost:8001/docs](http://localhost:8001/docs)
- **Healthcheck**: [http://localhost:8001/health](http://localhost:8001/health)

Para detener los servicios:
```bash
docker compose down
```

---

## 🧪 Flujo de Prueba Paso a Paso

1. **Ingresar a http://localhost:8001**:
   - Nombre de Empresa: `Burger Station Gourmet`
   - Rubro: `Gastronomía Artesanal`
   - Sube una fotografía de una hamburguesa o plato.
   - Clic en **"Analizar con Gemini 1.5 Flash y Generar 3 Guiones"**.

2. **Revisar y Seleccionar el Guion**:
   - Observarás las 3 opciones (A: Viral / Humor, B: Profesional / Calidad, C: Promocional Flash).
   - Haz clic en **"Seleccionar Opción A y Crear Video"**.

3. **Generación Multimedia Automática**:
   - El sistema descargará 3 imágenes verticales en Pollinations.ai basadas en los prompts del guion.
   - MoviePy superpondrá los subtítulos y compilará `campaign_1.mp4` a 24fps vertical 9:16.

4. **Visualizar y Publicar en TikTok**:
   - En la vista de la campaña, podrás reproducir el video en el mockup móvil vertical HTML5 y descargar el archivo MP4.
   - Haz clic en **"Publicar Video en TikTok Content Posting API"**.
   - En modo `TIKTOK_SANDBOX_MODE=true`, simulará la publicación, generará el `publish_id` y persistirá el registro con estado `PUBLISHED` en PostgreSQL.
   - En la sección **Historial** (`/campaigns/history`) podrás auditar todas las campañas creadas.

---

## 🛠️ Tecnologías Utilizadas

- **Backend**: Python 3.11, FastAPI, Uvicorn, Jinja2, Pydantic Settings.
- **Base de Datos**: PostgreSQL 15, SQLAlchemy 2.0, Psycopg2.
- **Inteligencia Artificial**: Google Gemini API (`gemini-1.5-flash`), `google-genai` / `google-generativeai`.
- **Generación de Imágenes**: Pollinations.ai API (Flux/SDXL).
- **Procesamiento de Video**: MoviePy 1.0.3, FFmpeg, Pillow (PIL).
- **Redes Sociales**: TikTok Content Posting API v2, OAuth 2.0.
- **Frontend**: Tailwind CSS CDN, Font Awesome 6, Vanilla JS.
- **Infraestructura**: Docker, Docker Compose, Linux Debian Slim.

