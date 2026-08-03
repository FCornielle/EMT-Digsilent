from pathlib import Path

import pytest

from pfemt.builders.cable_energization import (
    _cable_system_type,
    _cable_type,
    _fit_cable_system,
    apply_cable_bonding_scenario,
)
from pfemt.cable import cable_scenarios
from pfemt.config import load_yaml


class _Object:
    def __init__(self, class_name: str, name: str) -> None:
        self.class_name = class_name
        self.loc_name = name
        self.attributes: dict[str, object] = {}

    def HasAttribute(self, name: str) -> int:
        return 1

    def SetAttribute(self, name: str, value: object) -> None:
        self.attributes[name] = value

    def GetAttribute(self, name: str) -> object:
        return self.attributes.get(name)

    def GetFullName(self) -> str:
        return "{}.{}".format(self.loc_name, self.class_name)


class _Folder:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], _Object] = {}

    def GetContents(self, pattern: str) -> list[_Object]:
        name, class_name = pattern.rsplit(".", 1)
        item = self.objects.get((class_name, name))
        return [item] if item is not None else []

    def CreateObject(self, class_name: str, name: str) -> _Object:
        item = _Object(class_name, name)
        self.objects[(class_name, name)] = item
        return item


class _Application:
    def __init__(self) -> None:
        self.equipment = _Folder()

    def GetProjectFolder(self, folder_name: str, create: int) -> _Folder:
        assert folder_name == "equip"
        assert create == 1
        return self.equipment


class _CableSystem(_Object):
    def __init__(self) -> None:
        super().__init__("ElmCabsys", "CABLE_COUPLING")
        self.update_calls = 0
        self.fit_calls = 0

    def Update(self) -> int:
        self.update_calls += 1
        return 0

    def FitParams(self) -> int:
        self.fit_calls += 1
        return 0


def _config() -> dict:
    root = Path(__file__).resolve().parents[2]
    return load_yaml(root / "studies/02_hv_cable_energization/configs/base.yaml")


def test_typcab_builder_maps_catalogue_geometry_to_verified_attribute_vectors() -> None:
    application = _Application()
    cable_type = _cable_type(application, _config())
    assert cable_type.attributes["diaCon"] == pytest.approx(41.2)
    assert cable_type.attributes["thSht"] == pytest.approx(3.1)
    assert cable_type.attributes["thIns"] == pytest.approx([24.7, 14.2, 1.0])
    assert cable_type.attributes["epsr"][0] == pytest.approx(2.83293, rel=1e-5)
    assert cable_type.attributes["Cf"][0] == pytest.approx(90.0113, rel=1e-5)
    assert cable_type.attributes["has_sht"] == 1
    assert cable_type.attributes["has_arm"] == 0


def test_typcabsys_builder_preserves_flat_buried_formation_and_explicit_sheath() -> None:
    application = _Application()
    config = _config()
    cable_type = _cable_type(application, config)
    system_type = _cable_system_type(application, config, cable_type)
    assert system_type.attributes["iopt_bur"] == "gnd"
    assert system_type.attributes["nphas"] == [3.0]
    assert system_type.attributes["red"] == [0.0]
    assert system_type.attributes["bond"] == [0.0]
    assert system_type.attributes["pcab_c"] == [cable_type]
    assert system_type.attributes["xy_c"] == [[-0.35, 0.0, 0.35, 1.5, 1.5, 1.5]]


def test_elm_cabsys_frequency_fit_is_requested_once() -> None:
    cable_system = _CableSystem()
    _fit_cable_system(cable_system, _config())
    assert cable_system.attributes["i_dist"] == 1
    assert cable_system.attributes["i_model"] == 1
    assert cable_system.attributes["fd_model"] == 1
    assert cable_system.attributes["fmin"] == pytest.approx(10.0)
    assert cable_system.attributes["fmax"] == pytest.approx(20000.0)
    assert cable_system.update_calls == 1
    assert cable_system.fit_calls == 1
    _fit_cable_system(cable_system, _config())
    assert cable_system.update_calls == 1
    assert cable_system.fit_calls == 1


def test_bonding_scenario_controls_ground_switches_and_cross_bonding() -> None:
    config = _config()
    scenarios = cable_scenarios(config)
    cable_system_type = _Object("TypCabsys", "CABLE_SYSTEM")
    cable_system_type.attributes["bond"] = [0.0]
    cable_system = _CableSystem()
    ground_sending = _Object("ElmGndswt", "GROUND_SEND")
    ground_receiving = _Object("ElmGndswt", "GROUND_RECV")
    objects = {
        "cable_system_type": cable_system_type,
        "cable_system": cable_system,
        "sheath_ground_sending": ground_sending,
        "sheath_ground_receiving": ground_receiving,
    }

    single_point = next(item for item in scenarios if item.bonding_id == "single_point")
    apply_cable_bonding_scenario(objects, single_point)
    assert ground_sending.attributes["on_off"] == 1
    assert ground_receiving.attributes["on_off"] == 0
    assert cable_system_type.attributes["bond"] == [0.0]
    assert cable_system.fit_calls == 0

    cross_bonded = next(item for item in scenarios if item.bonding_id == "cross_bonded")
    apply_cable_bonding_scenario(objects, cross_bonded)
    assert ground_sending.attributes["on_off"] == 1
    assert ground_receiving.attributes["on_off"] == 1
    assert cable_system_type.attributes["bond"] == [1.0]
    assert cable_system.update_calls == 1
    assert cable_system.fit_calls == 1
