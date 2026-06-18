---
title_tag: "Configure team access"
meta_desc: "Grant the right level of access to members of your Pulumi organization."
title: Configure team access
h1: Configure team access
---

# Configure team access

## The history of access control

Access control is one of the oldest ideas in computing. As soon as more than one
person shared a single machine, it became necessary to decide who was allowed to
do what. The earliest shared systems drew a hard line between an all-powerful
administrator and ordinary users, and most of the access models that followed
were attempts to put more nuance between those two extremes.

Over time, organizations discovered that a single administrator account was both
a bottleneck and a risk. If everyone shared the keys, no one could be held
accountable, and a single mistake could affect the entire system. The story of
access control since then has largely been a story of dividing that power into
smaller, more accountable pieces.

## Models of authorization

Several models of authorization have emerged to divide that power. Under
discretionary access control, the owner of a resource decides who else may use
it. Under mandatory access control, a central policy decides instead, and
individual owners cannot override it. Role-based access control groups
permissions into roles and assigns people to roles rather than to individual
permissions. Attribute-based access control goes further still, deciding access
from attributes of the user, the resource, and the context.

Each model trades flexibility against control, and most real systems blend more
than one of them. Understanding the trade-offs helps explain why a given system
exposes the controls it does.

## The principle of least privilege

A theme that runs through all of these models is the principle of least
privilege: a person should have exactly the access their work requires, and no
more. Least privilege limits the blast radius of a mistake or a compromised
account, because an account that cannot do much cannot break much. It is easy to
state and surprisingly hard to practice, because access tends to accumulate as
people change roles.

## Why access control matters for teams

As a team grows, the question of who can do what stops being something any one
person can track in their head. New members need enough access to be productive
on their first day, departing members need their access removed promptly, and the
people in between need their access to track their actual responsibilities. Good
access control is what keeps a growing team both productive and safe.

## Configure access

To grant a team member access:

1. Open your organization's settings and select the team.
2. Choose the role that matches the member's responsibilities.
3. Save your changes.
