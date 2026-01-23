# calculation/plot_payloads.py
import os
import time
import numpy as np
import logging
from dataclasses import dataclass
from typing import List, Tuple
from scipy.signal import find_peaks, peak_widths


# ----------------------------------------------------------------------
# 1️⃣  XIC‑grid payload (used by plot_annotated_XICs)
# ----------------------------------------------------------------------
@dataclass
class IonInfo:
    label: str  # e.g. "M+H (123.45)"
    colour: str  # hex string
    x: List[float]  # time axis
    y: List[float]  # intensity axis
    peak_time: float
    peak_intensity: float


@dataclass
class XicCompound:
    name: str
    dock_position: str  # "bottom" or "right"
    relative_to: str | None  # name of the first dock in the row
    ions: List[IonInfo]


# ----------------------------------------------------------------------
# 2️⃣  LC‑annotation payload (used by plot_annotated_LC)
# ----------------------------------------------------------------------
@dataclass
class LcPeak:
    curve_x: np.ndarray
    curve_y: np.ndarray
    colour: str
    brush_colour: str
    label: str  # e.g. "Peak 3"


@dataclass
class LcPayload:
    title: str
    background_colour: str
    x_label: str
    y_label: str
    base_curve: Tuple[np.ndarray, np.ndarray]  # (x, y) of the whole chromatogram
    base_colour: str
    peaks: List[LcPeak]  # one entry per detected peak


logger = logging.getLogger(__name__)


def prepare_xic_payload(path: str, xics: tuple) -> list[XicCompound]:
    """
    Runs the same logic that used to live inside ``plot_annotated_XICs``,
    but returns a list of ``XicCompound`` objects.
    """
    start = time.time()
    colour_list = (
        "#e25759",
        "#0b81a2",
        "#7e4794",
        "#59a89c",
        "#9d2c00",
        "#36b700",
        "#f0c571",
        "#c8c8c8",
        "#e25759",
        "#0b81a2",
        "#7e4794",
        "#59a89c",
        "#9d2c00",
        "#36b700",
        "#f0c571",
        "#c8c8c8",
    )

    payloads: list[XicCompound] = []
    for i, compound in enumerate(xics):
        dock_pos = "bottom" if i % 5 == 0 else "right"
        relative = (
            None if dock_pos == "bottom" else payloads[-1].name if payloads else None
        )

        ions: list[IonInfo] = []
        for j, ion in enumerate(compound.ions.keys()):
            if j >= len(colour_list):
                break
            data = compound.ions[ion]["MS Intensity"]
            if data is None:
                continue

            x = data[0].tolist()
            y = data[1].tolist()
            max_idx = int(np.argmax(data[1]))
            peak_time = float(data[0][max_idx])
            peak_int = float(data[1][max_idx])

            ions.append(
                IonInfo(
                    label=f"{ion} ({compound.ion_info[j]})",
                    colour=colour_list[j],
                    x=x,
                    y=y,
                    peak_time=peak_time,
                    peak_intensity=peak_int,
                )
            )

        payloads.append(
            XicCompound(
                name=compound.name,
                dock_position=dock_pos,
                relative_to=relative,
                ions=ions,
            )
        )

    logger.info(
        "Prepared XIC payload for %s in %.1f ms (%d compounds)",
        os.path.basename(path),
        (time.time() - start) * 1000,
        len(payloads),
    )
    return payloads


def prepare_lc_payload(path: str, chromatogram) -> LcPayload:
    """
    Mirrors ``plot_annotated_LC`` but returns a pure data payload.
    """
    start = time.time()
    filename = os.path.basename(path).split(".")[0]

    # ---- base chromatogram -------------------------------------------------
    base_x = chromatogram["Time (min)"].to_numpy()
    base_y = chromatogram["Value (mAU)"].to_numpy()

    # ---- peak detection ----------------------------------------------------
    lc_peaks, _ = find_peaks(base_y, distance=10, prominence=10)
    widths, _, left, right = peak_widths(base_y, lc_peaks, rel_height=0.9)

    colours = [
        "#cc6677",
        "#332288",
        "#ddcc77",
        "#117733",
        "#88ccee",
        "#882255",
        "#44aa99",
        "#999933",
        "#aa4499",
    ]

    peaks: list[LcPeak] = []
    for i, peak_idx in enumerate(lc_peaks):
        left_i, right_i = int(left[i]), int(right[i])
        curve_x = base_x[left_i:right_i]
        curve_y = base_y[left_i:right_i]

        colour = colours[i % len(colours)]
        peaks.append(
            LcPeak(
                curve_x=curve_x,
                curve_y=curve_y,
                colour=colour,
                brush_colour=colour,
                label=f"Peak {i}",
            )
        )

    payload = LcPayload(
        title=f"Chromatogram of {filename} with annotations (click a peak to select it)",
        background_colour="w",
        x_label="Retention time (min)",
        y_label="Absorbance (mAU)",
        base_curve=(base_x, base_y),
        base_colour="#dddddd",
        peaks=peaks,
    )

    logger.info(
        "Prepared LC payload for %s in %.1f ms (%d peaks)",
        filename,
        (time.time() - start) * 1000,
        len(peaks),
    )
    return payload
