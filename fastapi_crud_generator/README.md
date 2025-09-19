# Fast API CRUD Generator

## Note:
This script is not fully tested yet, please report all problems you encounter on the [GitHub issues page.](https://github.com/ZolotarevAlexandr/fast_api_hackathon_template/issues)

## Description
A small template-driven FastAPI CRUD code generator that scaffolds 
Pydantic v2 schemas, SQLAlchemy 2.0 models, async repositories, 
and APIRouter endpoints, then wires them into the app and runs Ruff fixes

### What gets generated
- Schema file at `src/schemas/{module}.py` with Create and Response models.
- Model file at `src/db/models/{module}.py` using typed declarative mapping with Mapped[...] and mapped_column(...).
- Repository file at `src/db/repositories/{module}.py` with async CRUD methods returning ORM instances.
- Routes file at `src/api/{module}/routes.py` containing POST, GET list, GET by id, PATCH, and DELETE endpoints.

Remember that you still need to generate database migration using `uv run alembic revision --autogenerate -m "{your message}"`
(Script not generating migration is intended behaviour and is not a bug)  
And apply it with `uv run alembic upgrade head`. (It will also be applied automatically on the server start)

## Usage
Command structure:
```bash
uv run python -m fastapi_crud_generator generate ModelName field_name:field_type[:params]
```
Example:
```bash
uv run python -m fastapi_crud_generator generate Book title:str:unique author_email:email year:int:nullable in_stock:bool:default=True
```
