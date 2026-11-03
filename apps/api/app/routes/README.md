# app/routes/

FastAPI routers, one module per resource (`fights.py`, `tags.py`). Routes parse
input, call services or stat functions, and return Pydantic models. No stat
logic here. See issue #12.
