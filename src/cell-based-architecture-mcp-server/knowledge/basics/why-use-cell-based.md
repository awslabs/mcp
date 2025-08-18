# Why Use Cell-Based Architecture?

## Main Advantages

### Scale-out over Scale-up

**Scaling up** accommodates growth by increasing the size of a system's component (database, server, subsystem).

**Scaling out** accommodates growth by increasing the number of system components and dividing the workload such that the load on any component stays bounded over time.

Benefits of scaling out:
- **Workload isolation** - Dividing workload across components provides failure containment
- **Maximally-sized components** - Component size can be capped to maximum size, reducing risk of surprises
- **Not too big to test** - Components can be stress tested and pushed past breaking point

### Lower Scope of Impact

Breaking a service into multiple cells reduces the scope of impact. Cells represent bulkheaded units that provide containment for many common failure scenarios. When properly isolated, cells have failure containment similar to AWS Regions.

### Higher Scalability

Cell-based architectures scale-out rather than scale-up, and are inherently more scalable. When scaling up, you can reach resource limits of a particular service, instance, or AWS account. Scaling out within an AZ, Region, and AWS account helps avoid reaching limits of specific services or resources.

### Higher Testability

Testing distributed systems is challenging and amplified as the system grows. The capped size of cells allows for well-understood and testable maximum scale behavior. It's easier to test cells compared to bulk services since cells have limited size.

### Higher Mean Time Between Failure (MTBF)

- Cells have consistent capped size that is regularly tested and operated
- Eliminates the "every day is a new adventure" dynamic
- Problems can be identified locally with customers distributed among cells
- Gradual deployment strategies allow better management of system changes

### Lower Mean Time to Recovery (MTTR)

- Cells are easier to recover because they limit the number of hosts for problem diagnosis
- Predictability of size and scale makes recovery more predictable
- Emergency code and configuration deployment is more contained

### Higher Availability

Cell-based architectures achieve higher overall availability through:
- Higher MTBF and lower MTTR per cell
- Fewer, shorter failure events per cell
- Minimizing time when successful requests drop to zero

Formula: `#successful requests / #total requests`

### More Control Over Deployments

- Cells provide another dimension for phased deployments
- Reduces scope of impact from problematic deployments
- First cell can be a canary cell
- Each cell can have its own canary with synthetic workloads
- Combines canary deployment strategy with even lesser impact context