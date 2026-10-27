# 分步构建 (Separate Build)

在这个文件夹中，我们将向你展示一种构建 REST 镜像的“新”方法。这里面的两个Dockerfile和主目录下的[Dockerfile.abini](../Dockerfile.abini)相似度非常高，刻意的将其拆成两个Dockerfile是为了解决以下问题：

* 对于重复构建/更新版本时，openblas、libcint这些库每次都需要重新编译，对于更新版本而言经常是纯痛苦多余的。
* 构建后的镜像体积庞大。特别是当你只是一个纯粹的用户，不想在下载存储镜像时还带着不需要的源码。
* 运行命令过于复杂。特别是当你对 Docker、Singularity 以及其他虚拟化技术并不熟悉时。

因此，在本次构建中：

* “abini” 将被拆分为“依赖项 (dependencies)”和“压缩版 (compressed)”两部分。这样一来，在依赖项没有变化的情况下，每次你想更新时，只需重新构建compressed部分即可。
* 最终镜像中**仅**包含 REST 的二进制文件以及必不可少的库。这将为普通用户节省磁盘空间，但**如果你是开发者，请勿使用这种方式进行构建！**
* 生成的镜像中添加了默认的运行命令。如果使用 Docker，这会缩短运行命令；如果使用 Singularity，其使用体验将类似于直接运行二进制文件，我们将在下文详细介绍。**但是**，<font color="red">引入默认入口点（entrypoint）可能会**破坏** abini 原有的运行命令。</font>因此，我们建议运行时使用下方提供的命令，如果你仍想使用abini中的方法，则要提前测试是否可行。

自2026-10-26开始，separate_build的基础镜像将从ubuntu:jammy更改为debian:trixie-slim（dependencies的实际镜像为rust:slim-trixie，不过也是debian:trixie-slim的基底）。这一方面会在满足目前组件的版本要求之上，给未来REST的新组件提供更加新的系统环境支持，另一方面可以进一步压缩dependencies和成品rest的镜像体积。目前本目录的默认Dockerfile链接到trixie-based，你也可以在jammy-based里面找到老的版本。

对应项目从2026-10-26的更新开始也将提供直接的镜像产物。尽管REST项目目前在GITEE仓库活跃开发，但是GITEE本身不提供免费的CI/CD，因而现在dependencies和rest的镜像，以及singularity的镜像仅在Github仓库的package和release中提供（[rest_dependencies](https://github.com/Makarov3821/rest_docker/pkgs/container/rest_dependencies)，[rest(docker)](https://github.com/Makarov3821/rest_docker/pkgs/container/rest)，以及[rest(sif)](https://github.com/Makarov3821/rest_docker/releases)）。GitHub Actions运行于 Ubuntu 24.04（linux/amd64），使用 Docker Buildx 0.38.1、BuildKit 0.34.1 构建 Docker 镜像，并使用 SingularityCE 4.6.0 转换生成 SIF 文件。镜像的更新时间不定，大概是dependencies半年一次，rest每个月或者重大功能更新一次。

当然，你也可以选择自己重头构建以获得最终的镜像产品，接下来我们将向你展示如何构建和使用这样的一个精简镜像。你也可以参考上级目录的 README.md 以获取更多细节。

## 构建镜像

### 构建依赖项

在此文件夹下运行：

```sh
docker build -t rest_dependencies:latest --no-cache -f Dockerfile.dependencies --target dependencies-final .
```

将生成镜像 `rest_dependencies:latest`，它是后续步骤的基础。当依赖项没有变化时，该镜像无需重新构建。

此外，你也可以通过以下命令直接拉取预构建的依赖镜像：`docker pull ghcr.io/makarov3821/rest_dependencies:latest`

### 构建压缩版 REST 镜像

同样在此文件夹下运行：

```sh
docker build -t rest:<tag> --no-cache -f Dockerfile.compressed --build-arg DEPENDENCIES_IMAGE=rest_dependencies:latest --target rest-final .
```

例如在 2025 年 10 月 25 日构建，就可以将tag命名为251025：

```sh
docker build -t rest:251025 --no-cache -f Dockerfile.compressed --build-arg DEPENDENCIES_IMAGE=rest_dependencies:latest --target rest-final .
```

你也可以基于预构建的依赖项来构建压缩版镜像。只须更换`DEPENDENCIES_IMAGE`为ghcr的镜像：

```
docker build -t rest:<tag> --no-cache -f Dockerfile.compressed --build-arg DEPENDENCIES_IMAGE=ghcr.io/makarov3821/rest_dependencies:latest --target rest-final .
```

如果你对依赖有特定要求也可以更改dependencies的tag，这里不再赘述。

### （可选）制作 Singularity 镜像

与 abini 类似，通过以下命令构建一个名为 `rest.sif` 的 sif 镜像：

```sh
singularity build rest.sif docker-daemon://rest:<tag>
```

或者从 Docker 镜像 tar 包中构建：

```sh
docker save -o rest_<tag>.tar rest:<tag>
singularity build rest.sif docker-archive://rest_<tag>.tar
```

## 运行镜像

~~该镜像内部的基组（basis-sets）位于 `/opt/basis-set-pool`。如果你曾使用过旧版本的 REST，该镜像中的基组路径依然保持兼容，不过新路径明显更短。~~

该镜像内部的基组（basis-sets）位于 `/opt/basis-set-pool`。参考最新的REST版本中对于基组的要求，`REST_BASIS_DIR`这个变量也指向这个目录。

### 使用 Docker

运行命令会比 abini 稍显简单。由于镜像内部自带了运行命令，你唯一需要做的额外步骤就是将包含输入文件的文件夹挂载到 `/data`。示例如下：

```sh
docker run --rm -v /your/ctrl.in/path:/data rest:<tag>
```

输出将直接打印在屏幕上。你也可以通过以下方式将其重定向到日志文件中：

```sh
docker run --rm -v /your/ctrl.in/path:/data rest:<tag> > rest.log 2>&1
```

如果你的输入文件名不是 `ctrl.in`，你可以像这样指定（以 `H2.rjf` 为例）：

```sh
docker run --rm -v /your/ctrl.in/path:/data rest:<tag> -i H2.rjf > rest.log 2>&1
```

### 使用 Singularity

由于 sif 镜像本身配置了默认命令，因此在有singularity环境的机器上直接运行 `rest.sif` 镜像将获得类似于运行二进制文件的体验：

```sh
#保证这个镜像可执行，其次有singularity的环境
chmod +x rest.sif
./rest.sif > rest.log 2>&1
```

你依然可以指定输入文件：

```sh
./rest.sif -i H2.rjf > rest.log 2>&1
```

或者使用 MPI 方式运行：

```sh
mpirun -np 4 ./rest.sif > rest.log 2>&1
```
