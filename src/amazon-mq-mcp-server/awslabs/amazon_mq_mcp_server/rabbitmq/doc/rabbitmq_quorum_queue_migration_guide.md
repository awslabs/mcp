You can migrate your classic mirrored queues to quorum queues on Amazon MQ brokers on version 3.13 or above by creating a new virtual host on the same cluster, or by migrating in place.

## Option 1: Migrating from classic mirrored queues to quorum queues with a new virtual host

You can migrate your classic mirrored queues to quorum queues on Amazon MQ brokers on version 3.13 or above by creating a new virtual host on the same cluster.

- In your existing cluster, create a new virtual host (vhost) with the default queue type as quorum.
- Create the Federation plugin from the new vhost with the URI pointing to the old vhost using classic mirrored queues.
- Using rabbitmqadmin, export the definitions from the old vhost to a new file. You must make changes to the schema file so it is compatible with quorum queues.  After applying the necessary changes to the file, reimport the definitions to the new vhost.
- Create a new policy in the new vhost. For recommendations on Amazon MQ policy configurations for quorum queues. Then, start the Federation you created earlier from the old vhost to the new vhost.
- Point consumers and producers to the new vhost.
- Configure the Shovel plug in to move any remaining messages. Once a queue is empty, delete the Shovel.

## Option 2: Migrating from classic mirrored queues to quorum queues in place

You can migrate your classic mirrored queues to quorum queues on Amazon MQ brokers on version 3.13 or above by migrating in place.

- Stop the consumers and producers.
- Create a new temporary quorum queue.
- Configure the Shovel plug in to move any messages from the old classic mirrored queue to the new temporary quorum queue. After all messages are moved to the temporary quorum queue, delete the Shovel.
- Delete the source classic mirrored queue. Then, recreate a quorum queue with the same name and bindings as the source classic mirrored queue.
- Create a new Shovel to move the messages from the temporary quorum queue to the new quorum queue.

You can get more information on the migration from official RabbitMQ open source guidelines:
- https://www.rabbitmq.com/blog/2023/03/02/quorum-queues-migration#moving-definitions
