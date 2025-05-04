import psutil
import json
import platform
from datetime import datetime

def get_system_data():
    """Sammelt eine Vielzahl von Systemstatistiken, geeignet für Monitoring und Live-Streaming."""
    data = {}

    data["timestamp"] = datetime.now().timestamp()

    ## Systeminformationen
    data["system_info"] = {
        "system": platform.system(),
        "node": platform.node(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor()
    }

    ## Systemzeit / Boot
    data["boot_time"] = datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")

    # CPU
    data["cpu"] = {
        "percent": psutil.cpu_percent(interval=0),
        "percent_per_core": psutil.cpu_percent(interval=0, percpu=True),
        "count_logical": psutil.cpu_count(logical=True),
        "count_physical": psutil.cpu_count(logical=False),
        "freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
        "times": psutil.cpu_times()._asdict(),
        "stats": psutil.cpu_stats()._asdict(),
        "load_avg": psutil.getloadavg() if hasattr(psutil, "getloadavg") else None,
    }

    ## RAM
    virtual_mem = psutil.virtual_memory()
    data["memory"] = virtual_mem._asdict()

    ## Swap
    swap = psutil.swap_memory()
    data["swap"] = swap._asdict()

    ## Disk
    data["disk"] = {
        "usage": psutil.disk_usage("/")._asdict(),
        "io": psutil.disk_io_counters()._asdict(),
        "partitions": [
            {
                "device": p.device,
                "mountpoint": p.mountpoint,
                "fstype": p.fstype,
                "opts": p.opts,
            } for p in psutil.disk_partitions()
        ]
    }

    ## Netzwerk
    # net_io = psutil.net_io_counters(pernic=True)
    # data["network_io"] = {
    #     iface: counters._asdict() for iface, counters in net_io.items()
    # }

    ## Netzverbindungen
    try:
        connections = psutil.net_connections()
        data["network_connections"] = [
            {
                "fd": c.fd,
                "family": str(c.family),
                "type": str(c.type),
                "laddr": f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else None,
                "raddr": f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else None,
                "status": c.status,
                "pid": c.pid,
            } for c in connections[:20]  # nur die ersten 20, um es übersichtlich zu halten
        ]
    except Exception:
        data["network_connections"] = []

    ## Prozesse (nur die wichtigsten Infos)
    # data["processes"] = []
    # for proc in psutil.process_iter(['pid', 'name', 'status', 'cpu_percent', 'memory_percent']):
    #     try:
    #         data["processes"].append(proc.info)
    #     except (psutil.NoSuchProcess, psutil.AccessDenied):
    #         continue

    ## Benutzer
    # data["users"] = [u._asdict() for u in psutil.users()]

    ## Temperaturen (nur wenn unterstützt)
    try:
        temps = psutil.sensors_temperatures()
        data["temperatures"] = {k: [t._asdict() for t in v] for k, v in temps.items()}
    except Exception:
        data["temperatures"] = {}

    ## Lüfter (nur wenn unterstützt)
    # try:
    #     fans = psutil.sensors_fans()
    #     data["fans"] = {k: [f._asdict() for f in v] for k, v in fans.items()}
    # except Exception:
    #     data["fans"] = {}

    return data

# Beispiel für schöne Ausgabe
if __name__ == "__main__":
    print(json.dumps(get_system_data(), indent=4))
