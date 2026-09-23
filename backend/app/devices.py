"""影像来源设备(imaging source devices)管理。

提供设备列表/详情/重新拉取检查的 REST 接口，以及一个 /ws/devices
WebSocket 通道：设备状态(在检/空闲/离线)发生变更时立即推送给所有
已连接的前端，使设备列表与详情弹窗保持同步。

状态全部保存在内存中，由后台协程模拟设备的状态流转。
"""
import asyncio
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

router = APIRouter(prefix="/api/devices", tags=["devices"])
# WebSocket 单独挂在 /ws 下，前端开发服务器仅对 /ws 开启协议升级代理
ws_router = APIRouter(tags=["devices"])

# 设备状态
SCANNING = "scanning"  # 在检
IDLE = "idle"          # 空闲
OFFLINE = "offline"    # 离线

ALL_STATUSES = (SCANNING, IDLE, OFFLINE)

# 每个设备的状态流转周期(秒)与下一次变更的随机时刻
_TICK_INTERVAL = 2.0
_NEXT_TICK_RANGE = (6, 18)

# 重新拉取时各模态下可能出现的检查描述
_STUDY_TITLES = {
    "CT": ["胸部CT平扫", "头部CT平扫", "腹部增强CT", "CTA血管成像", "胸部高分辨CT"],
    "MR": ["头颅MRI", "腰椎MRI平扫", "腹部MRI增强", "膝关节MRI", "颈椎MRI"],
    "DR": ["胸部正位片", "四肢X线片", "腹部立位片"],
}

RECENT_STUDY_LIMIT = 5


def _iso(dt: datetime) -> str:
    """统一以带时区的 ISO8601 字符串返回时间。"""
    return dt.astimezone(timezone.utc).isoformat()


def _make_study(device_id: str, seq: int, modality: str, at: datetime) -> Dict:
    titles = _STUDY_TITLES.get(modality, _STUDY_TITLES["CT"])
    # 仅 CT 可走现有体渲染查看流程；按设备给出对应的体渲染预设
    ct_presets = {"CT-01": "chest", "CT-03": "abdomen"}
    preset = ct_presets.get(device_id, "brain") if modality == "CT" else None
    return {
        "id": f"{device_id}-S{seq:04d}",
        "patientName": random.choice(["张伟", "李娜", "王芳", "刘强", "陈静", "杨洋", "赵敏", "黄磊"]),
        "patientId": f"P{random.randint(100000, 999999)}",
        "modality": modality,
        # 只有 CT 检查能走现有的体渲染查看流程
        "viewable": modality == "CT",
        "preset": preset,
        "description": random.choice(titles),
        "receivedAt": _iso(at),
    }


def _seed_devices(now: datetime) -> List[Dict]:
    """构造一批模拟影像设备，各自带若干历史检查。"""
    seeds = [
        ("CT-01", "1号CT机", "CT", "放射科一楼", SCANNING),
        ("CT-02", "2号CT机", "CT", "放射科一楼", IDLE),
        ("MR-01", "1.5T磁共振", "MR", "放射科二楼", IDLE),
        ("DR-01", "数字胃肠DR", "DR", "放射科三楼", OFFLINE),
        ("CT-03", "急诊CT机", "CT", "急诊大楼", OFFLINE),
    ]
    devices: List[Dict] = []
    for i, (did, name, modality, location, status) in enumerate(seeds):
        # 历史检查数：越多越像老设备；时间倒序排列
        study_count = 120 + i * 37 + random.randint(0, 20)
        studies = []
        for seq in range(study_count, max(0, study_count - RECENT_STUDY_LIMIT) + 1, -1):
            at = now - timedelta(minutes=(study_count - seq) * (25 + i * 4) + random.randint(1, 15))
            studies.append(_make_study(did, seq, modality, at))
        last_connected = now - (timedelta(seconds=4) if status != OFFLINE
                                else timedelta(minutes=12 + i * 7))
        devices.append({
            "id": did,
            "name": name,
            "modality": modality,
            "location": location,
            "status": status,
            "lastConnectedAt": _iso(last_connected),
            "totalStudies": study_count,
            "recentStudies": studies,
            "_nextChangeAt": now.timestamp() + random.uniform(*_NEXT_TICK_RANGE),
        })
    return devices


