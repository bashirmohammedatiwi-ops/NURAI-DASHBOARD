"""Iraq demo seed — municipality alerts in Zayouna block 712 (Baghdad).

Street names and coordinates sourced from OpenStreetMap © contributors.
Includes default speed violations in Al-Ameen district (40 km/h limit).
"""

from __future__ import annotations

import secrets
import uuid
import math
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FleetDevice, Project, RoadEvent, RoadEventType
from app.models.fleet import DeviceTelemetry
from app.services.road.event_helpers import default_recipient

DEMO_MARKER = "rasid_iraq_demo_v5"
LEGACY_DEMO_MARKERS = ("rasid_iraq_demo_v1", "rasid_iraq_demo_v2", "rasid_iraq_demo_v3", "rasid_iraq_demo_v4")
DEMO_NEIGHBORHOOD = "zayouna"
DEMO_NEIGHBORHOOD_AR = "الزيونة"
DEMO_BLOCK = "712"
DEMO_BLOCK_AR = "محلة 712"
OSM_ATTRIBUTION = "OpenStreetMap"
# All demo detections are attributed to vehicle #2 (Baghdad fleet)
DEMO_SOURCE_DEVICE = "rasid-bgd-02"
DEMO_SOURCE_VEHICLE_ID = "RASID-BGD-02"

AMEEN_NEIGHBORHOOD = "al_ameen"
AMEEN_NEIGHBORHOOD_AR = "حي الأمين"
AMEEN_SPEED_LIMIT_KMH = 40

# Demo fleet — all offline; Baghdad units across city districts
FLEET_VEHICLES: list[dict] = [
    {"device_id": "rasid-bgd-01", "vehicle_id": "RASID-BGD-01", "gov": "baghdad", "lat": 33.3229822, "lng": 44.4520278, "online": False, "neighborhood_ar": "الزيونة"},
    {"device_id": "rasid-bgd-02", "vehicle_id": "RASID-BGD-02", "gov": "baghdad", "lat": 33.3208066, "lng": 44.4521284, "online": False, "neighborhood_ar": "الزيونة"},
    {"device_id": "rasid-bgd-03", "vehicle_id": "RASID-BGD-03", "gov": "baghdad", "lat": 33.3176879, "lng": 44.4518373, "online": False, "neighborhood_ar": "الزيونة"},
    {"device_id": "rasid-bgd-04", "vehicle_id": "RASID-BGD-04", "gov": "baghdad", "lat": 33.3098500, "lng": 44.5185000, "online": False, "neighborhood_ar": "حي الأمين"},
    {"device_id": "rasid-bgd-05", "vehicle_id": "RASID-BGD-05", "gov": "baghdad", "lat": 33.3120000, "lng": 44.3920000, "online": False, "neighborhood_ar": "الكرادة"},
    {"device_id": "rasid-bgd-06", "vehicle_id": "RASID-BGD-06", "gov": "baghdad", "lat": 33.3128000, "lng": 44.3660000, "online": False, "neighborhood_ar": "المنصور"},
    {"device_id": "rasid-bgd-07", "vehicle_id": "RASID-BGD-07", "gov": "baghdad", "lat": 33.3230000, "lng": 44.4210000, "online": False, "neighborhood_ar": "الرصافة"},
    {"device_id": "rasid-bgd-08", "vehicle_id": "RASID-BGD-08", "gov": "baghdad", "lat": 33.3810000, "lng": 44.3840000, "online": False, "neighborhood_ar": "الأعظمية"},
    {"device_id": "rasid-bgd-09", "vehicle_id": "RASID-BGD-09", "gov": "baghdad", "lat": 33.3890000, "lng": 44.4640000, "online": False, "neighborhood_ar": "مدينة الصدر"},
    {"device_id": "rasid-bgd-10", "vehicle_id": "RASID-BGD-10", "gov": "baghdad", "lat": 33.2430000, "lng": 44.3940000, "online": False, "neighborhood_ar": "الدور"},
]

