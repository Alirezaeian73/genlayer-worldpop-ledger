# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
import hashlib
import json
import re


MAX_RESPONSE_LENGTH = 12000
INDICATOR_ID = "SP.POP.TOTL"
INDICATOR_NAME = "Population, total"


def _json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _clean_country_code(value: str) -> str:
    if not isinstance(value, str):
        raise gl.vm.UserError("Country code must be text")
    country_code = value.strip().upper()
    if re.fullmatch(r"[A-Z]{3}", country_code) is None:
        raise gl.vm.UserError("Enter a three-letter ISO country code, such as JPN")
    return country_code


def _clean_year(value: u256) -> int:
    year = int(value)
    if year < 1960 or year > 2100:
        raise gl.vm.UserError("Year must be between 1960 and 2100")
    return year


def _extract_population(payload_text: str, country_code: str, year: int):
    if (
        not isinstance(payload_text, str)
        or not payload_text.strip()
        or len(payload_text) > MAX_RESPONSE_LENGTH
    ):
        return None

    try:
        payload = json.loads(payload_text)
    except Exception:
        return None

    if not isinstance(payload, list) or len(payload) != 2:
        return None

    rows = payload[1]
    if not isinstance(rows, list):
        return None

    for row in rows:
        if not isinstance(row, dict):
            return None

        if (
            row.get("countryiso3code") != country_code
            or row.get("date") != str(year)
        ):
            continue

        indicator = row.get("indicator")
        if not isinstance(indicator, dict):
            return None
        if indicator.get("id") != INDICATOR_ID:
            return None

        indicator_name = indicator.get("value")
        if not isinstance(indicator_name, str) or not indicator_name:
            return None

        population = row.get("value")
        if population is None:
            return {
                "status": "NO_DATA",
                "country_iso3": country_code,
                "year": year,
            }

        if isinstance(population, bool) or not isinstance(population, (int, float)):
            return None
        if int(population) != population or population < 0:
            return None

        return {
            "status": "OK",
            "country_iso3": country_code,
            "year": year,
            "population": int(population),
            "indicator_id": INDICATOR_ID,
            "indicator_name": indicator_name,
        }

    return {
        "status": "NO_DATA",
        "country_iso3": country_code,
        "year": year,
    }


class WorldPopLedger(gl.Contract):
    record_count: u256
    records: TreeMap[u256, str]

    def __init__(self):
        self.record_count = 0
        self.records = TreeMap()

    @gl.public.write
    def record_population(self, country_iso3: str, year: u256) -> u256:
        country_iso3 = _clean_country_code(country_iso3)
        year = _clean_year(year)

        source_url = (
            "https://api.worldbank.org/v2/country/"
            + country_iso3
            + "/indicator/"
            + INDICATOR_ID
            + "?format=json&date="
            + str(year)
            + "&per_page=1"
        )

        def evaluate_source() -> str:
            try:
                response = gl.nondet.web.get(source_url)
                response_text = response.body.decode("utf-8")
            except Exception:
                return _json({"status": "SOURCE_UNAVAILABLE"})

            result = _extract_population(response_text, country_iso3, year)
            if result is None:
                return _json({"status": "EXTRACTION_UNCLEAR"})

            if result.get("status") != "OK":
                return _json(result)

            result["source_sha256"] = hashlib.sha256(
                response_text.encode("utf-8")
            ).hexdigest()

            return _json(result)

        principle = (
            "Independently inspect the returned World Bank JSON. Both results must "
            "agree on status. For status OK, require exact agreement on country ISO3 "
            "code, year, population value, indicator ID, and indicator name. For "
            "NO_DATA, require agreement on country code and year. Ignore response hash "
            "differences only when all required data fields agree. Do not infer or "
            "invent a population value."
        )

        consensus_output = gl.eq_principle.prompt_comparative(
            evaluate_source,
            principle=principle,
        )

        try:
            if isinstance(consensus_output, str):
                observed = json.loads(consensus_output)
            elif isinstance(consensus_output, dict):
                observed = consensus_output
            else:
                observed = {"status": "EXTRACTION_UNCLEAR"}
        except Exception:
            observed = {"status": "EXTRACTION_UNCLEAR"}

        status = "UNCLEAR"
        population = None
        indicator_name = ""
        source_sha256 = ""

        if isinstance(observed, dict):
            observed_status = observed.get("status")

            if observed_status == "SOURCE_UNAVAILABLE":
                status = "SOURCE_UNAVAILABLE"

            elif observed_status == "NO_DATA":
                if (
                    observed.get("country_iso3") == country_iso3
                    and observed.get("year") == year
                ):
                    status = "NO_DATA"

            elif (
                observed_status == "OK"
                and observed.get("country_iso3") == country_iso3
                and observed.get("year") == year
                and observed.get("indicator_id") == INDICATOR_ID
                and observed.get("indicator_name") == INDICATOR_NAME
            ):
                observed_population = observed.get("population")

                if (
                    isinstance(observed_population, int)
                    and not isinstance(observed_population, bool)
                    and observed_population >= 0
                ):
                    status = "RECORDED"
                    population = observed_population
                    indicator_name = observed.get("indicator_name", "")
                    source_sha256 = observed.get("source_sha256", "")

        record_id = self.record_count

        record = {
            "id": int(record_id),
            "status": status,
            "country_iso3": country_iso3,
            "year": year,
            "indicator_id": INDICATOR_ID,
            "indicator_name": indicator_name or INDICATOR_NAME,
            "population": population,
            "source_name": "World Bank Open Data",
            "source_url": source_url,
            "source_sha256": source_sha256,
            "notice": (
                "This is an annual World Bank population indicator, not a real-time "
                "population count. Source data may be revised. This record is "
                "informational and is not an official census certificate."
            ),
        }

        self.records[record_id] = _json(record)
        self.record_count += 1
        return record_id

    @gl.public.view
    def get_record(self, record_id: u256) -> str:
        return self.records.get(record_id, "")

    @gl.public.view
    def get_record_count(self) -> u256:
        return self.record_count
