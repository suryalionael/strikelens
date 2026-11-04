# app/routes/

FastAPI routers, one module per resource: `fighters.py`, `fights.py`, `tags.py`.
`common.py` holds shared helpers. Routes parse input, read and write the database,
and return Pydantic models. No stat logic here.
