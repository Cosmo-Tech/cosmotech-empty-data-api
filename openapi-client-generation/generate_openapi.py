import yaml

from cosmotech.example_api.__main__ import app

if __name__ == "__main__":
    with open("openapi.yaml", "w") as f:
        yaml.dump(app.openapi(), f)
