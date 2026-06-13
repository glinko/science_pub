from __future__ import annotations

import base64
import json
import os
import random
import ssl
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IMAGE_PATH = "/var/lib/vz/template/iso/ubuntu-24.04-server-cloudimg-amd64.img"
DEFAULT_NODE = "pve"
DEFAULT_STORAGE = "SSD240G"
DEFAULT_BRIDGE = "vmbr0"
DEFAULT_VM_NAME = "sci-docker"
DEFAULT_VMID = "103"
DEFAULT_SSH_USER = "alex"
DEFAULT_IP_RANGE = range(150, 200)


@dataclass(slots=True)
class ProvisionResult:
    vmid: str
    mac_address: str
    reserved_ip: str


class JsonHttpClient:
    def __init__(self, base_url: str, *, verify_tls: bool = True, headers: dict[str, str] | None = None):
        self.base_url = base_url.rstrip("/")
        self.context = None if verify_tls else ssl._create_unverified_context()
        self.headers = headers or {}

    def request(self, method: str, path: str, payload: dict | None = None):
        body = None
        headers = dict(self.headers)
        if payload is not None:
            if self.base_url.endswith("/rest") and method.upper() in {"POST", "PUT", "PATCH"}:
                body = json.dumps(payload).encode("utf-8")
                headers["Content-Type"] = "application/json"
            else:
                encoded = urllib.parse.urlencode(payload, doseq=True, quote_via=urllib.parse.quote)
                body = encoded.encode("utf-8")
                headers["Content-Type"] = "application/x-www-form-urlencoded"
        request = urllib.request.Request(f"{self.base_url}{path}", data=body, headers=headers, method=method)
        with urllib.request.urlopen(request, context=self.context, timeout=30) as response:
            content = response.read().decode("utf-8")
        if not content:
            return None
        return json.loads(content)


def read_public_key() -> str:
    for candidate in [
        Path.home() / ".ssh" / "id_ed25519.pub",
        Path.home() / ".ssh" / "id_rsa.pub",
    ]:
        if candidate.exists():
            return candidate.read_text(encoding="utf-8").strip()
    raise FileNotFoundError("No SSH public key found in ~/.ssh")


def generate_mac_address() -> str:
    octets = [0x52, 0x54, 0x00, random.randint(0x00, 0x7F), random.randint(0x00, 0xFF), random.randint(0x00, 0xFF)]
    return ":".join(f"{octet:02X}" for octet in octets)


def get_proxmox_client() -> JsonHttpClient:
    token_id = os.environ["PVE_TOKEN_ID"]
    token_secret = os.environ["PVE_TOKEN_SECRET"]
    base_url = os.environ.get("PVE_API_URL", "https://192.168.88.10:8006/api2/json")
    return JsonHttpClient(
        base_url,
        verify_tls=False,
        headers={"Authorization": f"PVEAPIToken={token_id}={token_secret}"},
    )


def get_mikrotik_client() -> JsonHttpClient:
    base_url = os.environ.get("MIKROTIK_REST_URL", "http://192.168.88.1/rest")
    user = os.environ["MIKROTIK_USER"]
    password = os.environ["MIKROTIK_PASSWORD"]
    creds = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("utf-8")
    return JsonHttpClient(base_url, headers={"Authorization": f"Basic {creds}"})


def choose_ip(mikrotik: JsonHttpClient) -> str:
    leases = mikrotik.request("GET", "/ip/dhcp-server/lease") or []
    used = {item["address"] for item in leases if item.get("address")}
    for suffix in DEFAULT_IP_RANGE:
        candidate = f"192.168.88.{suffix}"
        if candidate not in used:
            return candidate
    raise RuntimeError("No free IP found in 192.168.88.150-199")


def wait_for_proxmox_task(proxmox: JsonHttpClient, node: str, upid: str, *, timeout_seconds: int = 300) -> None:
    started_at = time.time()
    encoded_upid = urllib.parse.quote(upid, safe="")
    while time.time() - started_at < timeout_seconds:
        status = proxmox.request("GET", f"/nodes/{node}/tasks/{encoded_upid}/status")["data"]
        if status.get("status") == "stopped":
            if status.get("exitstatus") != "OK":
                raise RuntimeError(f"Proxmox task failed: {status}")
            return
        time.sleep(3)
    raise TimeoutError(f"Task {upid} did not finish in time")


def ensure_vm_absent_or_stopped(proxmox: JsonHttpClient, node: str, vmid: str) -> None:
    vms = proxmox.request("GET", f"/nodes/{node}/qemu")["data"]
    for vm in vms:
        if str(vm["vmid"]) == vmid and vm.get("status") == "running":
            raise RuntimeError(f"VM {vmid} already exists and is running")


def reserve_dhcp_lease(mikrotik: JsonHttpClient, ip_address: str, mac_address: str) -> str:
    payload = {
        "address": ip_address,
        "mac-address": mac_address,
        "comment": "Инфра / Science Pub / sci_docker",
    }
    result = mikrotik.request("PUT", "/ip/dhcp-server/lease", payload)
    return result[".id"]


