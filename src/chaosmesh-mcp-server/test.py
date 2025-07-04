import json
from time import sleep
import logging
import sys
from fault_inject import *
from fault_inject import client
from chaosmesh.client import Experiment
from kube import get_service_pod_logs

logger = logging.getLogger("chaosmesh")
logger.setLevel(logging.DEBUG)


def test(type: str, func: callable, **args) -> None:
    r = func(type=type, **args)
    print(r)

    sleep(10)

    r = client.delete_experiment(
        experiment_type=Experiment[type], namespace="default", name=r["metadata"]["name"])
    print(r)


def test_kube(service_name: str, namespace: str, container_name: str, type: str = "all", tail_lines: int = 20):
    pod_logs = get_service_pod_logs(
        service_name=service_name, namespace=namespace, container_name=container_name, type=type, tail_lines=tail_lines)
    for pod_name, log in pod_logs.items():
        print(f"Logs for pod '{pod_name}':")
        print(log)
        print("\n")


if __name__ == "__main__":
    test("POD_FAILURE", pod_fault, service="checkoutservice", kwargs='{\
         "duration": "30s", "mode": "one"}')
    test("POD_KILL", pod_fault, service="checkoutservice", kwargs='{\
         "duration": "30s", "mode": "one"}')
    test("CONTAINER_KILL", pod_fault, service="checkoutservice", kwargs='{\
        "container_names": ["server"]}')
    test("POD_STRESS_CPU", pod_stress_test, service="checkoutservice", kwargs='{\
        "duration": "30s",  "workers": 1, "load": 90}', container_names=["server"])
    test("POD_STRESS_MEMORY", pod_stress_test, service="checkoutservice", kwargs='{\
        "duration": "30s", "workers": 1, "size": "256MB", "time": "10s"}', container_names=["server"], )
    test("HOST_STRESS_CPU", host_stress_test, kwargs='{\
        "duration": "30s", "workers": 1, "load": 90}', address=["192.168.49.2"])
    test("HOST_STRESS_MEMORY", host_stress_test, kwargs='{\
        "duration": "30s", "workers": 1, "size": "256MB", "time": "10s"}', address=["192.168.49.2"])
    test("NETWORK_PARTITION", network_fault, service="checkoutservice", kwargs='{\
        "direction": "both", "external_targets": ["cartservice"], "duration": "30s"}')
    test("NETWORK_BANDWIDTH", network_fault, service="checkoutservice", kwargs='{\
         "direction": "to", "external_targets": ["cartservice"], "rate": "1mbps", "limit": 1024, "buffer": 1024}')
    test_kube("checkoutservice", "default",
              "server", type="one", tail_lines=20)
    test_kube("loadgenerator", "default",
              "main", type="one", tail_lines=20)
