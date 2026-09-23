import random, math, time, threading
import numpy as np
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Medical Imaging Viewer")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class VolumeRequest(BaseModel):
    preset: str = "brain"  # brain / chest / abdomen
    width: int = 64
    height: int = 64
    depth: int = 64


class ROIRequest(BaseModel):
    center: list = [32, 32, 32]
    radius: int = 10
    label: str = "lesion"


class WindowLevelRequest(BaseModel):
    window: float = 400.0
    level: float = 40.0
    preset: str = "brain"


WINDOW_PRESETS = {
    "lung":     {"window": 1500, "level": -600, "desc": "肺窗 (W1500/L-600)"},
    "mediastinum": {"window": 350, "level": 50, "desc": "纵隔窗 (W350/L50)"},
    "bone":     {"window": 2000, "level": 300, "desc": "骨窗 (W2000/L300)"},
    "brain":    {"window": 80, "level": 40, "desc": "脑窗 (W80/L40)"},
    "abdomen":  {"window": 400, "level": 40, "desc": "腹窗 (W400/L40)"},
}


def generate_volume(preset: str, w: int, h: int, d: int):
    """Generate synthetic CT-like volume"""
    np.random.seed(42)
    vol = np.zeros((d, h, w), dtype=np.float32)

    center_x, center_y, center_z = w//2, h//2, d//2
    for z in range(d):
        for y in range(h):
            for x in range(w):
                # Head-like shape
                rx = (x - center_x - 5) / (w * 0.4)
                ry = (y - center_y) / (h * 0.45)
                rz = (z - center_z + 3) / (d * 0.4)
                dist = math.sqrt(rx**2 + ry**2 + rz**2)

                if preset == "brain":
                    if dist < 0.85:
                        # Brain tissue
                        base = 35
                        # Sulci pattern
                        noise = (np.sin(x * 0.4) * np.cos(y * 0.3) + np.sin(z * 0.35)) * 8
                        # Ventricles (CSF)
                        vent_dist = math.sqrt(((x-center_x+2)/(w*0.15))**2 + ((y-center_y)/(h*0.12))**2 + ((z-center_z)/(d*0.1))**2)
                        if vent_dist < 0.6:
                            base = 10 + noise * 0.3
                        # Skull
                        if dist > 0.7 and dist < 0.85:
                            base = 200 + random.uniform(-20, 20)
                        vol[z, y, x] = base + noise
                    elif dist < 0.9:
                        vol[z, y, x] = 100  # Scalp
                elif preset == "chest":
                    # Body oval
                    bx = (x - center_x) / (w * 0.35)
                    by = (y - center_y) / (h * 0.4)
                    body = math.sqrt(bx**2 + by**2)
                    if body < 1.0:
                        # Lungs (dark)
                        lung_dist1 = math.sqrt(((x-center_x+8)/(w*0.12))**2 + ((y-center_y)/(h*0.13))**2)
                        lung_dist2 = math.sqrt(((x-center_x-8)/(w*0.12))**2 + ((y-center_y)/(h*0.13))**2)
                        if lung_dist1 < 0.7 or lung_dist2 < 0.7:
                            vol[z, y, x] = -650 + np.sin(z*0.3)*30
                        else:
                            vol[z, y, x] = 30 + np.random.uniform(-5, 5)
                        # Spine
                        if abs(x - center_x) < 3 and abs(y - center_y + 8) < 4:
                            vol[z, y, x] = 250
                    vol[z, y, x] += np.random.uniform(-3, 3)
                elif preset == "abdomen":
                    bx = (x - center_x) / (w * 0.33)
                    by = (y - center_y) / (h * 0.4)
                    body = math.sqrt(bx**2 + by**2)
                    if body < 1.0:
                        base = 35
                        # Liver (right upper)
                        lv = math.sqrt(((x-center_x-6)/(w*0.08))**2 + ((y-center_y+4)/(h*0.07))**2)
                        if lv < 0.6:
                            base = 55 + np.random.uniform(-5, 5)
                        # Kidneys
                        kd1 = math.sqrt(((x-center_x-5)/(w*0.04))**2 + ((y-center_y-5)/(h*0.04))**2)
                        kd2 = math.sqrt(((x-center_x+5)/(w*0.04))**2 + ((y-center_y-5)/(h*0.04))**2)
                        if kd1 < 0.4 or kd2 < 0.4:
                            base = 45
                        # Spine
                        if abs(x - center_x) < 3 and abs(y - center_y + 7) < 4:
                            base = 250 + np.random.uniform(-10, 10)
                        vol[z, y, x] = base + np.random.uniform(-9, 9)

    return vol.tolist()


