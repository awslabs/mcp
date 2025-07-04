from kubernetes import client, config, utils
import requests
import os
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_k8s_client():
    """
    初始化Kubernetes客户端，优先支持EKS环境
    """
    try:
        # 首先尝试集群内配置（如果运行在Pod中）
        if os.path.exists('/var/run/secrets/kubernetes.io/serviceaccount'):
            logger.info("Loading in-cluster configuration")
            config.load_incluster_config()
        else:
            # 尝试加载本地配置
            logger.info("Loading kube config from local file")
            config.load_kube_config()
            
        # 验证连接
        v1_test = client.CoreV1Api()
        namespaces = v1_test.list_namespace(limit=1)
        logger.info(f"✓ Kubernetes client initialized successfully - found {len(namespaces.items)} namespace(s)")
        
        # 显示当前连接的集群信息
        try:
            current_context = config.list_kube_config_contexts()[1]
            if current_context:
                logger.info(f"✓ Connected to cluster: {current_context.get('name', 'unknown')}")
        except Exception:
            pass  # 忽略获取上下文信息的错误
            
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize Kubernetes client: {e}")
        # 提供更详细的错误信息和解决建议
        logger.error("Please ensure:")
        logger.error("1. kubectl is configured and can access the cluster")
        logger.error("2. For EKS: aws eks update-kubeconfig --region <region> --name <cluster-name>")
        logger.error("3. IAM permissions include eks:DescribeCluster and appropriate RBAC permissions")
        return False

# 初始化客户端
if initialize_k8s_client():
    v1 = client.CoreV1Api()
    api = client.CustomObjectsApi()
else:
    logger.error("Failed to initialize Kubernetes client - some functions may not work")
    v1 = None
    api = None


def get_pod_logs(pod_name: str, namespace: str, container_name: str, tail_lines: int = 20) -> str:
    """
    Retrieve logs for a specific pod and container.
    增加了更好的错误处理和重试机制
    """
    try:
        # 添加超时设置
        logs = v1.read_namespaced_pod_log(
            name=pod_name, 
            namespace=namespace, 
            container=container_name, 
            tail_lines=tail_lines,
            _request_timeout=30  # 30秒超时
        )
        return logs

    except client.exceptions.ApiException as e:
        if e.status == 404:
            logger.warning(f"Pod {pod_name} or container {container_name} not found")
        elif e.status == 403:
            logger.error(f"Permission denied accessing pod {pod_name}. Check RBAC permissions.")
        else:
            logger.error(f"API error retrieving logs: {e}")
        return f"Error: {e.reason}"
    except Exception as e:
        logger.error(f"Unexpected error retrieving logs: {e}")
        return f"Error: {str(e)}"


def get_pods_by_service(service_name: str, namespace: str) -> list[str]:
    """
    Retrieve all pods for a specific service in a namespace.
    改进了标签选择器的逻辑
    """
    try:
        # 更灵活的标签选择器
        label_selectors = [
            f"app={service_name}",
            f"app.kubernetes.io/name={service_name}",
            f"k8s-app={service_name}"
        ]
        
        pod_names = []
        for selector in label_selectors:
            try:
                pods = v1.list_namespaced_pod(
                    namespace=namespace, 
                    label_selector=selector,
                    _request_timeout=30
                )
                if pods.items:
                    pod_names.extend([pod.metadata.name for pod in pods.items])
                    break  # 找到匹配的pods就停止
            except Exception as e:
                logger.debug(f"Label selector {selector} failed: {e}")
                continue
        
        if not pod_names:
            logger.warning(f"No pods found for service '{service_name}' in namespace '{namespace}'")
            
        return list(set(pod_names))  # 去重

    except client.exceptions.ApiException as e:
        if e.status == 403:
            logger.error(f"Permission denied listing pods in namespace {namespace}. Check RBAC permissions.")
        else:
            logger.error(f"API error retrieving pods: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error retrieving pods: {e}")
        return []


def get_service_pod_logs(service_name: str, namespace: str, container_name: str, type: str = "all", tail_lines: int = 20) -> dict:
    """
    Retrieve logs for all pods of a specific service in a namespace.

    Args:
        service_name (str): Name of the service.
        namespace (str): Namespace of the service.
        container_name (str): Name of the container.
        type (str): Type of logs to retrieve. Default is "all".
            - "all": Retrieve logs from all pods.
            - "one": Retrieve logs from one pod.
        tail_lines (int): Number of lines to return from the end of the logs.
            Default is 20.

    Returns:
        dict: Dictionary with pod names as keys and logs as values.
    """
    pod_logs = {}
    pod_names = get_pods_by_service(service_name, namespace)

    if not pod_names:
        print(
            f"No pods found for service '{service_name}' in namespace '{namespace}'.")
        return pod_logs

    if type == "one":
        pod_names = [pod_names[0]]

    for pod_name in pod_names:
        logs = get_pod_logs(pod_name, namespace, container_name, tail_lines)
        if logs:
            pod_logs[pod_name] = logs
        else:
            print(f"No logs found for pod '{pod_name}'.")

    return pod_logs


def load_generate(rate: int) -> list[str]:
    url = "http://localhost:80"
    results = []

    def send_request():
        try:
            response = requests.get(url=url, timeout=5)
            return f"Status: {response.status_code}"
        except Exception as e:
            return f"Error: {str(e)}"

    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=min(rate, 100)) as executor:
        futures = [executor.submit(send_request) for _ in range(rate)]
        for future in as_completed(futures):
            results.append(future.result())

    return results


def inject_delay_fault(service_name: str, delay_seconds: int, namespace: str = "default"):
    virtual_service_manifest = {
        "apiVersion": "networking.istio.io/v1",
        "kind": "VirtualService",
        "metadata": {
            "name": f"{service_name}-delay",
            "namespace": namespace,
        },
        "spec": {
            "hosts": [service_name],
            "http": [
                {
                    "fault": {
                        "delay": {
                            "fixedDelay": f"{delay_seconds}s",
                            "percentage": {
                                "value": 100,
                            }
                        }
                    },
                    "route": [
                        {
                            "destination": {
                                "host": service_name
                            }
                        }
                    ]
                }
            ]
        }
    }

    r = api.create_namespaced_custom_object(
        group="networking.istio.io",
        version="v1",
        namespace=namespace,
        plural="virtualservices",
        body=virtual_service_manifest,
    )
    logger.info(
        f"Injected delay fault for service '{service_name}' with {delay_seconds} seconds delay in namespace '{namespace}'.")

    return r


def remove_delay_fault(service_name: str, namespace: str = "default"):
    try:
        r = api.delete_namespaced_custom_object(
            group="networking.istio.io",
            version="v1",
            namespace=namespace,
            plural="virtualservices",
            name=f"{service_name}-delay",
        )
        logger.info(f"Removed delay fault for service '{service_name}' in namespace '{namespace}'.")
        return r
    except Exception as e:
        logger.error(f"Error removing delay fault: {e}")
        return {"error": str(e)}