# OSM centerline polylines — alerts are placed along the middle band, not at street ends.
STREET_POLYLINES: dict[str, list[tuple[float, float]]] = {
    "712-6": [(33.3209604, 44.4472993), (33.3204061, 44.4480162), (33.3198835, 44.4486922), (33.3193685, 44.4493582)],
    "712-8": [(33.3219290, 44.4483501), (33.3213578, 44.4490670), (33.3208314, 44.4497259), (33.3203018, 44.4503880)],
    "712-12": [(33.3232290, 44.4497840), (33.3227326, 44.4504272), (33.3221570, 44.4511718), (33.3216298, 44.4518535)],
    "712-20": [(33.3262504, 44.4531449), (33.3256831, 44.4538772), (33.3251653, 44.4545456), (33.3246601, 44.4551977)],
    "712-18": [(33.3232225, 44.4548032), (33.3237235, 44.4541641), (33.3242347, 44.4535121), (33.3247649, 44.4528357)],
    "712-7": [(33.3170897, 44.4480132), (33.3194050, 44.4505766), (33.3216746, 44.4530894), (33.3245234, 44.4562436)],
    "712-22": [(33.3245234, 44.4562436), (33.3247657, 44.4559127), (33.3248869, 44.4557472), (33.3250081, 44.4555817)],
    "712-23": [(33.3234786, 44.4513770), (33.3247649, 44.4528357), (33.3256831, 44.4538772), (33.3266171, 44.4549363)],
}

# Back-compat alias used by helpers below.
STREET_ON_ROAD_POINTS = STREET_POLYLINES

# Al-Ameen (الأمين الثانية) — OSM-sampled road points, eastern Baghdad
AMEEN_ON_ROAD_POINTS: dict[str, list[tuple[float, float]]] = {
    "nuwwab": [(33.3087489, 44.5170126), (33.3098500, 44.5185000)],
    "araml": [(33.3092000, 44.5148000), (33.3105000, 44.5159000)],
    "park": [(33.3131894, 44.5122919)],
}

# 20 municipality alerts across 8 Zayouna block-712 streets (OSM coordinates).
# 712-7, 712-22, 712-23 → 4 alerts each; 712-6/8 → 1 each; 712-12/20/18 → 2 each.
# Breakdown: 11 speed bump · 3 pothole · 6 manhole.
STREET_SCENARIOS: list[dict] = [
    {
        "street": "712-6",
        "street_ar": "712-6",
        "events": [
            ("speed_bump", "مطب — وسط الشارع", "medium", 0.88),
        ],
    },
    {
        "street": "712-8",
        "street_ar": "712-8",
        "events": [
            ("pothole", "حفرة — منتصف الشارع", "high", 0.91),
        ],
    },
    {
        "street": "712-12",
        "street_ar": "712-12",
        "events": [
            ("speed_bump", "مطب — وسط الشارع", "medium", 0.86),
            ("manhole", "بالوعة — على الشارع", "medium", 0.88),
        ],
    },
    {
        "street": "712-20",
        "street_ar": "712-20",
        "events": [
            ("pothole", "حفرة — وسط الشارع", "high", 0.92),
            ("speed_bump", "مطب — منتصف الشارع", "medium", 0.85),
        ],
    },
    {
        "street": "712-18",
        "street_ar": "712-18",
        "events": [
            ("manhole", "بالوعة — وسط الشارع", "medium", 0.88),
            ("speed_bump", "مطب — على الشارع", "medium", 0.86),
        ],
    },
    {
        "street": "712-7",
        "street_ar": "712-7",
        "events": [
            ("speed_bump", "مطب — وسط الشارع", "medium", 0.84),
            ("speed_bump", "مطب — أمام محل", "medium", 0.83),
            ("pothole", "حفرة — منتصف الشارع", "high", 0.90),
            ("manhole", "بالوعة — على الشارع", "medium", 0.89),
        ],
    },
    {
        "street": "712-22",
        "street_ar": "712-22",
        "events": [
            ("speed_bump", "مطب — وسط الشارع", "medium", 0.85),
            ("speed_bump", "مطب — على الشارع", "low", 0.82),
            ("speed_bump", "مطب — منتصف الشارع", "medium", 0.84),
            ("manhole", "بالوعة — على الشارع", "medium", 0.88),
        ],
    },
    {
        "street": "712-23",
        "street_ar": "712-23",
        "events": [
            ("speed_bump", "مطب — وسط الشارع", "medium", 0.87),
            ("speed_bump", "مطب — منتصف الشارع", "medium", 0.86),
            ("manhole", "بالوعة — على الشارع", "medium", 0.88),
            ("manhole", "بالوعة — قرب مطب", "medium", 0.87),
        ],
    },
]

