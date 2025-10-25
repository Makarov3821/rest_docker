# REST Docker

## Getting the Docker Image

You can either pull the Docker image from Docker Hub or build it yourself.

### Pull from Docker Hub

To pull the image from Docker Hub, follow these steps:

1. Open your terminal.
2. Run the following command:
    ```sh
    docker pull bsplu/rest_docker
    ```
3. Verify the image has been pulled by running:
    ```sh
    docker images
    ```

### Build the Docker Image

To build the Docker image yourself, follow these steps:

1. Open your terminal.
2. Navigate to the directory containing the Dockerfile.
3. Run the following command to build the Docker image:
    ```sh
    docker build -t [name]:[version] .
    # Example:
    docker build -t rest:dev . -f ./Dockerfile
    ```

    Multiple Dockerfiles are provided for different purposes:
    - **Dockerfile.static [default]**: Used to build REST from source code, while some dependencies are linked as static libraries from pre-built packages.
    - **Dockerfile.abini**: Used to build REST and its dependencies entirely from source code.
    - **Dockerfile.develop**: Create an Ubuntu-based development environment with all necessary dependencies pre-installed for compiling REST from source. Ideal for contributors who need a read-to-use build environment.

    Additionally, there are several useful build arguments and options you can use:
    - `--build-arg CHINA=True`: Speeds up download speeds if you are located in China.
    - `--build-arg BLAS=[blas_toolkit]`: Specifies BLAS and LAPACK libraries used. Two options: either `openblas` or `intel-mkl`
    - `--build-arg USERNAME=[string]`: Sets the default non-root user account name for the container (default:`admin`). This affects both system access and file permissions within the container.
    - `--no-cache-filter rest`: Avoids caching for specific parts of the build process.
    - `--build-arg PR_REST=[number]`: Specifies a pull request branch for REST to test a specific PR.

4. Verify the images after a successful build:
    ```sh
    docker images
    ```
5. [Optional] After you build, you may want to clean the cache:
    ```sh
    docker image prune -f
    ```

**Note:**
- `[name]` is the image name you want to use, like `rest/mpi`, `your_name/rest/x86`, etc.
- `[version]` is the version tag for the named image, like `v0.2`, etc.
- If you are in China, you may want to use `docker build --build-arg CHINA=True -t [name]:[version] .` to speed up downloading files.

## Running the Docker Container

### Shell Mode (for Debugging)

To run the container in interactive mode:

1. Open your terminal.
2. Run the following command:
    ```sh
    docker run --rm -it [name]:[version] /bin/bash
    ```
3. When done, type `exit` to leave the container.

### Exec Mode (for Job Submission)

To run the container for job submission:

1. Open your terminal.
2. Run the following command:
    ```sh
    docker run --rm -v /path/to/local/dir:/path/in/container -w /path/in/container [name]:[version] /bin/bash -c "rest"
    ```

## Converting to Singularity

### Using docker-daemon

Run the following command:
```sh
singularity build [name]_[version].sif docker-daemon://[name]:[version]
```

### Export Docker Image to a TAR File

1. Export the Docker image:
    ```sh
    docker save -o [name]_[version].tar [name]:[version]
    ```
2. Build the Singularity image:
    ```sh
    singularity build [name]_[version].sif docker-archive://[name]_[version].tar
    ```

### Running the Singularity Container

To run the Singularity container:
```sh
singularity exec --bind /path/to/local:/path/in/container [name]_[version].sif bash -c "rest"
```

## Binary-like build

If you want a faster way in version update and smaller in image outcome, you can also experience [separate build](./separate_build/README.md)

## For Developers

1. To debugging in the Container:
    - To debug code within the container environment:
        ```sh
        docker run --rm -it [name]:[version] sudo su - && /bin/bash
        ```
    - If you want to write a Dockerfile based on this repository, you can use:
        ```dockerfile
        FROM bsplu/rest_docker
        USER root
        ```
2. Host-Based Development (Linux Only):
    - Setup Development Container:
	    Build a container with all REST compilation dependencies:
        ```sh
        docker build \
		  --build-arg CHINA=True \
		  --build-arg BLAS=intel-mkl \
		  --build-arg USERNAME=$USER \
		  -t rest:dev \
		  -f ./Dockerfile.develop .
        ```
      **Important**:  Set `USERNAME=$USER` to match your host system's username for proper permissions.
    - Prepare REST Workspace
       ```sh
        git clone https://gitee.com/restgroup/rest_workspace.git
        cd rest_workspace
        ./Config -r gitee -f $FC -e
        cd ../
       ```
    - Run Container with Mounted Workspace: 
       ```sh
        docker run --rm -v $(pwd)/rest_workspace:/home/$USER/rest_workspace -w /home/$USER/rest_workspace -it rest:dev /bin/bash
       ```
    - Compile REST: 
	   Inside the container:
       ```sh
        cargo build --release --features intel-mkl
       ```

