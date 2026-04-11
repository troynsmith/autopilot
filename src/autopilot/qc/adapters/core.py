"""Autopilot adapters for qccompute."""

import json
from collections.abc import Callable

import numpy as np
from automol import geom
from qccompute import compute
from qccompute.adapters.base import ProgramAdapter
from qcdata import CalcType, ProgramInput, SinglePointResults

from ..struc import from_geometry, geometry


class ScanAdapter(ProgramAdapter[ProgramInput, SinglePointResults]):
    """Adapter for relaxed scan with geomeTRIC."""

    supported_calctypes = [CalcType.transition_state]  # noqa: RUF012
    program = "geometric_scan"

    def program_version(self, stdout: str | None) -> str:  # noqa: ARG002
        """Return program version."""
        return "v0.0.1"

    def compute_data(
        self,
        input_data: ProgramInput,
        update_func: Callable | None = None,  # noqa: ARG002
        update_interval: float | None = None,  # noqa: ARG002
        **kwargs,  # noqa: ANN003, ARG002
    ) -> tuple[SinglePointResults, str]:
        """Perform relaxed scan with geomeTRIC."""
        # Perform the calculation and return the results and stdout
        scan_params = input_data.keywords.get("scan_params")
        if not scan_params:
            msg = "scan_params missing in ProgramInput keywords."
            raise ValueError(msg)

        def _convert_list(item: str) -> list:
            """Ensure item is a list."""
            if isinstance(item, str):
                return json.loads(item)
            return item

        scan_type = scan_params.get("scan_type")
        idxs = _convert_list(scan_params.get("scan_indices"))
        vals = _convert_list(scan_params.get("scan_values"))

        current_geo = geometry(input_data.structure)
        path_outputs = []
        trajectory = {"path_values": [], "path_energies": [], "path_structures": []}
        log = ""

        for i, val in enumerate(vals):
            geom.set_dist(geo=current_geo, idxs=idxs, dist=val, in_place=True)

            step_inp = input_data.model_copy(
                update={
                    "structure": from_geometry(geo=current_geo),
                    "calctype": CalcType.optimization,
                    "keywords": {
                        **input_data.keywords,
                        "constraints": {
                            "freeze": [
                                {"type": scan_type, "indices": idxs, "value": val}
                            ]
                        },
                    },
                },
                deep=True,
            )

            output = compute("geometric", step_inp)

            current_geo = geometry(output.data.final_structure)

            path_outputs.append(output.data)

            trajectory["path_values"].append(val)
            trajectory["path_energies"].append(output.data.final_energy)
            trajectory["path_structures"].append(output.data.final_structure)

            log += f"\n--- Scan Point {i}: {val} ---\n{output.logs}"

        maximum = max(path_outputs, key=lambda x: x.final_energy)

        if np.allclose(
            trajectory["path_structures"][0].geometry, maximum.final_structure.geometry
        ) or np.allclose(
            trajectory["path_structures"][-1].geometry, maximum.final_structure.geometry
        ):
            msg = f"Highest energy with {scan_params = } was the first or last point."
            raise RuntimeError(msg)

        ts_inp = input_data.model_copy(update={"calctype": CalcType.transition_state})

        output = compute("geometric", ts_inp)

        output.data.extras["trajectory"] = trajectory
        output.data.extras["scan_maximum"] = max(
            path_outputs, key=lambda x: x.final_energy
        )

        return output.data, log
