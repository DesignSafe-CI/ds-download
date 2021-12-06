# Designsafe-CI Download Service

## Prerequisites for local development

- Docker and Docker Compose
- Poetry (https://python-poetry.org/docs/#installation)
- Python 3.10 installed locally
- Designsafe dev certificate authority configured as a trusted CA (refer to main portal readme)

## Local dev environment setup

1. Update your /etc/hosts file by adding this line: `127.0.0.1 ds-download.test`
2. Clone the Git repository and `cd` into it.
3. Run `poetry install` to install dependencies locally. If you receive an error about a Python version mismatch, run `poetry env use $PATH_TO_PYTHON_3.10_INSTALL`.
4. Build the dev image with `docker-compose -f docker-compose.dev.yml build server`
5. Run the server with `docker-compose -f docker-compose.dev.yml up`
6. Confirm that the server is running by accessing the test message at `https://ds-download.test`

## Updating dependencies

For simplicity the Dockerfile uses a `requirements.txt` exported from Poetry. To add a new dependency:

1. Run `poetry add $NEW_DEPENDENCY`.
2. Run `poetry export > requirements.txt` in the repository root.
3. Rebuild the dev image with `docker-compose -f docker-compose.dev.yml build server`
