# DataUSA API server

This repository provides the data server for the DataUSA website.
It's based on [LogicLayer](https://pypi.org/project/logiclayer/), a framework based on FastAPI, which allows to setup modules to provide data through REST endpoints. Most of the data retrieval is done through [tesseract-olap](https://pypi.org/project/tesseract-olap/), a semantic layer library.

## Development

The project metadata and dependencies are declared in the [`pyproject.toml`](./pyproject.toml) file.
To setup a virtual environment and start with local development, it's suggested to use [uv](https://docs.astral.sh/uv/):

```bash
uv venv --python 3.12  # create a virtual environment
uv sync --group dev  # resolve and install dependencies
```

Then you can use `uvicorn` to run a development server:

```bash
uvicorn --log-config=./etc/logging.json --reload app:layer
```

The main entrypoint of the application is declared in the [`app.py`](./app.py) file, and the ASGI server object is stored

### Environment variables

All the required environment variables are declared in the [`app.py`](./app.py) file.
You can declare them in your terminal session, or create a .env file and add the setting `--env-file=.env` to the `uvicorn` command.

## Production

Deployments are configured to be done via container image. Production images are built and deployed [through workflows](./.github/workflows) executed by Github Actions. You can use [docker](https://docs.docker.com/engine/install/) or [podman](https://podman.io/get-started) to build the image in your local machine and ensure it works.

To build the image:
```bash
# NO ENV VARS AT BUILDTIME
docker build --tag datausa-tesseract:latest .
```

To run the container:
```bash
docker run --rm --env-file=.env.local -p 7777:7777 datausa-tesseract:latest
```
