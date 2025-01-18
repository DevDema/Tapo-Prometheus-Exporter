from contextlib import contextmanager
from enum import Enum, auto
from math import floor
from time import time
from time import sleep

from loguru import logger
from prometheus_client import Histogram
from prometheus_client.core import GaugeMetricFamily
from PyP100 import PyP110


OBSERVATION_RED_METRICS = Histogram(
    "tapo_observation_rate_ms",
    "RED metrics for queries to the TP-Link TAPO devices. (milliseconds)",
    labelnames=["ip_address", "room", "success"],
    buckets=(10, 100, 150, 200, 250, 300, 500, 750, 1000, 1500, 2000)
)

class MetricType(Enum):
    DEVICE_COUNT = auto()
    TODAY_RUNTIME = auto()
    MONTH_RUNTIME = auto()
    TODAY_ENERGY = auto()
    MONTH_ENERGY = auto()
    CURRENT_POWER = auto()


def get_absolute_metrics():
    return {
        MetricType.DEVICE_COUNT: GaugeMetricFamily(
            "tapo_device_count",
            "Number of available TP-Link TAPO Smart Sockets.",
        )
    }

def get_metrics(model):
    model_name = model.lower()
    prefix = "tapo_" + model_name + "_"
    return {
        MetricType.TODAY_RUNTIME: GaugeMetricFamily(
            prefix + "today_runtime_mins",
            "Current running time for the TP-Link TAPO " + model + " Smart Socket today. (minutes)",
            labels=["ip_address", "room", "model"],
        ),
        MetricType.MONTH_RUNTIME: GaugeMetricFamily(
            prefix + "month_runtime_mins",
            "Current running time for the TP-Link TAPO " + model + " Smart Socket this month. (minutes)",
            labels=["ip_address", "room", "model"],
        ),
        MetricType.TODAY_ENERGY: GaugeMetricFamily(
            prefix + "today_energy_wh",
            "Energy consumed by the TP-Link TAPO " + model + " Smart Socket today. (Watt-hours)",
            labels=["ip_address", "room", "model"],
        ),
        MetricType.MONTH_ENERGY: GaugeMetricFamily(
            prefix + "month_energy_wh",
            "Energy consumed by the TP-Link TAPO " + model + " Smart Socket this month. (Watt-hours)",
            labels=["ip_address", "room", "model"],
        ),
        MetricType.CURRENT_POWER: GaugeMetricFamily(
            prefix + "power_consumption_w",
            "Current power consumption for TP-Link TAPO " + model + " Smart Socket. (Watts)",
            labels=["ip_address", "room", "model"],
        ),
    }


RED_SUCCESS = "SUCCESS"
RED_FAILURE = "FAILURE"

@contextmanager
def time_observation(ip_address, room, model):
    caught = None
    status = RED_SUCCESS
    start = time()

    try:
        yield
    except Exception as e:
        status = RED_FAILURE
        caught = e
    
    duration = floor((time() - start) * 1000)
    OBSERVATION_RED_METRICS.labels(ip_address=ip_address, room=room, success=status).observe(duration)

    logger.debug("observation completed", extra={
        "ip": ip_address, "room": room, "duration_ms": duration,
    })

    if caught:
        raise caught


class Collector:
    def __init__(self, deviceMap, email_address, password):
        def create_device(ip_address, room, model):
            extra = {
                "ip": ip_address,
                "room": room,
                "model": model
            }
            logger.debug("connecting to device", extra=extra)
            
            exception_count = 0  # Counter for exceptions
            
            while True:
                try:
                    d = PyP110.P110(ip_address, email_address, password)
                    d.handshake()
                    d.login()
                except Exception as e:
                    exception_count += 1
                    logger.error("failed to connect to device", extra=extra, exc_info=True)
                    if exception_count >= 3:  # Return None after the third exception
                        d = None
                        break
                    sleep(1)  # Sleep for 1 second after each exception
                    continue
                break

            if d is not None:
                logger.debug("successfully authenticated with device", extra=extra)
            
            return d

        self.devices = {
            room: (device_info['ip_address'], device, device_info['model'])
            for room, device_info in deviceMap.items()
            if (device := create_device(device_info['ip_address'], room, device_info['model'])) is not None
        }

    def get_device_data(self, device, ip_address, room, model):
        with time_observation(ip_address, room, model):
            logger.debug("retrieving energy usage statistics for device", extra={
                "ip": ip_address, "room": room,
            })
            return device.getEnergyUsage()

    def collect(self):
        logger.info("receiving prometheus metrics scrape: collecting observations")

        metrics = get_absolute_metrics()
        metrics[MetricType.DEVICE_COUNT].add_metric([], len(self.devices))

        for room, (ip_addr, device, model) in self.devices.items():
            new_metrics = get_metrics(model)

            for metric_type, new_metric in new_metrics.items():
                metrics[metric_type] = new_metric

            logger.info("performing observations for device", extra={
                "ip": ip_addr, "room": room, "model": model
            })

            try:
                data = self.get_device_data(device, ip_addr, room, model)

                labels = [ip_addr, room, model]
                metrics[MetricType.TODAY_RUNTIME].add_metric(labels, data['today_runtime'])
                metrics[MetricType.MONTH_RUNTIME].add_metric(labels, data['month_runtime'])
                metrics[MetricType.TODAY_ENERGY].add_metric(labels, data['today_energy'])
                metrics[MetricType.MONTH_ENERGY].add_metric(labels, data['month_energy'])
                metrics[MetricType.CURRENT_POWER].add_metric(labels, data['current_power'])
            except Exception as e:
                logger.exception("encountered exception during observation!")

        for m in metrics.values():
            yield m        

            