"""Configuration for MSK cluster metrics."""

from typing import Any, Dict

# Mapping of metrics to their configurations
METRICS = {
    "CpuUser": {
        "monitoring_level": "DEFAULT",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The percentage of CPU utilization by the Kafka broker.",
    },
    "MemoryUsed": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The amount of memory used by the broker.",
    },
    "KafkaDataLogsDiskUsed": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The amount of disk space used for Kafka data logs.",
    },
    "NetworkRxThroughput": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The incoming (receive) network throughput in bytes per second.",
    },
    "NetworkTxThroughput": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The outgoing (transmit) network throughput in bytes per second.",
    },
    "RootDiskUsed": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The amount of root disk space used by the broker.",
    },
    "MessagesInPerSec": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID", "Topic"],
        "default_statistic": "Average",
        "description": "The number of messages received per second.",
    },
    "OfflinePartitionsCount": {
        "monitoring_level": "DEFAULT",
        "dimensions": ["Cluster Name"],
        "default_statistic": "Sum",
        "description": "The number of partitions that don't have an active leader and are therefore not readable or writable.",
    },
    "UnderReplicatedPartitions": {
        "monitoring_level": "DEFAULT",
        "dimensions": ["Cluster Name"],
        "default_statistic": "Sum",
        "description": "The number of partition replicas that are not in sync with their leaders.",
    },
    "GlobalPartitionCount": {
        "monitoring_level": "DEFAULT",
        "dimensions": ["Cluster Name"],
        "default_statistic": "Sum",
        "description": "The total number of partitions in the cluster.",
    },
    "GlobalTopicCount": {
        "monitoring_level": "DEFAULT",
        "dimensions": ["Cluster Name"],
        "default_statistic": "Sum",
        "description": "The total number of topics in the cluster.",
    },
    "PartitionCount": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Sum",
        "description": "The number of partitions on this broker.",
    },
    "EstimatedMaxTimeLag": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Maximum",
        "description": "The estimated maximum time lag in milliseconds for replicas to catch up with the leader.",
    },
    "LeaderCount": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Sum",
        "description": "The number of partitions for which this broker is the leader.",
    },
    "ActiveControllerCount": {
        "monitoring_level": "DEFAULT",
        "dimensions": ["Cluster Name"],
        "default_statistic": "Maximum",
        "description": "Only one controller per cluster should be active at any given time.",
    },
    "BurstBalance": {
        "monitoring_level": "DEFAULT",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The remaining balance of input-output burst credits for EBS volumes in the cluster. Use it to investigate latency or decreased throughput.",
    },
    "BytesInPerSec": {
        "monitoring_level": "DEFAULT",
        "dimensions": ["Cluster Name", "Broker ID", "Topic"],
        "default_statistic": "Sum",
        "description": "The number of bytes per second received from clients. This metric is available per broker and also per topic.",
    },
    "BytesOutPerSec": {
        "monitoring_level": "DEFAULT",
        "dimensions": ["Cluster Name", "Broker ID", "Topic"],
        "default_statistic": "Sum",
        "description": "The number of bytes per second sent to clients. This metric is available per broker and also per topic.",
    },
    "BwInAllowanceExceeded": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Sum",
        "description": "The number of packets shaped because the inbound aggregate bandwidth exceeded the maximum for the broker.",
    },
    "BwOutAllowanceExceeded": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Sum",
        "description": "The number of packets shaped because the outbound aggregate bandwidth exceeded the maximum for the broker.",
    },
    "ConntrackAllowanceExceeded": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Sum",
        "description": "The number of packets shaped because the connection tracking exceeded the maximum for the broker. Connection tracking is related to security groups that track each connection established to ensure that return packets are delivered as expected.",
    },
    "ConnectionCloseRate": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The number of connections closed per second per listener. This number is aggregated per listener and filtered for the client listeners.",
    },
    "ConnectionCreationRate": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The number of new connections established per second per listener. This number is aggregated per listener and filtered for the client listeners.",
    },
    "CpuCreditUsage": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The number of CPU credits spent by the broker. If you run out of the CPU credit balance, it can have a negative impact on your cluter's performance. You can take steps to reduce CPU load. For example, you can reduce the number of client requests or update the broker type to an M5 broker type.",
    },
    "FetchConsumerLocalTimeMsMean": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The mean time in milliseconds that the consumer request is processed at the leader.",
    },
    "FetchConsumerRequestQueueTimeMsMean": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The mean time in milliseconds that the consumer request waits in the request queue.",
    },
    "FetchConsumerResponseQueueTimeMsMean": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The mean time in milliseconds that the consumer request waits in the response queue.",
    },
    "FetchConsumerResponseSendTimeMsMean": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The mean time in milliseconds for the consumer to send a response.",
    },
    "FetchConsumerTotalTimeMsMean": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The mean total time in milliseconds that consumers spend on fetching data from the broker.",
    },
    "FetchFollowerLocalTimeMsMean": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The mean time in milliseconds that the follower request is processed at the leader.",
    },
    "FetchFollowerRequestQueueTimeMsMean": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The mean time in milliseconds that the follower request waits in the request queue.",
    },
    "FetchFollowerResponseQueueTimeMsMean": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The mean time in milliseconds that the follower request waits in the response queue.",
    },
    "FetchFollowerResponseSendTimeMsMean": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The mean time in milliseconds for the follower to send a response.",
    },
    "FetchFollowerTotalTimeMsMean": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The mean total time in milliseconds that followers spend on fetching data from the broker.",
    },
    "FetchMessageConversionsPerSec": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The number of fetch message conversions per second for the broker.",
    },
    "FetchThrottleByteRate": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The number of throttled bytes per second.",
    },
    "FetchThrottleQueueSize": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The number of messages in the throttle queue.",
    },
    "FetchThrottleTime": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The average fetch throttle time in milliseconds.",
    },
    "IAMNumberOfConnectionRequests": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Sum",
        "description": "The number of IAM authentication requests per second.",
    },
    "IAMTooManyConnections": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Sum",
        "description": "The number of connections attempted beyond 100. 0 means the number of connections is within the limit. If >0, the throttle limit is being exceeded and you need to reduce number of connections.",
    },
    "NetworkProcessorAvgIdlePercent": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The average percentage of the time the network processors are idle.",
    },
    "PpsAllowanceExceeded": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Sum",
        "description": "The number of packets shaped because the bidirectional PPS exceeded the maximum for the broker.",
    },
    "ProduceLocalTimeMsMean": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The mean time in milliseconds that the request is processed at the leader.",
    },
    "ProduceMessageConversionsPerSec": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The number of produce message conversions per second for the broker.",
    },
    "ProduceMessageConversionsTimeMsMean": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The mean time in milliseconds spent on message format conversions.",
    },
    "ProduceRequestQueueTimeMsMean": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The mean time in milliseconds that request messages spend in the queue.",
    },
    "ProduceResponseQueueTimeMsMean": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The mean time in milliseconds that response messages spend in the queue.",
    },
    "ProduceResponseSendTimeMsMean": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The mean time in milliseconds spent on sending response messages.",
    },
    "ProduceThrottleByteRate": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The number of throttled bytes per second.",
    },
    "ProduceThrottleQueueSize": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The number of messages in the throttle queue.",
    },
    "ProduceThrottleTime": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The average produce throttle time in milliseconds.",
    },
    "ProduceTotalTimeMsMean": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The mean produce time in milliseconds.",
    },
    "RemoteFetchBytesPerSec": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The total number of bytes transferred from tiered storage in response to consumer fetches.",
    },
    "RemoteCopyBytesPerSec": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The total number of bytes transferred to tiered storage, including data from log segments, indexes, and other auxiliary files.",
    },
    "RemoteLogManagerTasksAvgIdlePercent": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The average percentage of time the remote log manager spent idle.",
    },
    "RemoteLogReaderAvgIdlePercent": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The average percentage of time the remote log reader spent idle.",
    },
    "RemoteLogReaderTaskQueueSize": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The number of tasks responsible for reads from tiered storage that are waiting to be scheduled.",
    },
    "RemoteFetchErrorsPerSec": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The total rate of errors in response to read requests that the specified broker sent to tiered storage.",
    },
    "RemoteFetchRequestsPerSec": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The total number of read requests that the specifies broker sent to tiered storage.",
    },
    "RemoteCopyErrorsPerSec": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The total rate of errors in response to write requests that the specified broker sent to tiered storage.",
    },
    "RemoteLogSizeBytes": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The number of bytes stored on the remote tier.",
    },
    "ReplicationBytesInPerSec": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The number of bytes per second received from other brokers.",
    },
    "ReplicationBytesOutPerSec": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The number of bytes per second sent to other brokers.",
    },
    "RequestExemptFromThrottleTime": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The average time in milliseconds spent in broker network and I/O threads to process requests that are exempt from throttling.",
    },
    "RequestHandlerAvgIdlePercent": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The average percentage of the time the request handler threads are idle.",
    },
    "RequestThrottleQueueSize": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The number of messages in the throttle queue.",
    },
    "RequestThrottleTime": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The average request throttle time in milliseconds.",
    },
    "TcpConnections": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "Shows number of incoming and outgoing TCP segments with the SYN flag set.",
    },
    "RemoteCopyLagBytes": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The total number of bytes of the data that is eligible for tiering on the broker but has not been transferred to tiered storage yet.",
    },
    "TrafficBytes": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Sum",
        "description": "Shows network traffic in overall bytes between clients (producers and consumers) and brokers. Traffic between brokers isn't reported.",
    },
    "VolumeQueueLength": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Average",
        "description": "The number of read and write operation requests waiting to be completed in a specified time period.",
    },
    "VolumeReadBytes": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Sum",
        "description": "The number of bytes read in a specified time period.",
    },
    "VolumeReadOps": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Sum",
        "description": "The number of read operations in a specified time period.",
    },
    "VolumeTotalReadTime": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Sum",
        "description": "The total number of seconds spent by all read operations that completed in a specified time period.",
    },
    "VolumeTotalWriteTime": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Sum",
        "description": "The total number of seconds spent by all write operations that completed in a specified time period.",
    },
    "VolumeWriteBytes": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Sum",
        "description": "The number of bytes written in a specified time period.",
    },
    "VolumeWriteOps": {
        "monitoring_level": "PER_BROKER",
        "dimensions": ["Cluster Name", "Broker ID"],
        "default_statistic": "Sum",
        "description": "The number of write operations in a specified time period.",
    },
}


def get_metric_config(metric_name: str) -> Dict[str, Any]:
    """Get the configuration for a specific metric.

    Args:
        metric_name: The name of the metric

    Returns:
        Dictionary containing the metric configuration

    Raises:
        KeyError: If the metric configuration is not found
    """
    try:
        return METRICS[metric_name]
    except KeyError:
        raise KeyError(f"No configuration found for metric {metric_name}")