_EVENT_TYPE = {
    "pothole": RoadEventType.POTHOLE,
    "speed_bump": RoadEventType.SPEED_BUMP,
    "manhole": RoadEventType.POTHOLE,
    "traffic_violation": RoadEventType.TRAFFIC_VIOLATION,
}

_KIND_AR = {
    "pothole": "حفرة",
    "speed_bump": "مطب سرعة",
    "manhole": "بالوعة",
}

# Skip the first/last ~18% of each street so markers sit in the mid-block segment.
_STREET_MID_MARGIN = 0.18


def _pick_street_point(
    polyline: list[tuple[float, float]],
    slot: int,
    total: int,
    *,
    margin: float = _STREET_MID_MARGIN,
) -> tuple[float, float]:
    """Evenly distribute alerts along the middle of an OSM centerline."""
    if not polyline:
        raise ValueError("Empty street polyline")
    if len(polyline) == 1 or total <= 0:
        return polyline[0]

    seg_lens = [
        math.hypot(polyline[i + 1][0] - polyline[i][0], polyline[i + 1][1] - polyline[i][1])
        for i in range(len(polyline) - 1)
    ]
    length = sum(seg_lens) or 1.0
    lo = margin * length
    hi = (1.0 - margin) * length
    target = lo + (hi - lo) * (slot + 0.5) / total

    walked = 0.0
    for i, seg_len in enumerate(seg_lens):
        if walked + seg_len >= target or i == len(seg_lens) - 1:
            frac = (target - walked) / seg_len if seg_len else 0.5
            frac = max(0.0, min(1.0, frac))
            lat_a, lng_a = polyline[i]
            lat_b, lng_b = polyline[i + 1]
            return (
                round(lat_a + (lat_b - lat_a) * frac, 7),
                round(lng_a + (lng_b - lng_a) * frac, 7),
            )
        walked += seg_len
    return polyline[-1]


def _build_municipality_alerts() -> list[dict]:
    alerts: list[dict] = []
    idx = 0
    for scenario in STREET_SCENARIOS:
        street = scenario["street"]
        street_ar = scenario["street_ar"]
        polyline = STREET_POLYLINES.get(street, [])
        events = scenario["events"]
        total_on_street = len(events)
        for slot, event in enumerate(events):
            if len(event) == 5:
                event_key, detail, severity, conf, _legacy_idx = event
            else:
                event_key, detail, severity, conf = event
            idx += 1
            event_type = _EVENT_TYPE[event_key]
            lat, lng = _pick_street_point(polyline, slot, total_on_street)
            kind_ar = _KIND_AR[event_key]
            if street_ar.startswith("شارع"):
                title = f"{kind_ar} — {DEMO_BLOCK_AR} · {street_ar}"
            else:
                title = f"{kind_ar} — {DEMO_BLOCK_AR} {street_ar}"
            if detail and "—" in detail:
                title = f"{kind_ar} — {DEMO_BLOCK_AR} · {detail.split('—', 1)[-1].strip()}"
            alerts.append({
                "event_type": event_type,
                "lat": lat,
                "lng": lng,
                "title": title,
                "severity": severity,
                "confidence": conf,
                "device_key": DEMO_SOURCE_DEVICE,
                "hours_ago": max(1, 24 - idx),
                "street": street,
                "street_ar": street_ar,
                "reference": f"MUN-712-{idx:03d}",
                "detection_class": "manhole" if event_key == "manhole" else None,
            })
    return alerts


