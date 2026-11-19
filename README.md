# WorldPopLedger

WorldPopLedger is a GenLayer Intelligent Contract that stores annual population data from the World Bank for a selected country and year.

It is a data-recording project, not a real-time population counter or a census certificate.

## How it works

1. The caller provides a three-letter ISO country code and a year.
2. The contract requests the World Bank population indicator for that country and year.
3. Independent evaluations compare the country code, year, population value, and indicator details.
4. The contract stores the agreed result, source URL, and response SHA-256 on-chain.

## Indicator

- Indicator ID: `SP.POP.TOTL`
- Indicator name: `Population, total`
- Data source: World Bank Open Data API

## Possible results

- `RECORDED`: A population value was found and stored.
- `NO_DATA`: The API did not provide a value for that country and year.
- `SOURCE_UNAVAILABLE`: The API could not be reached.
- `UNCLEAR`: The response could not be reliably interpreted.

## Contract interface

### `record_population(country_iso3, year)`

Fetches and records a population value. The function returns the record ID.

Example inputs:

    country_iso3: JPN
    year: 2023

### `get_record(record_id)`

Returns the stored record as a JSON string.

### `get_record_count()`

Returns the number of stored records.

## Data source

The contract uses the World Bank API:

`https://api.worldbank.org/v2/country/{country_iso3}/indicator/SP.POP.TOTL`

The source provides annual indicator data. Values may be revised after publication.

## Deployment and live check

- Contract address: [`0xf7A9a7Db1817F62037b87eE8d4c7c0Df75871999`](https://explorer-studio.genlayer.com/address/0xf7A9a7Db1817F62037b87eE8d4c7c0Df75871999)
- Deployment transaction: [`0x6e87c36c86b68fe371755a6939b7b6f07ab9686cf14882dd0e3fb3ac2b86f3f6`](https://explorer-studio.genlayer.com/tx/0x6e87c36c86b68fe371755a6939b7b6f07ab9686cf14882dd0e3fb3ac2b86f3f6)
- Live population record transaction: [`0x7bc1a05d420424a3a9898946240dc9ca7d80dcbf04794117b22c1a930c01b03c`](https://explorer-studio.genlayer.com/tx/0x7bc1a05d420424a3a9898946240dc9ca7d80dcbf04794117b22c1a930c01b03c)

The live example recorded Japan's 2023 population as `124516650`. The stored record ID is `0`, and its source response SHA-256 is `479c6327f37a0f1681a1ed712c70405db3a0d857f0f8f3dfa764eb55792e6fa8`.

## Run local tests

    python -m pip install -r requirements-dev.txt
    python -m pytest -q

## Disclaimer

WorldPopLedger records an annual World Bank indicator. It is not a real-time count, an official census certificate, or demographic advice. Source data may be revised.
