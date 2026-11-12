# Yelp Tucson NoSQL

Academic MongoDB project based on the Yelp Open Dataset. The project builds a local-business directory and review platform for Tucson, Arizona, using events from 2012 through 2021.

## Project scope

- Database: MongoDB Community Edition
- Geographic scope: Tucson, Arizona
- Event period: 2012-01-01 through 2021-12-31
- Source: Yelp Open Dataset
- Runtime: Docker Compose with Python 3.12 and MongoDB 8.0

## Current status

The repository currently contains the reproducible project skeleton. Dataset filtering, validation, import, queries, and benchmarks will be implemented progressively and verified one step at a time.

## Data policy

The Yelp dataset is not included in this repository. Each contributor must obtain it through the official Yelp distribution and accept the applicable terms.

Never commit:

- raw Yelp JSON files;
- processed Tucson datasets;
- MongoDB data volumes;
- secrets or real `.env` files.

Place the downloaded JSONL files locally under `data/raw/`. This directory is mounted read-only inside the pipeline container.

## Repository structure

```text
.
├── compose.yaml
├── Dockerfile
├── requirements.txt
├── scripts/
├── src/queries/
├── docs/
├── data/raw/          # local only, ignored by Git
├── data/processed/    # generated locally, ignored by Git
└── results/
```

## Planned workflow

1. Filter and normalize Tucson businesses.
2. Filter reviews, tips, and check-ins to 2012-2021.
3. Retain only referenced users.
4. Validate identifiers, relationships, dates, coordinates, and types.
5. Import the validated dataset with PyMongo.
6. Implement and test queries incrementally.
7. Benchmark indexing and modeling decisions.

## Initial Docker commands

Copy the example environment file if local overrides are needed:

```bash
cp .env.example .env
```

Build the pipeline image and start MongoDB:

```bash
docker compose build
docker compose up -d mongodb
```

Check the services:

```bash
docker compose ps
```

MongoDB is exposed on `localhost:27018` by default to avoid conflicts with an existing local MongoDB installation. MongoDB Compass can connect with:

```text
mongodb://localhost:27018
```

## Collaboration

Contributors should work on focused branches and open pull requests instead of committing directly to `main`.

Suggested branch names:

- `feature/docker-setup`
- `feature/filter-businesses`
- `feature/filter-reviews`
- `feature/validate-dataset`
- `feature/import-mongodb`
- `feature/query-geospatial`

## License and attribution

The repository contains original project code and documentation only. Yelp data remains governed by Yelp's dataset terms and is not redistributed here. A code license will be selected by the team before the first public release.

