# app/models/

- `tables.py`: SQLAlchemy tables. Column names match the shared JSON Schemas.
- `schemas.py`: Pydantic models that mirror `shared/schema/*.json`.

`tests/test_models_match_schema.py` runs the same valid and invalid examples
through the Pydantic models and the JSON Schemas and checks they agree. If you
change a schema, change the model too, and add an example to the test.
