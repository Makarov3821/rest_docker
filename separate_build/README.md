# Separate Build

This directory provides a way to build a compact REST image using two Dockerfiles. Their approach is similar to [Dockerfile.abini](../Dockerfile.abini) in the repository root, with changes intended to address:

- Repeatedly compiling dependencies such as OpenBLAS and libcint when updating REST.
- Large images that include source code and build tools users do not need.
- Complicated commands for users unfamiliar with Docker, Singularity, and related tools.

The build is split into two parts:

- **dependencies** contains the reusable build environment and scientific libraries. When these dependencies have not changed, updating REST only requires rebuilding **compressed**.
- The final image contains **only the REST executable and the libraries and runtime files it needs**. This saves disk space for regular users, but **developers should use a development image instead**.
- A default entrypoint simplifies Docker commands and lets a Singularity image run like a standalone executable. **However**, <font color="red">this entrypoint may **break** commands previously used with abini</font>. Use the commands below, or test existing abini commands before relying on them.

Starting with the update dated 2026-10-26, the default separate build moves from `ubuntu:jammy` to a Debian Trixie environment. The dependencies image uses `rust:slim-trixie`, which is based on `debian:trixie-slim`; the final REST runtime uses `debian:trixie-slim` directly. This provides a newer environment for current and future REST components while helping reduce image size. The default Dockerfiles in this directory are symbolic links to `trixie-based/`. The older versions remain available in `jammy-based/`.

Prebuilt artifacts are also provided starting with the 2026-10-26 update. REST is actively developed on Gitee, while this project's automated builds and releases use GitHub Actions. The dependencies and REST Docker images are published in GitHub Packages, and Singularity images are published in GitHub Releases: [rest_dependencies](https://github.com/Makarov3821/rest_docker/pkgs/container/rest_dependencies), [REST Docker image](https://github.com/Makarov3821/rest_docker/pkgs/container/rest), and [REST SIF image](https://github.com/Makarov3821/rest_docker/releases). GitHub Actions runs on Ubuntu 24.04 (`linux/amd64`), builds Docker images using Docker Buildx 0.38.1 and BuildKit 0.34.1, and converts them to SIF using SingularityCE 4.6.0. Updates are irregular: dependencies are expected to be updated roughly every six months, and REST roughly monthly or after major feature updates.

You can also build the images yourself by following the instructions below. See the repository's [README.md](../README.md) for additional details.

## Build the image

### Building the dependencies

Run the following command in this directory:

```sh
docker build -t rest_dependencies:latest --no-cache -f Dockerfile.dependencies --target dependencies-final .
```

This produces `rest_dependencies:latest`, which serves as the base for the next step. You do not need to rebuild this image when its dependencies have not changed.

Alternatively, pull the prebuilt dependencies image with `docker pull ghcr.io/makarov3821/rest_dependencies:latest`.

### Building the compressed REST image

Run the following command in the same directory:

```sh
docker build -t rest:<tag> --no-cache -f Dockerfile.compressed --build-arg DEPENDENCIES_IMAGE=rest_dependencies:latest --target rest-final .
```

For example, a build performed on October 25, 2025 can be given the tag `251025`:

```sh
docker build -t rest:251025 --no-cache -f Dockerfile.compressed --build-arg DEPENDENCIES_IMAGE=rest_dependencies:latest --target rest-final .
```

To build using the prebuilt dependencies image, set `DEPENDENCIES_IMAGE` to its GHCR reference:

```sh
docker build -t rest:<tag> --no-cache -f Dockerfile.compressed --build-arg DEPENDENCIES_IMAGE=ghcr.io/makarov3821/rest_dependencies:latest --target rest-final .
```

You can select a different dependencies tag if you need a specific version.

### (Optional) Make a Singularity image

As with abini, build a SIF image named `rest.sif` from the local Docker image:

```sh
singularity build rest.sif docker-daemon://rest:<tag>
```

Alternatively, build it from a saved Docker image archive:

```sh
docker save -o rest_<tag>.tar rest:<tag>
singularity build rest.sif docker-archive://rest_<tag>.tar
```

## Run the image

~~The internal basis sets are located at `/opt/basis-set-pool`. The paths used by older REST images remain available for compatibility.~~

The internal basis sets are located at `/opt/basis-set-pool`. The image presets `REST_BASIS_DIR` to this directory, as required by current REST versions.

### Using Docker

The built-in entrypoint simplifies running REST. Mount the directory containing your input file at `/data`:

```sh
docker run --rm -v /your/ctrl.in/path:/data rest:<tag>
```

Output is printed to the terminal. To redirect it to a log file:

```sh
docker run --rm -v /your/ctrl.in/path:/data rest:<tag> > rest.log 2>&1
```

If your input file is not named `ctrl.in`, specify it with `-i`, for example:

```sh
docker run --rm -v /your/ctrl.in/path:/data rest:<tag> -i H2.rjf > rest.log 2>&1
```

### Using Singularity

The SIF image has a default command, so it can be run directly like a standalone executable on a machine with Singularity installed:

```sh
# Make the image executable and ensure Singularity is available.
chmod +x rest.sif
./rest.sif > rest.log 2>&1
```

You can specify an input file:

```sh
./rest.sif -i H2.rjf > rest.log 2>&1
```

Or run it with MPI:

```sh
mpirun -np 4 ./rest.sif > rest.log 2>&1
```
