"""Small, explainable fly-brain simulator used by the local demo.

The public contract is intentionally close to what a real connectome adapter
would expose: sensory input goes in, behavior/readout signals come out.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Protocol


class BrainBackend(Protocol):
    def reset(self, seed: int | None = None) -> None: ...

    def step(self, sensory_input: dict[str, float]) -> dict[str, Any]: ...


@dataclass
class FlyState:
    position: float = 0.5
    hunger: float = 0.5
    arousal: float = 0.2
    shelter_drive: float = 0.3
    cumulative_reward: float = 0.0


class SurrogateFlyBrain:
    """CPU-friendly recurrent approximation, not a biological connectome."""

    def __init__(self) -> None:
        self.rng = random.Random(0)
        self.state = FlyState()
        self.activity = [0.0] * 12

    def reset(self, seed: int | None = None) -> None:
        self.rng = random.Random(seed if seed is not None else 0)
        self.state = FlyState(
            hunger=0.42 + self.rng.random() * 0.16,
            arousal=0.15 + self.rng.random() * 0.10,
            shelter_drive=0.25 + self.rng.random() * 0.10,
        )
        self.activity = [0.0] * 12

    def step(self, sensory_input: dict[str, float]) -> dict[str, Any]:
        food = clamp(sensory_input.get("food", 0.5))
        shelter = clamp(sensory_input.get("shelter", 0.5))
        danger = clamp(sensory_input.get("danger", 0.5))
        social = clamp(sensory_input.get("social", 0.5))
        novelty = clamp(sensory_input.get("novelty", 0.5))
        water = clamp(sensory_input.get("water", 0.5))
        reward_cue = clamp(sensory_input.get("reward", 0.5))
        target_signal = clamp(sensory_input.get("target_signal", food))

        self.state.hunger = clamp(self.state.hunger + 0.011 - food * 0.018)
        self.state.shelter_drive = clamp(self.state.shelter_drive + 0.009 - shelter * 0.015)
        self.state.arousal = clamp(self.state.arousal * 0.91 + danger * 0.19 + novelty * 0.025)

        noise = self.rng.gauss(0.0, 0.035)
        approach = clamp(target_signal * 0.48 + food * 0.10 + shelter * 0.10 + water * 0.08 + social * 0.08 + novelty * 0.08 + reward_cue * 0.08 - danger * 0.30 + noise)
        avoidance = clamp(danger * 0.60 + self.state.hunger * 0.13 + self.state.shelter_drive * 0.16 - shelter * 0.12 - food * 0.08)
        exploration = clamp(novelty * 0.48 + (1.0 - danger) * 0.16 + target_signal * 0.12 + abs(noise) * 0.40)
        dwell = clamp(shelter * 0.25 + target_signal * 0.22 + food * 0.15 + water * 0.12 + social * 0.10 + reward_cue * 0.08 - danger * 0.34 + noise * 0.5)
        reward = approach * 0.55 + dwell * 0.35 - avoidance * 0.45
        self.state.cumulative_reward += reward

        # Twelve visible populations, deliberately grouped for the UI.
        self.activity = [
            target_signal, food, shelter, danger,
            approach, avoidance, exploration, dwell,
            self.state.hunger, self.state.arousal,
            social, clamp(reward * 0.5 + 0.5),
        ]
        return {
            "approach": round(approach, 4),
            "avoidance": round(avoidance, 4),
            "exploration": round(exploration, 4),
            "dwell": round(dwell, 4),
            "activity": [round(value, 4) for value in self.activity],
        }


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def classify(metrics: dict[str, float]) -> tuple[str, float, dict[str, Any]]:
    """Map the observed behavior to a stoplight answer.

    The color is determined from the observed behavior only. This explicit
    mapping is a product decision and is the first thing to recalibrate with
    neuroscience.
    """

    commitment = clamp(metrics["approach"] - metrics["avoidance"] * 0.72)
    hesitation = clamp(1.0 - abs(metrics["approach"] - metrics["avoidance"]) * 2.1)
    if metrics["approach"] >= 0.52 and commitment >= 0.28 and metrics["avoidance"] < 0.34:
        color = "green"
    elif metrics["approach"] >= 0.25 and commitment >= -0.06:
        color = "yellow"
    else:
        color = "red"
    confidence = clamp(abs(commitment) * 1.35 + (1.0 - hesitation) * 0.35 + 0.22)
    behavior = {
        "reachedTarget": bool(color == "green"),
        "commitment": round(commitment, 3),
        "hesitation": round(hesitation, 3),
        "interpretation": "va decidido" if color == "green" else "duda y explora" if color == "yellow" else "no se acerca",
    }
    return color, round(confidence, 3), behavior


def run_indicator(indicator: dict[str, Any], seed: int = 1, steps: int = 36) -> dict[str, Any]:
    brain: BrainBackend = SurrogateFlyBrain()
    brain.reset(seed)
    history: list[dict[str, Any]] = []

    sensory_input = dict(indicator["signals"])
    target_channel = indicator.get("stimulus", {}).get("targetChannel", "food")
    sensory_input["target_signal"] = sensory_input.get(target_channel, 0.5)
    for step_number in range(max(1, min(240, steps))):
        readout = brain.step(sensory_input)
        history.append({"step": step_number + 1, **readout})

    tail = history[-min(12, len(history)):]
    metrics = {
        key: sum(item[key] for item in tail) / len(tail)
        for key in ("approach", "avoidance", "exploration", "dwell")
    }
    color, confidence, behavior = classify(metrics)
    return {
        "indicatorId": indicator["id"],
        "title": indicator["title"],
        "dimension": indicator["dimension"],
        "question": indicator["question"],
        "stimulus": indicator.get("stimulus", {}),
        "answer": color,
        "confidence": confidence,
        "meaning": indicator["colorMeaning"][color],
        "behavior": behavior,
        "metrics": {key: round(value, 3) for key, value in metrics.items()},
        "activity": history[-1]["activity"],
        "trace": [
            {
                "step": item["step"],
                "approach": item["approach"],
                "avoidance": item["avoidance"],
                "exploration": item["exploration"],
                "dwell": item["dwell"],
            }
            for item in history
        ],
        "backend": "surrogate-lif",
    }


def run_survey(indicators: list[dict[str, Any]], seed: int = 1) -> dict[str, Any]:
    results = [run_indicator(indicator, seed=seed + index * 17) for index, indicator in enumerate(indicators)]
    counts = {color: sum(result["answer"] == color for result in results) for color in ("green", "yellow", "red")}
    return {"results": results, "counts": counts, "backend": "surrogate-lif"}
