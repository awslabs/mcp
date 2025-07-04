import json
import uuid
import logging
import time
from chaosmesh.client import Client, Experiment
from chaosmesh.k8s.selector import Selector
from kubernetes import client as k8s_client, config as k8s_config
from kubernetes.client.exceptions import ApiException
import os

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_kubernetes_config():
    """
    初始化Kubernetes配置，确保能正确连接到EKS集群
    """
    try:
        # 检查是否在集群内运行
        if os.path.exists('/var/run/secrets/kubernetes.io/serviceaccount'):
            logger.info("Loading in-cluster Kubernetes configuration")
            k8s_config.load_incluster_config()
        else:
            logger.info("Loading Kubernetes configuration from kubeconfig")
            k8s_config.load_kube_config()
        
        # 验证连接
        v1_test = k8s_client.CoreV1Api()
        namespaces = v1_test.list_namespace(limit=1)
        logger.info(f"✓ Kubernetes connection verified - found {len(namespaces.items)} namespace(s)")
        
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Kubernetes configuration: {e}")
        logger.error("Please ensure:")
        logger.error("1. kubectl is configured and can access the cluster")
        logger.error("2. For EKS: aws eks update-kubeconfig --region <region> --name <cluster-name>")
        logger.error("3. IAM permissions include eks:DescribeCluster and appropriate RBAC permissions")
        return False

def initialize_chaos_mesh_client():
    """
    初始化Chaos Mesh客户端，包含健康检查
    """
    try:
        # 首先确保Kubernetes配置已正确加载
        if not initialize_kubernetes_config():
            raise Exception("Kubernetes configuration failed")
        
        # 创建Chaos Mesh客户端
        client = Client(version="v1alpha1")
        
        # 验证Chaos Mesh是否可用
        v1 = k8s_client.CoreV1Api()
        
        # 检查chaos-mesh命名空间是否存在
        try:
            v1.read_namespace("chaos-mesh")
            logger.info("Chaos Mesh namespace found")
        except ApiException as e:
            if e.status == 404:
                logger.error("Chaos Mesh namespace not found. Please install Chaos Mesh first.")
                raise Exception("Chaos Mesh not installed")
            else:
                raise
        
        # 检查Chaos Mesh控制器是否运行
        pods = v1.list_namespaced_pod(
            namespace="chaos-mesh",
            label_selector="app.kubernetes.io/name=chaos-mesh"
        )
        
        running_pods = [pod for pod in pods.items if pod.status.phase == "Running"]
        if not running_pods:
            logger.error("No running Chaos Mesh controller pods found")
            raise Exception("Chaos Mesh controller not running")
        
        logger.info(f"Found {len(running_pods)} running Chaos Mesh controller pods")
        return client
        
    except Exception as e:
        logger.error(f"Failed to initialize Chaos Mesh client: {e}")
        logger.error("Please ensure:")
        logger.error("1. Chaos Mesh is installed: helm install chaos-mesh chaos-mesh/chaos-mesh -n chaos-mesh --create-namespace")
        logger.error("2. Chaos Mesh controllers are running")
        logger.error("3. RBAC permissions are correctly configured")
        raise

# 初始化客户端
try:
    client = initialize_chaos_mesh_client()
except Exception as e:
    logger.error(f"Chaos Mesh client initialization failed: {e}")
    client = None

__all__ = [
    "pod_fault",
    "pod_stress_test",
    "host_stress_test",
    "host_disk_fault",
    "network_fault",
    "delete_experiment",
]


def pod_fault(service: str, type: str, namespace: str = "default", **kwargs) -> dict:
    """
    Inject a fault into a pod
    Args:
        service (str): The name of the service to inject the fault into, e.g., "adservice".
        type (str): The type of fault to inject, one of "POD_FAILURE", "POD_KILL", "CONTAINER_KILL".
            - POD_FAILURE: Simulate a pod failure.
            - POD_KILL: Simulate a pod kill.
            - CONTAINER_KILL: Simulate a container kill.
        namespace (str): The namespace where the service is located. Default is "default".
        kwargs: Additional arguments for the experiment.
            - duration (str): The duration of the experiment, e.g., "5m" for 5 minutes.
            - container_names (list[str]): The names of the containers to inject the fault into, only used for "CONTAINER_KILL".
            - mode (str): The mode of the experiment, The mode options include one (selecting a random Pod), all (selecting all eligible Pods), fixed (selecting a specified number of eligible Pods), fixed-percent (selecting a specified percentage of Pods from the eligible Pods), and random-max-percent (selecting the maximum percentage of Pods from the eligible Pods).
            - value (str): The value for the mode configuration, depending on mode. For example, when mode is set to fixed-percent, value specifies the percentage of Pods.

    Returns:
        dict: The applied experiment's resource in Kubernetes.
    """
    # 验证服务是否存在
    try:
        # 检查指定命名空间中是否有匹配的pods
        v1 = k8s_client.CoreV1Api()
        pods = v1.list_namespaced_pod(
            namespace=namespace,
            label_selector=f"app={service}"
        )
        
        if not pods.items:
            # 尝试其他常见的标签选择器
            alternative_selectors = [
                f"app.kubernetes.io/name={service}",
                f"k8s-app={service}"
            ]
            
            for selector in alternative_selectors:
                pods = v1.list_namespaced_pod(
                    namespace=namespace,
                    label_selector=selector
                )
                if pods.items:
                    break
            
            if not pods.items:
                return {
                    "error": f"No pods found for service '{service}' in namespace '{namespace}'. Please check service name and namespace."
                }
        
        logger.info(f"Found {len(pods.items)} pods for service '{service}' in namespace '{namespace}'")
        
    except Exception as e:
        logger.warning(f"Could not verify service existence: {e}")
    
    # 将namespace添加到kwargs中
    kwargs['namespace'] = namespace
    
    return _pod_fault_inject(
        service=service,
        type=type,
        **kwargs,
    )


