# Calculator sample app

A tiny Python calculator used to exercise the Jenkins pipeline.

## Run the tests locally

    cd sample-app
    python3 -m venv .venv
    . .venv/bin/activate
    pip install -r requirements.txt
    python -m pytest -v