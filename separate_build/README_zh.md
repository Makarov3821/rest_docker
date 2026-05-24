# 分步构建 (Separate Build)

在这个文件夹中，我们将向你展示一种构建 REST 镜像的“新”方法。这里面的两个Dockerfile和主目录下的[Dockerfile.abini](../Dockerfile.abini)相似度非常高，刻意的将其拆成两个Dockerfile是为了解决以下问题：

* 对于重复构建/更新版本时，openblas、libcint这些库每次都需要重新编译，对于更新版本而言经常是纯痛苦多余的。
* 构建后的镜像体积庞大。特别是当你只是一个纯粹的用户，不想在下载存储镜像时还带着不需要的源码。
* 运行命令过于复杂。特别是当你对 Docker、Singularity 以及其他虚拟化技术并不熟悉时。

因此，在本次构建中：

* “abini” 将被拆分为“依赖项 (dependencies)”和“压缩版 (compressed)”两部分。这样一来，在依赖项没有变化的情况下，每次你想更新时，只需重新构建compressed部分即可。
* 最终镜像中**仅**包含 REST 的二进制文件以及必不可少的库。这将为普通用户节省磁盘空间，但**如果你是开发者，请勿使用这种方式进行构建！**
* 生成的镜像中添加了默认的运行命令。如果使用 Docker，这会缩短运行命令；如果使用 Singularity，其使用体验将类似于直接运行二进制文件，我们将在下文详细介绍。**但是**，<font color="red">引入默认入口点（entrypoint）可能会**破坏** abini 原有的运行命令。</font>因此，我们建议运行时使用下方提供的命令，如果你仍想使用abini中的方法，则要提前测试是否可行。

接下来我们将向你展示如何构建和使用这样的一个精简镜像。你也可以参考该仓库的 README.md 以获取更多细节。

## 构建镜像

### 构建依赖项

在此文件夹下运行：

```sh
docker build -t rest_dependencies:latest --no-cache -f Dockerfile.dependencies --target dependencies-final .
```

将生成镜像 `rest_dependencies:latest`，它是后续步骤的基础。当依赖项没有变化时，该镜像无需重新构建。

此外，你也可以通过以下命令直接拉取预构建的依赖镜像：`docker pull ghcr.io/makarov3821/rest_dependencies:260330`

### 构建压缩版 REST 镜像

同样在此文件夹下运行：

```sh
docker build -t [name]:<tag> --no-cache -f Dockerfile.compressed --target rest-final .
```

例如，你可以通过以下命令构建一个 2025 年 10 月 25 日的版本：

```sh
docker build -t rest_251025:latest --no-cache -f Dockerfile.compressed --target rest-final .
```

你也可以基于预构建的依赖项来构建压缩版镜像。将 `Dockerfile.compressed` 顶部的几行修改为：

```
# Copy built dependencies from the previous stage
#FROM rest_dependencies:latest AS rest
# Or use this line to download a precompiled image
FROM ghcr.io/makarov3821/rest_dependencies:260330 AS rest
```

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

由于 sif 镜像本身配置了默认命令，因此运行名为 `rest.sif` 的镜像将获得类似于运行二进制文件的体验：

```sh
rest.sif > rest.log 2>&1
```

你依然可以指定输入文件：

```sh
rest.sif -i H2.rjf > rest.log 2>&1
```

或者在装有 Singularity 环境 vehicular 的机器上，使用 MPI 方式运行：

```sh
mpirun -np 4 rest.sif > rest.log 2>&1
```