def pod_stress_test(service: str, type: str, container_names: list[str], namespace: str = "default", **kwargs) -> dict:
    """
    Simulate a stress test on a pod
    Args:
        service (str): The name of the service to inject the fault into, e.g., "adservice".
        type (str): The type of fault to inject, one of "POD_STRESS_CPU", "POD_STRESS_MEMORY".
            - POD_STRESS_CPU: Simulate a CPU stress test.
            - POD_STRESS_MEMORY: Simulate a memory stress test.
        container_names (list[str]): The names of the containers to inject the fault into.
        namespace (str): The namespace where the service is located. Default is "default".
        kwargs: Additional arguments for the experiment.
            - duration (str): The duration of the experiment, e.g., "5m" for 5 minutes.
            - mode (str): The mode of the experiment, The mode options include one (selecting a random Pod), all (selecting all eligible Pods), fixed (selecting a specified number of eligible Pods), fixed-percent (selecting a specified percentage of Pods from the eligible Pods), and random-max-percent (selecting the maximum percentage of Pods from the eligible Pods).
            - value (str): The value for the mode configuration, depending on mode. For example, when mode is set to fixed-percent, value specifies the percentage of Pods.
            - workers (int): The number of workers for the stress test.
            - load (int): The percentage of CPU occupied. 0 means that no additional CPU is added, and 100 refers to full load. The final sum of CPU load is workers * load.
            - size (str): The memory size to be occupied or a percentage of the total memory size. The final sum of the occupied memory size is size. e.g., "256MB", "50%".
            - time (str): The time to reach the memory size. The growth model is a linear model. e.g., "10min".
    Returns:
        dict: The applied experiment's resource in Kubernetes.
    """
    # 将namespace添加到kwargs中
    kwargs['namespace'] = namespace
    
    return _pod_fault_inject(
        service=service,
        type=type,
        container_names=container_names,
        **kwargs,
    )


def host_stress_test(type: str, address: list[str], **kwargs) -> dict:
    """
    Simulate a stress test on a host
    Args:
        type (str): The type of fault to inject, one of "HOST_STRESS_CPU", "HOST_STRESS_MEMORY".
            - HOST_STRESS_CPU: Simulate a CPU stress test.
            - HOST_STRESS_MEMORY: Simulate a memory stress test.
        address (list[str]): The addresses of the hosts to inject the fault into.
        kwargs: Additional arguments for the experiment.
            - duration (str): The duration of the experiment, e.g., "5m" for 5 minutes.
            - workers (int): The number of workers for the stress test.
            - load (int): The percentage of CPU occupied. 0 means that no additional CPU is added, and 100 refers to full load. The final sum of CPU load is workers * load.
            - size (str): The memory size to be occupied or a percentage of the total memory size. The final sum of the occupied memory size is size. e.g., "256MB", "50%".
            - time (str): The time to reach the memory size. The growth model is a linear model. e.g., "10min".
    Returns:
        dict: The applied experiment's resource in Kubernetes.
    """
    return _fault_inject(
        type=type,
        address=address,
        **kwargs,
    )


def host_disk_fault(type: str, address: list[str], size: str, path: str, **kwargs) -> dict:
    """
    Simulate a disk fault on a host
    Args:
        type (str): The type of fault to inject, one of "HOST_FILL", "HOST_READ_PAYLOAD", "HOST_WRITE_PAYLOAD".
            - HOST_FILL: Simulate a disk fill.
            - HOST_READ_PAYLOAD: Simulate a disk read payload.
            - HOST_WRITE_PAYLOAD: Simulate a disk write payload.
        address (list[str]): The addresses of the hosts to inject the fault into.
        size (str): The size of the payload, e.g., "1024K".
        path (str): The path to the file to be read or written.
        kwargs: Additional arguments for the experiment.
            - payload_process_num (int): The number of processes to read or write the payload.
            - fill_by_fallocate (bool): Whether to fill the disk by fallocate.
            - duration (str): The duration of the experiment, e.g., "5m" for 5 minutes.
    Returns:
        dict: The applied experiment's resource in Kubernetes.
    """
    return _fault_inject(
        type=type,
        address=address,
        size=size,
        path=path,
        **kwargs
    )