MUNICIPALITY_ALERTS = _build_municipality_alerts()
ALL_DEMO_MARKERS = {DEMO_MARKER, *LEGACY_DEMO_MARKERS}


def _build_speed_violation_alerts() -> list[dict]:
    """Two default speed violations in Al-Ameen — residential 40 km/h zone."""
    scenarios = [
        {
            "street": "nuwwab",
            "street_ar": "شارع نواب الضباط",
            "reference": "TRF-AME-001",
            "speed_kmh": 58,
            "hours_ago": 3,
            "point_idx": 0,
            "detail": "قرب تقاطع الزهور",
        },
        {
            "street": "araml",
            "street_ar": "شارع الأرامل",
            "reference": "TRF-AME-002",
            "speed_kmh": 52,
            "hours_ago": 5,
            "point_idx": 0,
            "detail": "أمام مدخل حي الأمين",
        },
    ]
    alerts: list[dict] = []
    for spec in scenarios:
        road_points = AMEEN_ON_ROAD_POINTS.get(spec["street"], [])
        if not road_points:
            raise ValueError(f"Missing on-road points for Al-Ameen street {spec['street']}")
        idx = spec["point_idx"]
        lat, lng = road_points[idx if idx < len(road_points) else 0]
        speed = spec["speed_kmh"]
        limit = AMEEN_SPEED_LIMIT_KMH
        excess = speed - limit
        title = f"تجاوز سرعة — {AMEEN_NEIGHBORHOOD_AR} · {speed} كم/س (حد {limit})"
        alerts.append({
            "event_type": RoadEventType.TRAFFIC_VIOLATION,
            "lat": lat,
            "lng": lng,
            "title": title,
            "severity": "high" if excess >= 15 else "medium",
            "confidence": None,
            "device_key": DEMO_SOURCE_DEVICE,
            "hours_ago": spec["hours_ago"],
            "street": spec["street"],
            "street_ar": spec["street_ar"],
            "reference": spec["reference"],
            "neighborhood": AMEEN_NEIGHBORHOOD,
            "neighborhood_ar": AMEEN_NEIGHBORHOOD_AR,
            "speed_kmh": speed,
            "speed_limit_kmh": limit,
            "speed": speed,
            "speed_limit": limit,
            "excess_kmh": excess,
            "detail": spec["detail"],
        })
    return alerts


SPEED_VIOLATION_ALERTS = _build_speed_violation_alerts()
ALL_DEMO_ALERTS = MUNICIPALITY_ALERTS + SPEED_VIOLATION_ALERTS


def _resolve_source_device(device_by_key: dict[str, FleetDevice]) -> FleetDevice | None:
    return device_by_key.get(DEMO_SOURCE_DEVICE)


def _apply_source_vehicle_meta(meta: dict, device: FleetDevice | None) -> dict:
    meta = dict(meta)
    meta["vehicle_id"] = device.vehicle_id if device else DEMO_SOURCE_VEHICLE_ID
    meta["device_code"] = DEMO_SOURCE_DEVICE
    meta["source_vehicle"] = DEMO_SOURCE_VEHICLE_ID
    return meta


