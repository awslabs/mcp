---
id: "REL05-BP07"
title: "Implement emergency levers"
pillar: "Reliability"
risk_level: "MEDIUM"
capability: "How do you design interactions in a distributed system to mitigate or withstand failures?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_emergency_levers.html"
---

# REL05-BP07 Implement emergency levers

Emergency levers are rapid processes that can mitigate availability
impact on your workload.

Emergency levers work by disabling, throttling, or changing the behavior of components or dependencies using known and tested mechanisms. This can alleviate workload impairments caused by resource exhaustion due to unexpected increases in demand and reduce the impact of failures in non-critical components within your workload.

**Desired outcome:** By implementing emergency levers, you can establish known-good processes to maintain the availability of critical components in your workload. The workload should degrade gracefully and continue to perform its business-critical functions during the activation of an emergency lever. For more detail on graceful degradation, see [REL05-BP01 Implement graceful degradation to transform applicable hard dependencies into soft dependencies](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_mitigate_interaction_failure_graceful_degradation.html).

**Common anti-patterns:**

- Failure of non-critical dependencies impacts the availability of your core workload.
- Not testing or verifying critical component behavior during non-critical component impairment.
- No clear and deterministic criteria defined for activation or deactivation of an emergency lever.

**Benefits of establishing this best practice:** Implementing emergency levers can improve the availability of the critical components in your workload by providing your resolvers with established processes to respond to unexpected spikes in demand or failures of non-critical dependencies.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

- Identify critical components in your workload.
- Design and architect the critical components in your workload to withstand failure of non-critical components.
- Conduct testing to validate the behavior of your critical components during the failure of non-critical components.
- Define and monitor relevant metrics or triggers to initiate emergency lever procedures.
- Define the procedures (manual or automated) that comprise the emergency lever.

### Implementation steps

- Identify business-critical components in your workload.

Each technical component in your workload should be mapped to its relevant business function and ranked as critical or non-critical. For examples of critical and non-critical functionality at Amazon, see [Any Day Can Be Prime Day: How Amazon.com Search Uses Chaos Engineering to Handle Over 84K Requests Per Second](https://community.aws/posts/how-search-uses-chaos-engineering).
- This is both a technical and business decision, and varies by organization and workload.

- Design and architect the critical components in your workload to withstand failure of non-critical components.

During dependency analysis, consider all potential failure modes, and verify that your emergency lever mechanisms deliver the critical functionality to downstream components.

- Conduct testing to validate the behavior of your critical components during activation of your emergency levers.

Avoid bimodal behavior. For more detail, see [REL11-BP05 Use static stability to prevent bimodal behavior](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_withstand_component_failures_static_stability.html).

- Define, monitor, and alert on relevant metrics to initiate the emergency lever procedure.

Finding the right metrics to monitor depends on your workload. Some example metrics are latency or the number of failed request to a dependency.

- Define the procedures, manual or automated, that comprise the emergency lever.

This may include mechanisms such as [load shedding](https://aws.amazon.com/builders-library/using-load-shedding-to-avoid-overload/), [throttling requests](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_mitigate_interaction_failure_throttle_requests.html), or implementing [graceful degradation](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_mitigate_interaction_failure_graceful_degradation.html).

## Resources

**Related best practices:**

- [REL05-BP01 Implement graceful degradation to transform applicable hard dependencies into soft dependencies](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_mitigate_interaction_failure_graceful_degradation.html)
- [REL05-BP02 Throttle requests](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_mitigate_interaction_failure_throttle_requests.html)
- [REL11-BP05 Use static stability to prevent bimodal behavior](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_withstand_component_failures_static_stability.html)

**Related documents:**

- [Automating safe, hands-off deployments](https://aws.amazon.com/builders-library/automating-safe-hands-off-deployments/)
- [Any Day Can Be Prime Day: How Amazon.com Search Uses Chaos Engineering to Handle Over 84K Requests Per Second](https://community.aws/posts/how-search-uses-chaos-engineering)

**Related videos:**

- [AWS re:Invent 2020: Reliability, consistency, and confidence through immutability](https://www.youtube.com/watch?v=jUSYnRztttY)
