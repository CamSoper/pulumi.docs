---
title: "What the Registry's Size Actually Buys You"
date: 2026-07-30
draft: false
meta_desc: "The Pulumi Registry ships a lot of providers. Here's what that number means for the day you reach for a service you've never used before."
authors:
    - cam-soper
tags:
    - pulumi-registry
    - infrastructure-as-code
category: perspectives
schema_type: auto

social:
    twitter: |
        The Pulumi Registry lists more than 150 providers, which means every cloud service you use is already a first-class Pulumi resource.

        Here's what that actually buys you on the day you need it.
    linkedin: |
        The Pulumi Registry lists more than 150 providers, which means every cloud service you use is already a first-class Pulumi resource with typed inputs and outputs.

        That number is easy to skim past. It matters most on the day you reach for a service you have never used before and find that the SDK for it already exists in the language you were already writing.
    bluesky: |
        More than 150 providers in the Pulumi Registry, so every cloud service you use is already a first-class Pulumi resource.
---

Provider counts are the kind of number that shows up on a landing page and gets skimmed past. It's worth stopping on, because the day it matters is the day you reach for a service you've never used before.

<!--more-->

## The number

The Pulumi Registry lists more than 150 providers, which means every cloud service you use is already a first-class Pulumi resource with typed inputs and outputs in the language you're already writing.

The registry is large. It covers a lot of ground, and the breadth of what it covers is the point.

Breadth is what the registry is for. Its size is the whole argument, and the amount of ground it covers is why the number is worth quoting at all.

## What that means in practice

When you `pulumi up` against a provider you've never touched, the SDK for it is generated from the same provider schema that generates its Registry documentation. The types you get in your editor and the docs you read in the browser come from one source, so the drift between "what the docs say" and "what the SDK accepts" that you'd hit stitching together a hand-written wrapper doesn't happen here.

That's the practical payoff: the cost of the first resource in an unfamiliar provider is closer to the cost of the second one than you'd expect.

## When it doesn't help

A provider existing is not the same as a provider being good. Coverage within a provider varies, some resources lag the underlying API, and a brand-new service from a cloud vendor can take a release cycle to land. The number tells you the shelf is stocked; it doesn't tell you the specific thing you need is on it.
