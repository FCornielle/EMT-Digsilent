from pathlib import Path

import pytest

from pfemt.errors import PowerFactoryExecutionError
from pfemt.project import export_powerfactory_project


class _ExportCommand:
    def __init__(self) -> None:
        self.attributes = {}
        self.deleted = False

    def SetAttribute(self, name: str, value: object) -> int:
        self.attributes[name] = value
        return 0

    def Execute(self) -> int:
        Path(str(self.attributes["g_file"])).write_bytes(b"powerfactory-project")
        return 0

    def Delete(self) -> None:
        self.deleted = True


class _User:
    def __init__(self, command: _ExportCommand) -> None:
        self.command = command

    def CreateObject(self, class_name: str, name: str) -> _ExportCommand:
        assert class_name == "ComPfdexport"
        assert name == "PFEMT Project Archive"
        return self.command


class _Project:
    loc_name = "PFEMT_02_HV_Cable_Energization_220kV"

    def __init__(self) -> None:
        self.deactivated = False

    def Deactivate(self) -> int:
        self.deactivated = True
        return 0


class _Application:
    def __init__(self, project: _Project, command: _ExportCommand) -> None:
        self.project = project
        self.command = command
        self.reactivated = None

    def GetActiveProject(self) -> object:
        return self.project

    def GetCurrentUser(self) -> _User:
        return _User(self.command)

    def ActivateProject(self, name: str) -> int:
        self.reactivated = name
        return 0


def test_project_export_is_atomic_and_reactivates_project(tmp_path: Path) -> None:
    project = _Project()
    command = _ExportCommand()
    app = _Application(project, command)
    output = tmp_path / "study.pfd"

    assert export_powerfactory_project(app, project, output) == output.resolve()
    assert output.read_bytes() == b"powerfactory-project"
    assert project.deactivated
    assert app.reactivated == project.loc_name
    assert command.attributes["g_objects"] == [project]
    assert command.attributes["g_file"].endswith("study.partial.pfd")
    assert command.deleted


def test_project_export_requires_pfd_extension(tmp_path: Path) -> None:
    with pytest.raises(PowerFactoryExecutionError, match=".pfd extension"):
        export_powerfactory_project(object(), object(), tmp_path / "study.zip")
