"""NETRA predictive spend forecasting module.

Calculates second-derivative spend acceleration (velocity change over time)
and projects 30-day confidence intervals (P10, P50, P90) based on historical burn.
Pure math and statistics with zero external dependencies.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional


def calculate_burn_acceleration(
    snapshots: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Calculate the first (velocity) and second (acceleration) derivatives of spend burn rate.
    
    Accepts snapshot list containing 'created_at' (epoch seconds) and 'total_inr_hour'.
    Returns acceleration in INR/hr^2 and qualitative trend.
    """
    if not snapshots or len(snapshots) < 2:
        return {
            "acceleration_inr_hour_sq": 0.0,
            "velocity_inr_hour": 0.0,
            "trend": "stable",
            "samples": len(snapshots) if snapshots else 0,
        }

    # Extract and sort points chronologically
    points = []
    for s in snapshots:
        raw_ts = s.get("created_at", s.get("sk", 0))
        burn = float(s.get("total_inr_hour", 0.0))
        if raw_ts is not None:
            points.append((float(raw_ts), burn))

    points.sort(key=lambda p: p[0])
    if len(points) < 2:
        return {
            "acceleration_inr_hour_sq": 0.0,
            "velocity_inr_hour": 0.0,
            "trend": "stable",
            "samples": len(points),
        }

    # Compute first differences (velocities in INR/hr per hour)
    velocities = []
    for i in range(1, len(points)):
        t_prev, b_prev = points[i - 1]
        t_curr, b_curr = points[i]
        dt_hours = max((t_curr - t_prev) / 3600.0, 0.0001)
        db = b_curr - b_prev
        v = db / dt_hours
        velocities.append((t_curr, v))

    latest_velocity = velocities[-1][1]

    # If only 2 points, acceleration cannot be computed from 2 velocities; return 0 accel
    if len(velocities) < 2:
        trend = "accelerating" if latest_velocity > 0.5 else ("decelerating" if latest_velocity < -0.5 else "stable")
        return {
            "acceleration_inr_hour_sq": 0.0,
            "velocity_inr_hour": round(latest_velocity, 4),
            "trend": trend,
            "samples": len(points),
        }

    # Second difference: acceleration
    v_prev = velocities[-2][1]
    t_prev = velocities[-2][0]
    v_curr = velocities[-1][1]
    t_curr = velocities[-1][0]
    dt_hours = max((t_curr - t_prev) / 3600.0, 0.0001)
    acceleration = (v_curr - v_prev) / dt_hours

    if acceleration > 0.05:
        trend = "accelerating"
    elif acceleration < -0.05:
        trend = "decelerating"
    else:
        trend = "stable"

    return {
        "acceleration_inr_hour_sq": round(acceleration, 4),
        "velocity_inr_hour": round(latest_velocity, 4),
        "trend": trend,
        "samples": len(points),
    }


def project_monthly_spend(
    snapshots: Optional[List[Dict[str, Any]]] = None,
    current_burn_inr: float = 0.0,
    confidence: float = 0.9,
    savings_factor: float = 0.65,
) -> Dict[str, Any]:
    """Project 30-day forward spend with P10, P50, and P90 confidence intervals.
    
    Hours in standard FinOps month = 730.
    """
    burn = max(0.0, float(current_burn_inr))
    horizon_hours = 730.0
    p50 = round(burn * horizon_hours, 2)

    # Calculate empirical variance if snapshots provided
    burns = []
    if snapshots:
        for s in snapshots:
            val = float(s.get("total_inr_hour", 0.0))
            if val > 0:
                burns.append(val)

    if len(burns) >= 2:
        mean = sum(burns) / len(burns)
        variance = sum((x - mean) ** 2 for x in burns) / (len(burns) - 1)
        std_dev = math.sqrt(variance)
    else:
        # Default variance assumption: 15% volatility of current burn
        std_dev = burn * 0.15

    # z-score for 90% confidence = ~1.645
    z = 1.645 if confidence >= 0.9 else 1.28
    # Monthly standard error: std_dev * sqrt(730)
    month_std_err = std_dev * math.sqrt(horizon_hours)
    margin = round(z * month_std_err, 2)

    p10 = max(0.0, round(p50 - margin, 2))
    p90 = round(p50 + margin, 2)
    potential_savings = round(p50 * savings_factor, 2)

    return {
        "current_burn_inr_hour": round(burn, 2),
        "p10_inr_month": p10,
        "p50_inr_month": p50,
        "p90_inr_month": p90,
        "confidence_level": confidence,
        "horizon_hours": int(horizon_hours),
        "potential_savings_30d": potential_savings,
    }
