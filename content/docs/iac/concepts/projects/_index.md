---
title_tag: "Projects | Pulumi Concepts"
meta_desc: A Pulumi project is any folder which contains a Pulumi.yaml file. Learn about how to use Pulumi projects, as well as example use cases.
title: Projects
h1: Projects
meta_image: /images/docs/meta-images/docs-meta.png
menu:
    iac:
        name: Projects
        parent: iac-concepts
        weight: 20
        identifier: iac-concepts-projects
    concepts:
        identifier: projects
        weight: 1

aliases:
- /docs/reference/project/
- /docs/tour/basics-projects/
- /docs/tour/programs/
- /docs/intro/concepts/project/
- /docs/concepts/projects/
---

A Pulumi project is any folder that contains a `Pulumi.yaml` project file. At runtime, the nearest parent folder containing a `Pulumi.yaml` file determines the current project. Projects are created with the [`pulumi new`](/docs/iac/cli/commands/pulumi_new/) command.

## The project file (Pulumi.yaml) {#pulumi-yaml}

The project file specifies which runtime to use and where to find the program that runs during each deployment. The supported runtimes are `nodejs`, `python`, `dotnet`, `go`, `java`, and `yaml`.

Project files also include metadata about your project. The filename must begin with a capital `P`, but either `.yml` or `.yaml` extension is accepted.

A typical `Pulumi.yaml` file resembles the following example:

```yaml
name: webserver
runtime: nodejs
description: A minimal JavaScript Pulumi program.
```

For JavaScript or TypeScript projects, the working directory should also contain a `package.json` file that points to an entrypoint such as `index.js`. For Python projects, the presence of a `__main__.py` or `setup.py` file defines the entrypoint instead.

The following examples show additional `Pulumi.yaml` files that define project configurations for other common use cases:

* A `Pulumi.yaml` file for a Node.js program that uses JavaScript rather than TypeScript:

    ```yaml
    name: my-project
    runtime:
      name: nodejs
      options:
        typescript: false
    ```

* A `Pulumi.yaml` file for a Go program that uses a pre-built executable named `mybinary`:

    ```yaml
    name: my-project
    description: A precompiled Go Pulumi program.
    runtime:
      name: go
      options:
        binary: mybinary
    ```

* A `Pulumi.yaml` file for a .NET program that uses a pre-built assembly named `MyInfra.dll` in the `bin` directory:

    ```yaml
    name: my-project
    description: A precompiled .NET Pulumi program.
    runtime:
      name: dotnet
      options:
        binary: bin/MyInfra.dll

    ```

* A `Pulumi.yaml` file for a Java program that uses a pre-built JAR file:

    ```yaml
    name: my-project
    description: A precompiled Java Pulumi program.
    runtime:
        name: java
        options:
            binary: target/my-project-1.0-SNAPSHOT-jar-with-dependencies.jar
    ```

* A `Pulumi.yaml` file for a `YAML` program that includes its resources inline:

    ```yaml
    name: my-project
    runtime: yaml
    resources:
      bucket:
        type: aws:s3:Bucket
    ```

For more information on valid Pulumi project metadata, see the [Pulumi.yaml reference](/docs/reference/pulumi-yaml/).

## Project-relative paths

When a Pulumi program references resources in the local filesystem, paths are always resolved relative to the working directory. In the following example, the `aws.ecr.Image` resource references a subfolder named `app` within the working directory that contains a `Dockerfile`:

{{< example-program path="awsx-ecr-image" >}}

## Root-relative paths

You can get the directory containing the `Pulumi.yaml` file, which may differ from your working directory if it specified a `main` option (see [main attribute](/docs/reference/pulumi-yaml/#attributes)), with the `ProjectDirectory` function.

The returned path is absolute. When passing it as a resource property, convert it to a path relative to the working directory. This avoids spurious diffs when the project runs on multiple machines with different root paths.

In CI environments, the working directory and the root path are commonly different, so the conversion step matters even when local development happens to put both at the same location. Always do the relative-path conversion at the boundary where the value enters resource configuration.

If you cannot determine the working directory at runtime, fall back to the project root and document the assumption. This makes downstream resource configuration easier to audit later.

{{< example-program path="awsx-root-directory" >}}

## Getting the current project programmatically

The {{< pulumi-getproject >}} function returns the name of the currently deploying project. This can be useful for naming or tagging resources.

{{< chooser language "typescript,python,go,csharp,java,yaml" >}}

{{% choosable language typescript %}}

```typescript
const project = pulumi.getProject();
```

{{% /choosable %}}
{{% choosable language python %}}

```python
project = pulumi.get_project()
```

{{% /choosable %}}
{{% choosable language go %}}

```go
project := ctx.Project()
```

{{% /choosable %}}
{{% choosable language csharp %}}

```csharp
var project = Deployment.Instance.ProjectName;
```

{{% /choosable %}}
{{% choosable language java %}}

```java
var project = ctx.projectName();
```

{{% /choosable %}}
{{% choosable language yaml %}}

```yaml
variables:
  project: ${pulumi.project}
```

{{% /choosable %}}

{{< /chooser >}}

## Stack settings files {#stack-settings-file}

Each stack that is created in a project will have a file named `Pulumi.<stackname>.yaml` that contains the configuration specific to this stack. This file typically resides in the root of the project directory.

For stacks that are actively developed by multiple members of a team, the recommended practice is to check them into source control as a means of collaboration. Since secret values are encrypted, it is safe to check in these stack settings. When using ephemeral stacks, the stack settings are typically not checked into source control.

For more information about configuration and how to manage these files on the command line and programmatically, refer to the [Configuration](/docs/concepts/config/) and [Secrets](/docs/concepts/secrets/) documentation.