@app.post("/api/volume")
def get_volume(req: VolumeRequest):
    vol = generate_volume(req.preset, req.width, req.height, req.depth)

    # Extract mid slices for MPR
    mid_axial = int(req.depth // 2)
    mid_coronal = int(req.height // 2)
    mid_sagittal = int(req.width // 2)

    # Return: 3D volume + 3 MPR slices
    return {
        "volume": vol,
        "dimensions": [req.depth, req.height, req.width],
        "mpr": {
            "axial": vol[mid_axial],
            "coronal": [[vol[z][mid_coronal][x] for x in range(req.width)] for z in range(req.depth)],
            "sagittal": [[vol[z][y][mid_sagittal] for y in range(req.height)] for z in range(req.depth)]
        },
        "preset": req.preset,
        "windowPresets": WINDOW_PRESETS
    }


class ROIAnalyzeRequest(BaseModel):
    volume: list
    rois: list = []


@app.post("/api/roi")
def analyze_roi(req: ROIAnalyzeRequest):
    results = []
    for roi in req.rois:
        center = roi.get("center", [32, 32, 32])
        radius = roi.get("radius", 8)
        label = roi.get("label", "roi")

        # Extract voxels within sphere
        voxels = []
        try:
            vol = np.array(req.volume)
            d, h, w = vol.shape
            for z in range(max(0, center[2]-radius), min(d, center[2]+radius+1)):
                for y in range(max(0, center[1]-radius), min(h, center[1]+radius+1)):
                    for x in range(max(0, center[0]-radius), min(w, center[0]+radius+1)):
                        if math.sqrt((x-center[0])**2 + (y-center[1])**2 + (z-center[2])**2) <= radius:
                            voxels.append(float(vol[z, y, x]))
        except:
            voxels = []

        if voxels:
            arr = np.array(voxels)
            results.append({
                "label": label,
                "center": center,
                "radius": radius,
                "mean": round(float(np.mean(arr)), 2),
                "std": round(float(np.std(arr)), 2),
                "min": round(float(np.min(arr)), 2),
                "max": round(float(np.max(arr)), 2),
                "voxelCount": len(voxels),
                "histogram": np.histogram(arr, bins=10, range=(float(np.min(arr)), float(np.max(arr))))[0].tolist()
            })

    return {"rois": results}


@app.get("/api/windows")
def get_windows():
    return {"presets": WINDOW_PRESETS}


# ============================================================
# 影像来源设备 (imaging source devices)
# ============================================================

DEVICE_TICK_SECONDS = 5
OFFLINE_MIN_TICKS = 6   # 离线至少 30s 后自动恢复
OFFLINE_MAX_TICKS = 12
_RECENT_LIMIT = 6

_PATIENTS = ["张伟", "王芳", "李娜", "刘洋", "陈静", "杨磊", "赵敏", "黄强", "周丽", "吴勇"]
_MODALITY_TEMPLATES = {
    "CT": [("胸部平扫", "chest"), ("腹部平扫", "abdomen"), ("头颅平扫", "brain")],
    "MR": [("头颅MRI", "brain"), ("腹部MRI", "abdomen")],
    "DR": [("胸部正位片", None), ("腹部立位片", None)],
}

_devices_lock = threading.Lock()
_devices: dict = {}
_sim_rng = random.Random(20240601)


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts).isoformat(timespec="seconds")


def _make_study(device_id: str, modality: str) -> dict:
    seq = _devices[device_id]["counter"] + 1
    _devices[device_id]["counter"] = seq
    description, preset = _sim_rng.choice(_MODALITY_TEMPLATES[modality])
    return {
        "studyId": f"{device_id}-S{seq:04d}",
        "patientName": _sim_rng.choice(_PATIENTS),
        "patientId": f"P{_sim_rng.randint(100000, 999999)}",
        "modality": modality,
        "bodyPart": description,
        "preset": preset,
        "receivedAt": _iso(time.time()),
    }


def _seed_device(device_id: str, name: str, modality: str, room: str,
                 status: str, seed_studies: int, newest_age_minutes: int):
    now = time.time()
    _devices[device_id] = {
        "deviceId": device_id,
        "name": name,
        "modality": modality,
        "room": room,
        "status": status,
        "lastConnectedAt": now if status != "offline" else now - 900,
        "totalStudies": 0,
        "counter": 0,
        "recent": [],
        "offlineTicks": 0,
    }
    # 从旧到新补造历史检查
    for i in range(seed_studies, 0, -1):
        study = _make_study(device_id, modality)
        study["receivedAt"] = _iso(now - newest_age_minutes * 60 - i * 480)
        _devices[device_id]["recent"].append(study)
    _devices[device_id]["recent"].reverse()
    _devices[device_id]["totalStudies"] = max(len(_devices[device_id]["recent"]),
                                              _devices[device_id]["counter"])


def _device_simulation_loop():
    """后台线程：周期性驱动设备心跳、上下线与新检查推送。"""
    while True:
        time.sleep(DEVICE_TICK_SECONDS)
        with _devices_lock:
            for dev in _devices.values():
                now = time.time()
                if dev["status"] == "offline":
                    dev["offlineTicks"] += 1
                    if dev["offlineTicks"] >= _sim_rng.randint(OFFLINE_MIN_TICKS, OFFLINE_MAX_TICKS):
                        # 恢复连接
                        dev["status"] = "idle"
                        dev["offlineTicks"] = 0
                        dev["lastConnectedAt"] = now
                    continue

                # 在线设备：心跳持续上报最近连接时间
                dev["lastConnectedAt"] = now

                if _sim_rng.random() < 0.12:
                    dev["status"] = "offline"
                    dev["offlineTicks"] = 0
                elif dev["status"] == "examining":
                    if _sim_rng.random() < 0.6:
                        study = _make_study(dev["deviceId"], dev["modality"])
                        dev["recent"].insert(0, study)
                        del dev["recent"][_RECENT_LIMIT:]
                        dev["totalStudies"] += 1
                        dev["status"] = "idle"
                else:
                    if _sim_rng.random() < 0.3:
                        dev["status"] = "examining"


def _serialize_study(study: dict) -> dict:
    return {
        "studyId": study["studyId"],
        "patientName": study["patientName"],
        "patientId": study["patientId"],
        "modality": study["modality"],
        "bodyPart": study["bodyPart"],
        "preset": study.get("preset"),
        "receivedAt": study["receivedAt"],
    }


def _serialize_device(dev: dict) -> dict:
    return {
        "deviceId": dev["deviceId"],
        "name": dev["name"],
        "modality": dev["modality"],
        "room": dev["room"],
        "status": dev["status"],
        "lastConnectedAt": _iso(dev["lastConnectedAt"]),
        "totalStudies": dev["totalStudies"],
        "recentStudies": [_serialize_study(s) for s in dev["recent"][:5]],
    }


_seed_device("CT-01", "1号CT机", "CT", "CT室1", "idle", 3, 40)
_seed_device("DR-02", "2号DR机", "DR", "放射室2", "examining", 2, 15)
_seed_device("MR-03", "3号MRI机", "MR", "磁共振室3", "offline", 4, 180)

threading.Thread(target=_device_simulation_loop, daemon=True).start()


@app.get("/api/devices")
def list_devices():
    with _devices_lock:
        devices = [_serialize_device(d) for d in _devices.values()]
    devices.sort(key=lambda d: (d["status"] == "offline", d["deviceId"]))
    return {"devices": devices, "serverTime": _iso(time.time())}


@app.get("/api/devices/{device_id}")
def get_device(device_id: str):
    with _devices_lock:
        dev = _devices.get(device_id)
        if dev is None:
            raise HTTPException(status_code=404, detail="设备不存在")
        return _serialize_device(dev)


@app.post("/api/devices/{device_id}/pull")
def pull_device_studies(device_id: str):
    """从设备重新拉取检查；离线设备不允许拉取(恢复后可再调用)。"""
    with _devices_lock:
        dev = _devices.get(device_id)
        if dev is None:
            raise HTTPException(status_code=404, detail="设备不存在")
        if dev["status"] == "offline":
            raise HTTPException(status_code=409, detail="设备离线，暂不可拉取；恢复连接后请重试")
        pulled = []
        if _sim_rng.random() < 0.7:
            study = _make_study(device_id, dev["modality"])
            dev["recent"].insert(0, study)
            del dev["recent"][_RECENT_LIMIT:]
            dev["totalStudies"] += 1
            pulled.append(study)
        return {
            "device": _serialize_device(dev),
            "pulledCount": len(pulled),
            "pulledStudies": [_serialize_study(s) for s in pulled],
        }