def _demo_event_meta(spec: dict, device: FleetDevice | None) -> dict:
    device = device or None
    meta: dict = {
        "recipient": default_recipient(spec["event_type"]),
        "severity": spec["severity"],
        "municipality_id": "baghdad",
        "street": spec["street"],
        "street_ar": spec["street_ar"],
        "location_source": OSM_ATTRIBUTION,
        "title": spec["title"],
        "reference": spec["reference"],
        "demo_batch": DEMO_MARKER,
    }
    if spec.get("detection_class"):
        meta["detection_class"] = spec["detection_class"]
    if spec.get("neighborhood"):
        meta["neighborhood"] = spec["neighborhood"]
        meta["neighborhood_ar"] = spec.get("neighborhood_ar")
    else:
        meta["neighborhood"] = DEMO_NEIGHBORHOOD
        meta["neighborhood_ar"] = DEMO_NEIGHBORHOOD_AR
        meta["block"] = DEMO_BLOCK
        meta["block_ar"] = DEMO_BLOCK_AR
    if spec["event_type"] == RoadEventType.TRAFFIC_VIOLATION:
        meta["speed_kmh"] = spec["speed_kmh"]
        meta["speed_limit_kmh"] = spec["speed_limit_kmh"]
        meta["speed"] = spec["speed"]
        meta["speed_limit"] = spec["speed_limit"]
        meta["excess_kmh"] = spec["excess_kmh"]
        meta["violation_type"] = "speed"
        if spec.get("detail"):
            meta["detail_ar"] = spec["detail"]
    return _apply_source_vehicle_meta(meta, device)


def _add_demo_event(
    db: AsyncSession,
    project_id: uuid.UUID,
    spec: dict,
    device_by_key: dict[str, FleetDevice],
    *,
    now: datetime,
    seq: int,
) -> RoadEvent:
    device = _resolve_source_device(device_by_key)
    created_at = now - timedelta(hours=spec["hours_ago"], minutes=seq * 3)
    confidence = None if spec["event_type"] == RoadEventType.TRAFFIC_VIOLATION else spec["confidence"]
    event = RoadEvent(
        project_id=project_id,
        device_id=device.id if device else None,
        event_type=spec["event_type"],
        latitude=spec["lat"],
        longitude=spec["lng"],
        confidence=confidence,
        is_active=True,
        extra_metadata=_demo_event_meta(spec, device),
        created_at=created_at,
    )
    db.add(event)
    return event


async def _existing_demo_references(db: AsyncSession, project_id: uuid.UUID) -> set[str]:
    result = await db.execute(select(RoadEvent).where(RoadEvent.project_id == project_id))
    refs: set[str] = set()
    for event in result.scalars().all():
        meta = event.extra_metadata or {}
        if meta.get("demo_batch") != DEMO_MARKER:
            continue
        ref = meta.get("reference")
        if isinstance(ref, str) and ref.strip():
            refs.add(ref.strip().upper())
    return refs


async def sync_demo_missing_alerts(
    db: AsyncSession,
    project_id: uuid.UUID,
    device_by_key: dict[str, FleetDevice],
    *,
    now: datetime | None = None,
) -> int:
    """Insert demo alerts that are missing (e.g. new speed violations after an upgrade)."""
    now = now or datetime.now(timezone.utc)
    existing = await _existing_demo_references(db, project_id)
    added = 0
    for seq, spec in enumerate(ALL_DEMO_ALERTS, start=1):
        ref = str(spec["reference"]).upper()
        if ref in existing:
            continue
        _add_demo_event(db, project_id, spec, device_by_key, now=now, seq=seq + 100)
        added += 1
    if added:
        await db.flush()
    return added


async def demo_already_seeded(db: AsyncSession, project_id: uuid.UUID) -> bool:
    check = await db.execute(
        select(RoadEvent).where(RoadEvent.project_id == project_id).limit(200)
    )
    for ev in check.scalars().all():
        if (ev.extra_metadata or {}).get("demo_batch") == DEMO_MARKER:
            return True
    return False


async def clear_demo_alerts(db: AsyncSession, project_id: uuid.UUID) -> int:
    result = await db.execute(select(RoadEvent).where(RoadEvent.project_id == project_id))
    removed = 0
    for event in result.scalars().all():
        batch = (event.extra_metadata or {}).get("demo_batch")
        if batch not in ALL_DEMO_MARKERS:
            continue
        await db.delete(event)
        removed += 1
    if removed:
        await db.flush()
    return removed


async def _has_legacy_demo(db: AsyncSession, project_id: uuid.UUID) -> bool:
    result = await db.execute(select(RoadEvent).where(RoadEvent.project_id == project_id).limit(200))
    for event in result.scalars().all():
        if (event.extra_metadata or {}).get("demo_batch") in LEGACY_DEMO_MARKERS:
            return True
    return False


