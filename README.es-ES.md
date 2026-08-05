## Cómo ejecutar

### Cómo ejecutar localmente
1. Instala [Python 3.12+](https://www.python.org/downloads/), [uv](https://docs.astral.sh/uv/) y [Docker](https://docs.docker.com/engine/install/).
2. Instala las dependencias del proyecto con [uv](https://docs.astral.sh/uv/cli/#install) usando el siguiente comando:
   ```bash
   uv sync
   ```
3. Copia el archivo `settings.example.yaml` a `settings.yaml` y añade el token:
   ```bash
   cp settings.example.yaml settings.yaml
   ```
4. Inicia la base de datos PostgreSQL con Docker:
   ```bash
   docker compose up db
   ```
5. Inicia el servidor de desarrollo desde el directorio backend:
   ```bash
   cd backend
   uv run -m src.api
   ```

> [!IMPORTANTE]
> Para acceder a los endpoints que requieren autenticación, haz clic en el botón "Authorize" en la interfaz de Swagger UI.

> [!CONSEJO]
> Modifica el archivo `settings.yaml` según tus necesidades. Puedes consultar el esquema en [settings.schema.yaml](settings.schema.yaml).

### Cómo ejecutar en Docker
1. Copia el archivo de configuración: `cp settings.example.yaml settings.yaml`.
2. Ajusta la configuración en `settings.yaml` según tus necesidades
   (consulta [settings.schema.yaml](settings.schema.yaml) para más detalles).
3. Instala Docker con Docker Compose.
4. Construye y ejecuta el contenedor Docker con el siguiente comando:
   `docker compose up --build`.


## Generación de código
> [!CONSEJO]
> El proyecto incluye un generador sencillo de código CRUD. Para más información, consulta el [README correspondiente](fastapi_crud_generator/README.md).
