# GitHub Metrics

Fetch and calculate statistics about pull requests in a GitHub repository.

## Installation

### Mac

```shell
$ brew install python
$ pip install poetry
$ make setup
```

### Arch Linux

```shell
# pacman -S poetry
$ make setup
```

### Other systems

Install these dependencies manually:

- Python >= 3.10
- poetry

Then run:

```shell
$ make setup
```

## Usage

```shell
ACCESS_TOKEN='<your github token>' \
./github-metrics -v \
    --owner '<repo owner>' \
    --repo '<repo name'> \
    --cache cache \
    --data results/data.csv \
    --stats-daily results/stats_daily.csv \
    --stats-weekly results/stats_weekly.csv
```

You can now find the statistics as CSV files in:

- `results/data.csv`
- `results/stats_daily.csv`
- `results/stats_weekly.csv`

## Development

### Testing and linting

``` shell
$ make test
$ make lint
```

### Help

``` shell
$ make help
```

## Contributing

__Feel free to remix this project__ under the terms of the [Apache License,
Version 2.0](http://www.apache.org/licenses/LICENSE-2.0).
