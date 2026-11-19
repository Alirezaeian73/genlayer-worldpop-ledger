import importlib.util
import json
import sys
import types
from pathlib import Path


class _Decorators:
    @staticmethod
    def write(function):
        return function

    @staticmethod
    def view(function):
        return function


class _UserError(Exception):
    pass


_fake_genlayer = types.ModuleType("genlayer")
_fake_genlayer.gl = types.SimpleNamespace(
    Contract=object,
    public=_Decorators(),
    vm=types.SimpleNamespace(UserError=_UserError),
)
_fake_genlayer.u256 = int
_fake_genlayer.TreeMap = dict

_contract_path = (
    Path(__file__).resolve().parents[1]
    / "contracts"
    / "world_pop_ledger.py"
)

_previous_genlayer = sys.modules.get("genlayer")
sys.modules["genlayer"] = _fake_genlayer

try:
    _spec = importlib.util.spec_from_file_location(
        "world_pop_ledger_under_test",
        _contract_path,
    )
    _contract = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_contract)
finally:
    if _previous_genlayer is None:
        sys.modules.pop("genlayer", None)
    else:
        sys.modules["genlayer"] = _previous_genlayer


def _world_bank_response(value=124516650):
    return json.dumps([
        {
            "page": 1,
            "pages": 1,
            "per_page": 1,
            "total": 1,
        },
        [
            {
                "indicator": {
                    "id": "SP.POP.TOTL",
                    "value": "Population, total",
                },
                "country": {
                    "id": "JP",
                    "value": "Japan",
                },
                "countryiso3code": "JPN",
                "date": "2023",
                "value": value,
            }
        ],
    ])


def test_clean_country_code_trims_and_normalizes_case():
    assert _contract._clean_country_code(" jpn ") == "JPN"


def test_clean_country_code_rejects_invalid_values():
    for value in ("JP", "JPN1", "123", ""):
        try:
            _contract._clean_country_code(value)
        except _UserError:
            pass
        else:
            raise AssertionError(f"Expected country code to be rejected: {value!r}")


def test_clean_year_accepts_supported_boundaries():
    assert _contract._clean_year(1960) == 1960
    assert _contract._clean_year(2100) == 2100


def test_clean_year_rejects_out_of_range_values():
    for year in (1959, 2101):
        try:
            _contract._clean_year(year)
        except _UserError:
            pass
        else:
            raise AssertionError(f"Expected year to be rejected: {year}")


def test_extract_population_reads_world_bank_observation():
    result = _contract._extract_population(
        _world_bank_response(),
        "JPN",
        2023,
    )

    assert result == {
        "status": "OK",
        "country_iso3": "JPN",
        "year": 2023,
        "population": 124516650,
        "indicator_id": "SP.POP.TOTL",
        "indicator_name": "Population, total",
    }


def test_extract_population_reports_null_value_as_no_data():
    result = _contract._extract_population(
        _world_bank_response(value=None),
        "JPN",
        2023,
    )

    assert result == {
        "status": "NO_DATA",
        "country_iso3": "JPN",
        "year": 2023,
    }


def test_extract_population_does_not_use_another_country():
    response = _world_bank_response().replace('"JPN"', '"FRA"')

    result = _contract._extract_population(response, "JPN", 2023)

    assert result == {
        "status": "NO_DATA",
        "country_iso3": "JPN",
        "year": 2023,
    }


def test_extract_population_rejects_malformed_json():
    assert _contract._extract_population(
        "{not valid json",
        "JPN",
        2023,
    ) is None


def test_extract_population_rejects_wrong_indicator():
    response = _world_bank_response().replace(
        "SP.POP.TOTL",
        "SP.DYN.LE00.IN",
    )

    assert _contract._extract_population(response, "JPN", 2023) is None


def test_extract_population_rejects_fractional_population():
    assert _contract._extract_population(
        _world_bank_response(value=124.5),
        "JPN",
        2023,
    ) is None


def test_extract_population_rejects_oversized_response():
    assert _contract._extract_population(
        "x" * 12001,
        "JPN",
        2023,
    ) is None