async def _purge_stale_demo_fleet(
    db: AsyncSession,
    project_id: uuid.UUID,
    device_by_key: dict[str, FleetDevice],
) -> int:
    """Remove legacy demo fleet units (e.g. other governorates) after roster changes."""
    allowed = {spec["device_id"] for spec in FLEET_VEHICLES}
    source = device_by_key.get(DEMO_SOURCE_DEVICE)
    result = await db.execute(select(FleetDevice).where(FleetDevice.project_id == project_id))
    removed = 0
    for device in result.scalars().all():
        meta = device.extra_metadata or {}
        if meta.get("demo_batch") != DEMO_MARKER or device.device_id in allowed:
            continue
        if source:
            events = await db.execute(
                select(RoadEvent).where(
                    RoadEvent.project_id == project_id,
                    RoadEvent.device_id == device.id,
                )
            )
            for event in events.scalars().all():
                event.device_id = source.id
        telemetry = await db.execute(select(DeviceTelemetry).where(DeviceTelemetry.device_id == device.id))
        for row in telemetry.scalars().all():
            await db.delete(row)
        await db.delete(device)
        removed += 1
    if removed:
        await db.flush()
    return removed


async def sync_demo_fleet(
    db: AsyncSession,
    project_id: uuid.UUID,
    *,
    now: datetime | None = None,
) -> dict[str, FleetDevice]:
    now = now or datetime.now(timezone.utc)
    device_by_key: dict[str, FleetDevice] = {}

    for spec in FLEET_VEHICLES:
        existing = await db.execute(
            select(FleetDevice).where(FleetDevice.device_id == spec["device_id"])
        )
        device = existing.scalar_one_or_none()
        meta = {"governorate": spec["gov"], "demo_batch": DEMO_MARKER}
        if spec["device_id"] == DEMO_SOURCE_DEVICE:
            meta["demo_source_vehicle"] = True
        if spec["device_id"] == DEMO_SOURCE_DEVICE:
            meta["neighborhood"] = DEMO_NEIGHBORHOOD
            meta["neighborhood_ar"] = DEMO_NEIGHBORHOOD_AR
            meta["block"] = DEMO_BLOCK
            meta["block_ar"] = DEMO_BLOCK_AR
        elif spec.get("neighborhood_ar"):
            meta["neighborhood_ar"] = spec["neighborhood_ar"]
        if not device:
            device = FleetDevice(
                project_id=project_id,
                device_id=spec["device_id"],
                vehicle_id=spec["vehicle_id"],
                api_key=secrets.token_urlsafe(24),
                gps_status="fix" if spec["online"] else "lost",
                camera_status="ok",
                is_online=spec["online"],
                latitude=spec["lat"],
                longitude=spec["lng"],
                last_communication=now - timedelta(minutes=2 if spec["online"] else 120),
                extra_metadata=meta,
            )
            db.add(device)
            await db.flush()
        else:
            device.vehicle_id = spec["vehicle_id"]
            device.is_online = spec["online"]
            device.latitude = spec["lat"]
            device.longitude = spec["lng"]
            device.gps_status = "fix" if spec["online"] else "lost"
            device.last_communication = now - timedelta(minutes=2 if spec["online"] else 120)
            device.extra_metadata = {**(device.extra_metadata or {}), **meta}
        device_by_key[spec["device_id"]] = device

    await _purge_stale_demo_fleet(db, project_id, device_by_key)
    await db.flush()
    return device_by_key


