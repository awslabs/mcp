---
id: "SUS06-BP01"
title: "Communicate and cascade your sustainability goals"
pillar: "Sustainability"
risk_level: "MEDIUM"
capability: "How do your organizational processes support your sustainability goals?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/sustainability-pillar/sus_sus_dev_a1.html"
---

# SUS06-BP01 Communicate and cascade your sustainability goals

Technology is a key enabler of sustainability. IT teams play a
crucial role in driving meaningful change towards your
organization's sustainability goals. These teams should clearly
understand the company's sustainability targets and work to
communicate and cascade those priorities across its operations.

**Common anti-patterns:**

- You don't know your organization's sustainability goals and how
they apply to your team.
- You have insufficient awareness and training about the
environmental impact of cloud workloads.
- You are unsure about the specific areas to prioritize.
- You do not involve your employees and customers in your
sustainability initiatives.

**Benefits of establishing this best
practice:** From optimization of infrastructure and systems
to use of innovative technologies, IT teams can reduce the
organization's carbon emissions and minimize resource consumption.
Communication of sustainability goals can provide the ability for IT
teams continuously improve and adapt to evolving sustainability
challenges. Additionally, these sustainable optimizations often
translate to cost savings as well, which strengthens the business
case.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

The primary sustainability goals for IT teams should be to
optimize systems and solutions to increase resource efficiency and
minimize the organization's carbon footprint and overall
environmental impact. Shared services and initiatives like
training programs and operational dashboards can support
organizations as they optimize IT operations and build solutions
that can help significantly reduce the carbon footprint. The cloud
presents an opportunity not only to move physical infrastructure
and energy procurement responsibilities to the shared
responsibility of the cloud provider but also to continuously
optimize the resource efficiency of cloud-based services.

When teams use the cloud's inherent efficiency and shared
responsibility model, they can drive meaningful reductions in the
organization's environmental impact. This, in turn, can contribute
to the organization's overall sustainability goals and demonstrate
the value of these teams as strategic partners in the journey
towards a more sustainable future.

### Implementation steps

- **Define goals and
objectives:** Establish well-defined goals for your IT program. This involves getting input from
responsible stakeholders from different departments such as
IT, sustainability, and finance. These teams should define
measurable goals that align with your organization's
sustainability goals, including areas such carbon reduction
and resource optimization.
- **Understand the carbon accounting
boundaries of your business:** Understand how
carbon accounting methods like the Greenhouse Gas (GHG)
Protocol relate to your workloads in the cloud
(for more detail, see [Cloud
sustainability](https://docs.aws.amazon.com/wellarchitected/latest/sustainability-pillar/cloud-sustainability.html)).
- **Use cloud solutions for carbon
accounting:** Use cloud solutions such as
[carbon
accounting solutions on AWS](https://aws.amazon.com/solutions/sustainability/carbon-accounting/) to track scope one, two,
and three for GHG emissions across your operations,
portfolios, and value chains. With these solutions,
organizations can streamline GHG emission data acquisition,
simplify reporting, and derive insights to inform their
climate strategies.
- **Monitor the carbon footprint of your
IT portfolio:** Track and report carbon emissions
of your IT systems. Use the
[AWS Customer Carbon Footprint Tool](https://aws.amazon.com/aws-cost-management/aws-customer-carbon-footprint-tool/) to track, measure,
review, and forecast the carbon emissions generated from
your AWS usage.
- **Communicate resource usage through
proxy metrics to your teams:** Track and report on
your
[resource
usage through proxy metrics](https://docs.aws.amazon.com/wellarchitected/latest/sustainability-pillar/evaluate-specific-improvements.html). In the on-demand pricing
models of the cloud, resource usage is related to cost,
which is a generally-understandable metric. At a minimum,
use cost as a proxy metric to communicate the resource usage
and improvements by each team.

**Enable hourly granularity in
your Cost Explorer and create a
[Cost
and Usage Report (CUR)](https://aws.amazon.com/aws-cost-management/aws-cost-and-usage-reporting/):** The CUR
provides daily or hourly usage granularity, rates,
costs, and usage attributes for all AWS services. Use
[the
Cloud Intelligence Dashboards](https://catalog.workshops.aws/awscid/) and its
Sustainability Proxy Metrics Dashboard as a starting
point for the processing and visualization of cost and
usage based data. For more detail, see the following:
- [Measure
and track cloud efficiency with sustainability proxy
metrics, Part I: What are proxy metrics?](https://aws.amazon.com/blogs/aws-cloud-financial-management/measure-and-track-cloud-efficiency-with-sustainability-proxy-metrics-part-i-what-are-proxy-metrics/)
- [Measure
and track cloud efficiency with sustainability proxy
metrics, Part II: Establish a metrics pipeline](https://aws.amazon.com/blogs/aws-cloud-financial-management/measure-and-track-cloud-efficiency-with-sustainability-proxy-metrics-part-ii-establish-a-metrics-pipeline/)

- **Continuously optimize and
evaluate:** Use an
[improvement
process](https://docs.aws.amazon.com/wellarchitected/latest/sustainability-pillar/improvement-process.html) to continuously optimize your IT systems,
including cloud workload for efficiency and sustainability.
Monitor carbon footprint before and after implementation of
optimization strategy. Use the reduction in carbon footprint
to assess the effectiveness.
- **Foster a sustainability
culture:** Use training programs (like
[AWS Skill Builder](https://explore.skillbuilder.aws/learn/external-ecommerce;view=none;redirectURL=?ctldoc-catalog-0=se-sustainability)) to educate your employees about
sustainability. Engage them in sustainability initiatives.
Share and celebrate their success stories. Use incentives to
award them if they achieve sustainability targets.

## Resources

**Related documents:**

- [Understanding
your carbon emission estimations](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/ccft-estimation.html)

**Related videos:**

- [AWS re:Invent 2023 - Accelerate data-driven circular economy
initiatives with AWS](https://www.youtube.com/watch?v=ivTJorpUTo0)
- [AWS re:Invent 2023 - Sustainability innovation in AWS Global
Infrastructure](https://www.youtube.com/watch?v=0EkcwLKeOQA)
- [AWS re:Invent 2023 - Sustainable architecture: Past, present, and
future](https://www.youtube.com/watch?v=2xpUQ-Q4QcM)
- [AWS re:Invent 2022 - Delivering sustainable, high-performing
architectures](https://www.youtube.com/watch?v=FBc9hXQfat0)
- [AWS re:Invent 2022 - Architecting sustainably and reducing your
AWS carbon footprint](https://www.youtube.com/watch?v=jsbamOLpCr8)
- [AWS re:Invent 2022 - Sustainability in AWS global
infrastructure](https://www.youtube.com/watch?v=NgMa8R9-Ywk)

**Related examples:**

- [Well-Architected
Lab - Turning cost & usage reports into efficiency
reports](https://catalog.workshops.aws/well-architected-sustainability/en-US/5-process-and-culture/cur-reports-as-efficiency-reports)

**Related trainings:**

- [Sustainability
Transformation on AWS](https://explore.skillbuilder.aws/learn/course/internal/view/elearning/15981/sustainability-transformation-with-aws?trk=f5740d24-133a-44e7-bdca-e6669e296419&sc_channel=el)
- [SimuLearn
- Sustainability Reporting](https://explore.skillbuilder.aws/learn/course/internal/view/elearning/20240/aws-simulearn-sustainability-reporting)
- [Decarbonization
with AWS](https://explore.skillbuilder.aws/learn/course/internal/view/elearning/19030/decarbonization-with-aws-introduction)