def release_dhcp_lease(mikrotik: JsonHttpClient, lease_id: str) -> None:
    mikrotik.request("POST", "/ip/dhcp-server/lease/remove", {".id": lease_id})


def create_vm(proxmox: JsonHttpClient, *, vmid: str, mac_address: str, ssh_key: str) -> None:
    payload = {
        "vmid": vmid,
        "name": DEFAULT_VM_NAME,
        "agent": "1",
        "cores": "4",
        "memory": "8192",
        "sockets": "1",
        "cpu": "host",
        "ostype": "l26",
        "scsihw": "virtio-scsi-single",
        "ide2": "local-lvm:cloudinit",
        "scsi0": f"{DEFAULT_STORAGE}:0,import-from={DEFAULT_IMAGE_PATH}",
        "boot": "order=scsi0",
        "serial0": "socket",
        "vga": "serial0",
        "net0": f"virtio={mac_address},bridge={DEFAULT_BRIDGE}",
        "ciuser": DEFAULT_SSH_USER,
        "ipconfig0": "ip=dhcp",
        "sshkeys": urllib.parse.quote(ssh_key, safe=""),
        "tags": "science-pub",
        "description": "Science Pub milestone 1 host",
    }
    create_result = proxmox.request("POST", f"/nodes/{DEFAULT_NODE}/qemu", payload)
    wait_for_proxmox_task(proxmox, DEFAULT_NODE, create_result["data"])
    resize_result = proxmox.request(
        "PUT",
        f"/nodes/{DEFAULT_NODE}/qemu/{vmid}/resize",
        {"disk": "scsi0", "size": "60G"},
    )
    wait_for_proxmox_task(proxmox, DEFAULT_NODE, resize_result["data"])
    start_result = proxmox.request("POST", f"/nodes/{DEFAULT_NODE}/qemu/{vmid}/status/start")
    wait_for_proxmox_task(proxmox, DEFAULT_NODE, start_result["data"])


def clone_vm(proxmox: JsonHttpClient, *, source_vmid: str, vmid: str, mac_address: str, ssh_key: str) -> None:
    clone_result = proxmox.request(
        "POST",
        f"/nodes/{DEFAULT_NODE}/qemu/{source_vmid}/clone",
        {
            "newid": vmid,
            "name": DEFAULT_VM_NAME,
            "full": "1",
            "storage": DEFAULT_STORAGE,
            "target": DEFAULT_NODE,
        },
    )
    wait_for_proxmox_task(proxmox, DEFAULT_NODE, clone_result["data"], timeout_seconds=900)
    proxmox.request(
        "PUT",
        f"/nodes/{DEFAULT_NODE}/qemu/{vmid}/config",
        {
            "agent": "1",
            "cores": "4",
            "memory": "8192",
            "sockets": "1",
            "cpu": "host",
            "net0": f"virtio={mac_address},bridge={DEFAULT_BRIDGE}",
            "ciuser": DEFAULT_SSH_USER,
            "ipconfig0": "ip=dhcp",
            "sshkeys": urllib.parse.quote(ssh_key, safe=""),
            "tags": "science-pub",
            "description": "Science Pub milestone 1 host (clone fallback)",
        },
    )
    resize_result = proxmox.request(
        "PUT",
        f"/nodes/{DEFAULT_NODE}/qemu/{vmid}/resize",
        {"disk": "scsi0", "size": "+10G"},
    )
    wait_for_proxmox_task(proxmox, DEFAULT_NODE, resize_result["data"])
    start_result = proxmox.request("POST", f"/nodes/{DEFAULT_NODE}/qemu/{vmid}/status/start")
    wait_for_proxmox_task(proxmox, DEFAULT_NODE, start_result["data"])


def main() -> None:
    ssh_key = read_public_key()
    proxmox = get_proxmox_client()
    mikrotik = get_mikrotik_client()
    vmid = os.environ.get("SCIENCE_PUB_VMID", DEFAULT_VMID)
    mac_address = os.environ.get("SCIENCE_PUB_VM_MAC", generate_mac_address())
    reserved_ip = choose_ip(mikrotik)
    ensure_vm_absent_or_stopped(proxmox, DEFAULT_NODE, vmid)
    lease_id = reserve_dhcp_lease(mikrotik, reserved_ip, mac_address)
    try:
        clone_source_vmid = os.environ.get("SCIENCE_PUB_CLONE_SOURCE_VMID")
        if clone_source_vmid:
            clone_vm(
                proxmox,
                source_vmid=clone_source_vmid,
                vmid=vmid,
                mac_address=mac_address,
                ssh_key=ssh_key,
            )
        else:
            create_vm(proxmox, vmid=vmid, mac_address=mac_address, ssh_key=ssh_key)
    except Exception:
        release_dhcp_lease(mikrotik, lease_id)
        raise
    time.sleep(10)
    print(json.dumps(ProvisionResult(vmid=vmid, mac_address=mac_address, reserved_ip=reserved_ip).__dict__))


if __name__ == "__main__":
    main()
