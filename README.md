This repository contains packages for privacy-preserving record linkage (PPRL) based on Bloom filters.
It covers a wide range of functionalities from basic primitives of setting bits in bitarrays to an entire
HTTP-based service for preprocessing, masking and matching records in a privacy-preserving manner.

# Repository structure

The [packages](./packages/) directory contains several Python modules.
These modules cover different functionalities for performing PPRL.
Each module is its own project with its own dependencies.

- [`pprl_client`](./packages/pprl_client/): HTTP-based client for using the PPRL service
- [`pprl_core`](./packages/pprl_core/): primitives for Bloom filter based PPRL
- [`pprl_model`](./packages/pprl_model/): data models for use in a HTTP-based service with PPRL in mind
- [`pprl_service`](./packages/pprl_service/): HTTP-based service for performing PPRL

# Setup

Working with the source code requires Python 3.10 and above and [Poetry](https://python-poetry.org/) to be installed. 
There are [several scripts](./scripts/) which facilitate working with this repository.
To install the dependencies for each module and set up virtual environments, run the following command.

```
$ ./scripts/poetry_run_in_each.sh install
```

This will run `poetry install` in each module.
You can then open every module in the IDE or code editor of your choice.

# Installation

To run the PPRL service locally, you have two options.

## Manual setup

If you already set up a development environment, you can run the PPRL service from the command line.
Change into the [root directory of the PPRL service](./packages/pprl_service/) and run one of the two following commands.

```
$ poetry run pprl_service
$ poetry run uvicorn pprl_service.main:app --host 0.0.0.0 --workers 4
```

The first command will spin up the server with a single service worker, similar to running `fastapi dev` without hot reloading capabilities.
The second command allows for more fine-grain control using `uvicorn` directly.
The arguments are the same as the default ones in the [Dockerfile](./Dockerfile) at the root of this repository.

## Docker

The [Dockerfile](./Dockerfile) can be used to start the PPRL service inside a container.
Build the service and then run it.

```
$ docker build -t pprl_service:dev .
$ docker run --rm -p 8000:8000 pprl_service:dev
```

You can then access the service documentation in your browser at http://localhost:8000/docs.
Alternatively, you can also use a pre-built Docker image.

```
$ docker run --rm -p 8000:8000 ghcr.io/ul-mds/pprl:0.1.0
```

# License

MIT.
