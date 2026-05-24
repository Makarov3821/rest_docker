# Separate Build

In this folder, we'll show you a "new" way to build the REST image. Build files in this way are about 80% similar to the [Dockerfile.abini](../Dockerfile.abini) you may have experienced, so changes are designed to tackle problems like:

- Painful and unnecessary procedure in building dependencies. Especially you are enthusiastic in building and trying new version.
- Enormous image size after building. Especially when you are just a user distributing or downloading image and not aiming to contribute to it.
- Complicated running command. Especially you are not familiar with docker, singularity and other virtualization stuff.

So in this build:

- "abini" will be break into two parts called "dependencies" and "compressed", so without dependencies change, only "compressed" part needs to be rebuild everytime you want to update.
- **ONLY** binary of the REST and libraries necessary will be included in the final image. This will save the disk for regular users, but **if you are a developer, do NOT build in this way!**
- A default running command will be added in produced image. This will shorten the running command if using docker, and will be binary-like if using singularity, we'll show this in detail below. **BUT**, <font color="red"> the introduce of default entrypoint may **BREAK** the running command in abini,</font> thus we recommand using the commands below, and test if you want to follow the abini way.

Now we'll show you the build and the use. You can also refer to README.md for this repo to get more detail.

## Build the image

### Building the dependencies

In this folder, run:
```sh
docker build -t rest_dependencies:latest --no-cache -f Dockerfile.dependencies --target dependencies-final .
```
will yield image "rest_dependencies:latest", which is the base of the following procedure. This image needs no rebuild when dependencies has no change.

Also, a pre-built dependencies image could be obtained by `docker pull ghcr.io/makarov3821/rest_dependencies:260524`

### Building compressed REST image

Also in this folder, run:
```sh
docker build -t [name]:<tag> --no-cache -f Dockerfile.compressed --target rest-final .
```

For instance, you can build a version at Oct 25 2025 by:
```sh 
docker build -t rest_251025:latest --no-cache -f Dockerfile.compressed --target rest-final .
```

You can also build a compressed one from pre-built dependencies. Change top lines in Dockerfile.compressed to:
```
# Copy built dependencies from the previous stage
#FROM rest_dependencies:latest AS rest
# Or use this line to download a precompiled image
FROM ghcr.io/makarov3821/rest_dependencies:260524 AS rest
```

### (Optional) Make Singularity image

Similiar to abini, build a sif image named rest.sif by:
```sh
singularity build rest.sif docker-daemon://rest:<tag>
```

Or from a saved docker image tar:
```sh
docker save -o rest_<tag>.tar rest:<tag>
singularity build rest.sif docker-archive://rest_<tag>.tar
```

## Run the image

~~Internal basis-sets in this image locate at `/opt/basis-set-pool`. Also if you have used REST of a former version, the path of basis-sets is still compatible in this image, though new path is significantly shorter.~~

Internal basis-sets in this image locate at `/opt/basis-set-pool`. As regulation for basis path in the newest REST is controlled by varible `REST_BASIS_DIR`, we have preset this varible to the directory above.


### Using Docker

The command will be slight simpler than abini. Since it has an internal run command, all additional step is attaching your input file folder to "/data". An example will be:
```sh
docker run --rm -v /your/ctrl.in/path:/data rest:<tag>
```

The output will be printed on screen. You can also redirect it to a logfile by:
```sh
docker run --rm -v /your/ctrl.in/path:/data rest:<tag> > rest.log 2>&1
```

And if your input file name is other than "ctrl.in", you can redirect it (H2.rjf for instance) by:
```sh
docker run --rm -v /your/ctrl.in/path:/data rest:<tag> -i H2.rjf > rest.log 2>&1
```


### Using Singularity

Since the sif has default command itself, so running a image named "rest.sif" will have a binary-like experience:
```sh
rest.sif > rest.log 2>&1
```
The input file can still be nominated:
```sh
rest.sif -i H2.rjf > rest.log 2>&1
```

or mpi type:
```sh
mpirun -np 4 rest.sif > rest.log 2>&1
```
works on machines with singularity environment.


