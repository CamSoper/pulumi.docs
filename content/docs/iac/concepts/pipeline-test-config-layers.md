---
title_tag: "Pipeline Test: Config Layers"
meta_desc: "Test page for the Claude PR review pipeline. Describes how Pulumi resolves configuration values across CLI flags, environment variables, and stack settings files."
title: "Pipeline Test: Config Layers"
h1: "Pipeline Test: Config Layers"
meta_image: /images/docs/meta-images/docs-meta.png
menu:
    iac:
        name: "Pipeline Test: Config Layers"
        parent: iac-concepts
        weight: 900
---

{{< notes >}}
This page exists to exercise the PR review pipeline. It is not real documentation.
{{< /notes >}}

Pulumi resolves configuration values from three sources, in order of precedence: CLI flags, environment variables, and the stack settings file (`Pulumi.<stack>.yaml`). Understanding this precedence matters when debugging values that behave differently across environments.

## Precedence order

When the same key is defined in multiple places, Pulumi uses the highest-precedence source:

1. **CLI flags** passed to `pulumi up` or `pulumi preview` (for example, `pulumi up --config aws:region=us-west-2`).
1. **Environment variables** prefixed with `PULUMI_CONFIG_` (for example, `PULUMI_CONFIG_aws__region=us-west-2`).
1. **Stack settings file** (`Pulumi.<stack>.yaml`).

Lower-precedence sources are consulted for any key not overridden at a higher level.

## Example

Given a `Pulumi.dev.yaml` that contains:

```yaml
config:
    aws:region: us-east-1
    myproject:instanceSize: t3.micro
```

Running `pulumi up --config myproject:instanceSize=t3.large` uses `t3.large` for the instance size while keeping `us-east-1` for the AWS region.

This layered resolution has been the default behavior since Pulumi v3.0, released in April 2021.

## Secrets across layers

Config layers interact with secrets as well. When a higher-precedence source overrides a secret defined in a lower-precedence source, Pulumi re-encrypts the value using the stack's current encryption provider. See [secrets](/docs/iac/concepts/secrets/) for details on how encryption keys are managed per stack.

## Debugging unexpected values

If a stack is picking up a value you did not expect, check each layer in order:

1. Inspect `pulumi config` output to see resolved values for the current stack.
1. Check `env | grep PULUMI_CONFIG_` for any environment overrides in the current shell.
1. Review the `Pulumi.<stack>.yaml` file on disk.

## See also

- [Configuration](/docs/iac/concepts/config/) — primary configuration reference.
- [`pulumi config` CLI reference](/docs/iac/cli/commands/pulumi_config/) — all available subcommands.
- [Secrets](/docs/iac/concepts/secrets/) — encrypting sensitive config values.