async def sync_demo_alert_vehicle(
    db: AsyncSession,
    project_id: uuid.UUID,
    device_by_key: dict[str, FleetDevice],
) -> int:
    """Point every demo alert at RASID-BGD-02 (all 20 municipality + extras)."""
    device = _resolve_source_device(device_by_key)
    if not device:
        return 0

    result = await db.execute(select(RoadEvent).where(RoadEvent.project_id == project_id))
    updated = 0
    for event in result.scalars().all():
        meta = dict(event.extra_metadata or {})
        if meta.get("demo_batch") != DEMO_MARKER:
            continue
        meta = _apply_source_vehicle_meta(meta, device)
        event.device_id = device.id
        event.extra_metadata = meta
        if event.event_type == RoadEventType.TRAFFIC_VIOLATION:
            event.confidence = None
        updated += 1

    if updated:
        await db.flush()
    return updated


async def _try_attach_demo_images(db: AsyncSession, project_id: uuid.UUID) -> dict:
    from app.core.config import get_settings, resolve_data_path
    from app.services.demo.attach_demo_images import attach_demo_images

    settings = get_settings()
    return await attach_demo_images(
        db,
        project_id,
        source_dir=resolve_data_path(settings.demo_images_dir),
        upload_dir=resolve_data_path(settings.evidence_upload_dir),
    )


async def seed_iraq_demo(db: AsyncSession, project_id: uuid.UUID, *, force: bool = False) -> dict:
    now = datetime.now(timezone.utc)
    device_by_key = await sync_demo_fleet(db, project_id, now=now)

    if not force and await demo_already_seeded(db, project_id):
        reassigned = await sync_demo_alert_vehicle(db, project_id, device_by_key)
        added = await sync_demo_missing_alerts(db, project_id, device_by_key, now=now)
        attach = await _try_attach_demo_images(db, project_id)
        return {
            "seeded": False,
            "reason": "already_seeded",
            "vehicles": len(FLEET_VEHICLES),
            "vehicles_online": sum(1 for s in FLEET_VEHICLES if s["online"]),
            "alerts_reassigned": reassigned,
            "alerts_added": added,
            "source_vehicle": DEMO_SOURCE_VEHICLE_ID,
            "images_attached": attach.get("attached", 0),
            "images_source": attach.get("source"),
            "municipality_breakdown": {"speed_bump": 11, "pothole": 3, "manhole": 6},
        }

    cleared = 0
    if force or await _has_legacy_demo(db, project_id):
        cleared = await clear_demo_alerts(db, project_id)

    alerts_created = 0
    for seq, spec in enumerate(ALL_DEMO_ALERTS, start=1):
        _add_demo_event(db, project_id, spec, device_by_key, now=now, seq=seq)
        alerts_created += 1

    await db.flush()
    await sync_demo_alert_vehicle(db, project_id, device_by_key)
    attach = await _try_attach_demo_images(db, project_id)
    return {
        "seeded": True,
        "vehicles": len(FLEET_VEHICLES),
        "vehicles_online": sum(1 for s in FLEET_VEHICLES if s["online"]),
        "alerts": alerts_created,
        "municipality_alerts": len(MUNICIPALITY_ALERTS),
        "speed_violations": len(SPEED_VIOLATION_ALERTS),
        "cleared": cleared,
        "marker": DEMO_MARKER,
        "neighborhood": DEMO_NEIGHBORHOOD_AR,
        "block": DEMO_BLOCK_AR,
        "source_vehicle": DEMO_SOURCE_VEHICLE_ID,
        "images_attached": attach.get("attached", 0),
        "images_source": attach.get("source"),
    }


async def seed_iraq_demo_for_default_project(db: AsyncSession) -> dict | None:
    result = await db.execute(select(Project).where(Project.name == "Road Infrastructure Monitoring"))
    project = result.scalar_one_or_none()
    if not project:
        return None
    return await seed_iraq_demo(db, project.id)


async def ensure_project_demo_events(db: AsyncSession, project_id: uuid.UUID) -> bool:
    """Seed demo alerts when project has no events (first load / empty DB)."""
    count = await db.execute(
        select(func.count(RoadEvent.id)).where(RoadEvent.project_id == project_id)
    )
    if (count.scalar() or 0) > 0:
        return False
    await seed_iraq_demo(db, project_id, force=False)
    await db.flush()
    return True