def network_fault(service: str, type: str, namespace: str = "default", **kwargs) -> dict:
    """
    Simulate a network fault on a pod
    Args:
        service (str): The name of the service to inject the fault into, e.g., "adservice".
        type (str): The type of fault to inject, one of "NETWORK_PARTITION", "NETWORK_BANDWIDTH".
            - NETWORK_PARTITION: Simulate a network partition.
            - NETWORK_BANDWIDTH: Simulate a network bandwidth limitation.
        namespace (str): The namespace where the service is located. Default is "default".
        kwargs: Additional arguments for the experiment.
            - mode (str): The mode of the experiment, The mode options include one (selecting a random Pod), all (selecting all eligible Pods), fixed (selecting a specified number of eligible Pods), fixed-percent (selecting a specified percentage of Pods from the eligible Pods), and random-max-percent (selecting the maximum percentage of Pods from the eligible Pods).
            - value (str): The value for the mode configuration, depending on mode. For example, when mode is set to fixed-percent, value specifies the percentage of Pods.
            - direction (str): The direction of target packets. Available values include from (the packets from target), to (the packets to target), and both ( the packets from or to target). This parameter makes Chaos only take effect for a specific direction of packets.
            - external_targets (list[str]): The network targets except for Kubernetes, which can be IPv4 addresses or domains or service name. e,.g., ["www.example.com", "1.1.1.1", "checkoutservice].
            - device (str): The affected network interface. e.g., "eth0".
            - rate (str): The bandwidth limit. Allows bit, kbit, mbit, gbit, tbit, bps, kbps, mbps, gbps, tbps unit. bps means bytes per second. e.g., "1mbps".
            - limit (int): The number of bytes waiting in queue.
            - buffer (int): The maximum number of bytes that can be sent instantaneously.
            - duration (str): The duration of the experiment, e.g., "5m" for 5 minutes.
    Returns:
        dict: The applied experiment's resource in Kubernetes.
    """
    # 将namespace添加到kwargs中
    kwargs['namespace'] = namespace
    
    return _pod_fault_inject(service=service, type=type, **kwargs)


def delete_experiment(type: str, name: str, namespace: str = "default") -> dict:
    """
    Delete a fault injection experiment
    Args:
        type (str): The type of fault to delete.
        name (str): The name of the experiment to delete.
        namespace (str): The namespace where the experiment is located. Default is "default".
    Returns:
        dict: The result of the deletion.
    """
    try:
        experiment_type = Experiment[type]
    except KeyError:
        return {
            "error": f"Invalid experiment type: {type}. Valid types are: {list(Experiment.__dict__.keys())}"
        }

    logger.info(f'Deleting experiment of type: {type} with name: {name} in namespace: {namespace}')

    return client.delete_experiment(
        experiment_type=experiment_type,
        namespace=namespace,
        name=name,
    )


def _pod_fault_inject(service: str, type: str, namespace: str = "default", **kwargs) -> dict:
    selector = Selector(
        labelSelectors={"app": service}, 
        pods=None, 
        namespaces=[namespace]
    )
    kwargs['selector'] = selector

    return _fault_inject(
        type=type,
        namespace=namespace,
        **kwargs,
    )


def _fault_inject(type: str, namespace: str = "default", **kwargs) -> dict:
    """
    改进的故障注入函数，包含重试机制和更好的错误处理
    """
    if client is None:
        return {
            "error": "Chaos Mesh client not initialized. Please check Chaos Mesh installation."
        }
    
    logger.info(f'Starting fault injection of type: {type} in namespace: {namespace}')
    logger.info(f'Additional arguments: {kwargs}')

    try:
        experiment_type = Experiment[type]
    except KeyError:
        available_types = [attr for attr in dir(Experiment) if not attr.startswith('_')]
        return {
            "error": f"Invalid experiment type: {type}. Valid types are: {available_types}"
        }

    # 生成唯一的实验名称，确保符合Kubernetes命名规范
    # 将下划线替换为连字符，确保名称符合RFC 1123规范
    experiment_name = f"{type.lower().replace('_', '-')}-{str(uuid.uuid4())[:8]}"
    
    # 添加重试机制
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempt {attempt + 1}/{max_retries} to start experiment in namespace: {namespace}")
            
            r = client.start_experiment(
                experiment_type=experiment_type,
                namespace=namespace,
                name=experiment_name,
                **kwargs,
            )

            logger.info(f'Experiment started successfully: {experiment_name} in namespace: {namespace}')
            return r

        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 指数退避
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"All {max_retries} attempts failed")
                return {
                    "error": f"Failed to start experiment after {max_retries} attempts: {str(e)}",
                    "experiment_name": experiment_name,
                    "namespace": namespace,
                    "type": type
                }
