---
id: "REL04-BP03"
title: "Do constant work"
pillar: "Reliability"
risk_level: "LOW"
capability: "How do you design interactions in a distributed system to prevent failures?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_prevent_interaction_failure_constant_work.html"
description: "Systems can fail when there are large, rapid changes in load. For example, if your workload is doing a health check that monitors the health of thousands of servers, it should send the same size payload (a full snapshot of the current state) each time. Whether no servers are failing, or all of them, the health check system is doing constant work with no large, rapid changes."
area: ["Workload architecture", "Design interactions in a distributed system to prevent failures"]
---

# REL04-BP03 Do constant work

Systems can fail when there are large, rapid changes in load. For
example, if your workload is doing a health check that monitors the
health of thousands of servers, it should send the same size payload
(a full snapshot of the current state) each time. Whether no servers
are failing, or all of them, the health check system is doing
constant work with no large, rapid changes.

For example, if the health check system is monitoring 100,000
servers, the load on it is nominal under the normally light server
failure rate. However, if a major event makes half of those servers
unhealthy, then the health check system would be overwhelmed trying
to update notification systems and communicate state to its clients.
So instead the health check system should send the full snapshot of
the current state each time. 100,000 server health states, each
represented by a bit, would only be a 12.5-KB payload. Whether no
servers are failing, or all of them are, the health check system is
doing constant work, and large, rapid changes are not a threat to
the system stability. This is actually how Amazon Route 53 handles
health checks for endpoints (such as IP addresses) to determine how
end users are routed to them.

**Level of risk exposed if this best practice
is not established:** Low

## Implementation guidance

- Do constant work so that systems do not fail when there are large,
rapid changes in load.
- Implement loosely coupled dependencies. Dependencies such as
queuing systems, streaming systems, workflows, and load balancers
are loosely coupled. Loose coupling helps isolate behavior of a
component from other components that depend on it, increasing
resiliency and agility.

[The
Amazon Builders' Library: Reliability, constant work, and a good cup of
coffee](https://aws.amazon.com/builders-library/reliability-and-constant-work/)
- [AWS re:Invent 2018: Close Loops and
Opening Minds: How to Take Control of Systems, Big and Small ARC337 (includes
constant work)](https://youtu.be/O8xLxNje30M?t=2482)

For the example of a health check system monitoring 100,000 servers, engineer
workloads so that payload sizes remain constant regardless of number of successes
or failures.

## Resources

**Related documents:**

- [Amazon EC2: Ensuring Idempotency](https://docs.aws.amazon.com/AWSEC2/latest/APIReference/Run_Instance_Idempotency.html)
- [The
Amazon Builders' Library: Challenges with distributed
systems](https://aws.amazon.com/builders-library/challenges-with-distributed-systems/)
- [The
Amazon Builders' Library: Reliability, constant work, and a
good cup of coffee](https://aws.amazon.com/builders-library/reliability-and-constant-work/)

**Related videos:**

- [AWS New York
Summit 2019: Intro to Event-driven Architectures and Amazon EventBridge (MAD205)](https://youtu.be/tvELVa9D9qU)
- [AWS re:Invent 2018: Close Loops and Opening Minds: How to Take
Control of Systems, Big and Small ARC337 (includes constant
work)](https://youtu.be/O8xLxNje30M?t=2482)
- [AWS re:Invent
2018: Close Loops and Opening Minds: How to Take Control of
Systems, Big and Small ARC337 (includes loose coupling, constant work, static stability)](https://youtu.be/O8xLxNje30M)
- [AWS re:Invent
2019: Moving to event-driven architectures (SVS308)](https://youtu.be/h46IquqjF3E)
