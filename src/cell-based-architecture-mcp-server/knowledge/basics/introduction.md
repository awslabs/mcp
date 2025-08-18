# Introduction to Cell-Based Architecture

## Overview

Resilience is the ability for workloads—a collection of resources and code that delivers business value, such as a customer-facing application or backend process—to respond and quickly recover from failures.

At AWS, we strive to build, operate, and deliver extremely resilient services, and build recovery mechanisms and mitigations, while keeping in mind that everything fails all the time. AWS provides different isolation boundaries, such as Availability Zones (AZs), AWS Regions, control planes, and data planes. These are not the only mechanisms we use. For more than a decade, our service teams have used cell-based architecture to build more resilient and scalable services.

## Key Concepts

Every organization is at a different point in their resilience journey—some are just beginning, while others might be more advanced and may require extreme levels of resilience in their applications. For these types of applications, this guidance can help you increase the resiliency of your applications and increase the trust of your services with your customers.

Cell-based architecture can give your workload more:
- **Fault isolation**
- **Predictability** 
- **Testability**

These are fundamental properties for workloads that need extreme levels of resilience.

## Modern Challenges

Today, modern organizations face an increasing number of challenges related to resiliency:
- Scalability and availability challenges
- Customer expectations of "always on, always available" systems
- Remote teams and complex distributed systems
- Growing need for frequent launches
- Acceleration of teams, processes, and systems moving from centralized to distributed models

All of this means that an organization and its systems need to be more resilient than ever.

## Multi-Tenant Reality

With the increasing use of cloud computing, sharing resources efficiently has become easier. The development of multi-tenant applications is increasing exponentially, but although the use of the cloud is more understood and customers are aware that they are in a multi-tenant environment, what they still want is the experience of a single-tenant environment.