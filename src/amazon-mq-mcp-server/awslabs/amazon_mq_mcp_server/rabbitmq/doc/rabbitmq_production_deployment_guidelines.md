# Minimum Hardware Requirements

RabbitMQ can used with a broad range of workloads. Some may be very I/O heavy (streams), others can require more CPU resources (large number of concurrent connections and queues). Those workloads may require a different mix of CPU, storage and network resources.

Below is a minimum system requirements for production deployments, per node:
- No colocation with other data services (e.g. data stores) or disk, network I/O heavy applications
- 4 CPU cores
- 4 GiB of RAM

> ⚠️ **Important:** RabbitMQ was not designed to run in environments with a single CPU core, or being colocated with other disk and network I/O-heavy tools.

# Storage Considerations

Data safety features of quorum queues and streams expect node data storage to be durable. Both data structures also assume reasonably stable latency of I/O operations, something that network-attached storage will not be always ready to provide in practice.

Quorum queue and stream replicas hosted on restarted nodes that use transient storage will have to perform a full sync of the entire data set on the leader replica. This can result in massive data transfers and network link overload that could have been avoided by using durable storage.

When nodes are restarted, the rest of the cluster expects them to retain the information about their cluster peers. When this is not the case, restarted nodes may be able to rejoin as new nodes but a special peer clean up mechanism would have to be enabled to remove their prior identities.

Transient entities (such as queues) and RAM node support will be removed in RabbitMQ 4.x.

# Overprovision Disk Space

Quorum queues and streams can have substantial on-disk footprint. Depending on the workload and settings, they may or may not reclaim disk space of consumed and confirmed or expired messages quickly.

The rule of thumb is: when in doubt, overprovision the disks that RabbitMQ nodes will use.

# Virtual Hosts, Users, Permissions

It is often necessary to seed a cluster with virtual hosts, users, permissions, topologies, policies and so on. The recommended way of doing this at deployment time is via definition import. Definitions can be imported on node boot or at any point after cluster deployment using rabbitmqadmin or the POST /api/definitions HTTP API endpoint.

### Virtual Hosts

In a single-tenant environment, for example, when your RabbitMQ cluster is dedicated to power a single system in production, using default virtual host (/) is perfectly fine.

In multi-tenant environments, use a separate vhost for each tenant/environment, e.g. project1_development, project1_production, project2_development, project2_production, and so on.

### Users

For production environments, delete the default user (guest). Default user only can connect from localhost by default, because it has well-known credentials. Instead of enabling remote connections, consider creating a separate user with administrative permissions and a generated password.

It is recommended to use a separate user per application. For example, if you have a mobile app, a Web app, and a data aggregation system, you'd have 3 separate users. This makes a number of things easier:

- Correlating client connections with applications
- Using fine-grained permissions
- Credentials roll-over (e.g. periodically or in case of a breach)

In case there are many instances of the same application, there's a trade-off between better security (having a set of credentials per instance) and convenience of provisioning (sharing a set of credentials between some or all instances).

For production environments, it is almost always a good idea to disable anonymous logins.
