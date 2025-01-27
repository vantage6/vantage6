from pathlib import Path
import pytest
from .fixtures import build_test_image, cleanup_test_image

def pytest_addoption(parser):
    parser.addini("dockerfile", "Path to Dockerfile", default="Dockerfile")
    parser.addini("imagename", "Docker image name")
    parser.addoption("--dockerfile", action="store", default=None)
    parser.addoption("--imagename", action="store", default=None)

@pytest.fixture(scope="session")
def docker_image(request):
    config = request.config
    dockerfile_path = config.getoption("--dockerfile") or config.getini("dockerfile")
    dockerfile_path = Path(dockerfile_path).resolve()
    image_name = config.getoption("--imagename") or config.getini("imagename")
    image = build_test_image(dockerfile_path, image_name)
    yield image
    cleanup_test_image(image)
