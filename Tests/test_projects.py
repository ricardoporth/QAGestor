# tests/test_projects.py
import os
from utils import get_project_list, PROJECTS_DIR

def test_get_project_list_creates_dir(tmp_path, monkeypatch):
    # usa diretório temporário
    monkeypatch.setattr("utils.PROJECTS_DIR", tmp_path)

    projects = get_project_list()

    assert projects == []
    assert os.path.exists(tmp_path)