class DeviceRegistry:
    """设备内存状态表 + WebSocket 连接管理 + 状态流转模拟。"""

    def __init__(self) -> None:
        self._devices: Dict[str, Dict] = {}
        self._connections: List[WebSocket] = []
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    # ---- 生命周期 ----
    def seed(self) -> None:
        now = datetime.now(timezone.utc)
        self._devices = {d["id"]: d for d in _seed_devices(now)}

    async def start(self) -> None:
        if self._task is None:
            self.seed()
            self._task = asyncio.create_task(self._simulate())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            self._task = None

    # ---- 查询 ----
    def _public(self, device: Dict) -> Dict:
        """剥离内部字段(带下划线)后返回给前端。"""
        return {k: v for k, v in device.items() if not k.startswith("_")}

    def snapshot(self) -> List[Dict]:
        return [self._public(d) for d in self._devices.values()]

    def get(self, device_id: str) -> Dict:
        device = self._devices.get(device_id)
        if device is None:
            raise HTTPException(status_code=404, detail="设备不存在")
        return self._public(device)

    # ---- WebSocket ----
    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.append(ws)
        # 连上后先推一份当前全量快照
        await ws.send_json({"type": "snapshot", "devices": self.snapshot()})

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self._connections:
            self._connections.remove(ws)

    async def _broadcast(self, changed: Optional[Dict] = None) -> None:
        payload = (
            {"type": "device_changed", "device": changed}
            if changed else
            {"type": "snapshot", "devices": self.snapshot()}
        )
        dead = []
        for ws in list(self._connections):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    # ---- 状态流转模拟 ----
    async def _simulate(self) -> None:
        try:
            while True:
                await asyncio.sleep(_TICK_INTERVAL)
                now_ts = datetime.now(timezone.utc).timestamp()
                changed_ids = []
                async with self._lock:
                    for device in self._devices.values():
                        if now_ts < device["_nextChangeAt"]:
                            continue
                        self._advance(device)
                        device["_nextChangeAt"] = now_ts + random.uniform(*_NEXT_TICK_RANGE)
                        changed_ids.append(device["id"])
                for did in changed_ids:
                    await self._broadcast(self._public(self._devices[did]))
        except asyncio.CancelledError:
            pass

    def _advance(self, device: Dict) -> None:
        """推进单个设备的状态，必要时生成新检查。"""
        now = datetime.now(timezone.utc)
        old_status = device["status"]

        if old_status == OFFLINE:
            # 离线 -> 空闲(恢复连接)；也可能继续离线
            device["status"] = IDLE if random.random() < 0.6 else OFFLINE
        elif old_status == SCANNING:
            # 在检结束 -> 空闲，并产生一条新检查
            device["status"] = IDLE
            device["totalStudies"] += 1
            study = _make_study(device["id"], device["totalStudies"],
                                device["modality"], now)
            device["recentStudies"].insert(0, study)
            del device["recentStudies"][RECENT_STUDY_LIMIT:]
        else:  # IDLE
            r = random.random()
            if r < 0.5:
                device["status"] = SCANNING
            elif r < 0.65:
                device["status"] = OFFLINE
            else:
                device["status"] = IDLE

        # 非离线即视为此刻仍在连接
        if device["status"] != OFFLINE:
            device["lastConnectedAt"] = _iso(now)

    # ---- 重新拉取 ----
    async def refetch(self, device_id: str) -> Dict:
        async with self._lock:
            device = self._devices.get(device_id)
            if device is None:
                raise HTTPException(status_code=404, detail="设备不存在")
            if device["status"] == OFFLINE:
                # 离线设备无法拉取；恢复后前端会再次开放入口
                raise HTTPException(status_code=409, detail="设备离线，无法拉取检查")

            now = datetime.now(timezone.utc)
            device["lastConnectedAt"] = _iso(now)
            # 模拟从设备补拉 0~2 条检查
            pulled = random.randint(0, 2)
            new_studies = []
            for _ in range(pulled):
                device["totalStudies"] += 1
                study = _make_study(device["id"], device["totalStudies"],
                                    device["modality"], now)
                device["recentStudies"].insert(0, study)
                new_studies.append(study)
            del device["recentStudies"][RECENT_STUDY_LIMIT:]

            public = self._public(device)
        await self._broadcast(public)
        return {"device": public, "pulledCount": pulled,
                "newStudies": new_studies}


registry = DeviceRegistry()


@router.get("")
def list_devices():
    """设备列表(含每个设备最近的检查)。"""
    return {"devices": registry.snapshot()}


@router.get("/{device_id}")
def get_device(device_id: str):
    """设备详情：最近连接时间 + 累计检查数 + 最近检查。"""
    return registry.get(device_id)


@router.post("/{device_id}/refetch")
async def refetch_device(device_id: str):
    """从在线设备重新拉取检查；离线设备返回 409。"""
    return await registry.refetch(device_id)


@ws_router.websocket("/ws/devices")
async def devices_ws(ws: WebSocket):
    await registry.connect(ws)
    try:
        while True:
            # 客户端不发业务消息，仅用于探活
            await ws.receive_text()
    except WebSocketDisconnect:
        registry.disconnect(ws)
