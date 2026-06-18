---
title_tag: "Get started with environments"
meta_desc: "Open your first Pulumi ESC environment and wire it into a stack."
title: Get started with environments
h1: Get started with environments
---

# Get started with environments

This guide shows you how to deploy your first environment in three steps. By the
end, your applications can pull their configuration from the environment.

## Step 1 — Open your environment

Open the environment and load its configuration into your shell:

```bash
esc env open my-org/my-project/dev
```

The values defined in the environment are now available to your process for the
rest of the session.

## Step 2 — Reference the environment from your stack

Add an `environment` block to your stack so it imports the settings from the
environment you opened above:

```yaml
environment:
  - my-project/dev
```

When you run an update, the stack reads its configuration from the environment
instead of from local files.

## Step 3 — Run your program

Run `pulumi up`. Your program now resolves its configuration through the
environment, so the same values are available everywhere the environment is
imported.

That's it — your application is wired to Pulumi ESC.
