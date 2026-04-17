"""Autopilot adapters for qccompute."""

import json
from collections.abc import Callable

from automol import geom
from qccompute import compute
from qccompute.adapters.base import ProgramAdapter
from qcdata import CalcType, ProgramInput, ScanData

from ..struc import from_geometry, geometry


class ScanAdapter(ProgramAdapter[ProgramInput, ScanData]):
    """Adapter for relaxed scan with geomeTRIC."""

    supported_calctypes = [CalcType.scan]  # noqa: RUF012
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
    ) -> tuple[ScanData, str]:
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
        trajectory = []
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
            trajectory.append(output)
            current_geo = geometry(output.data.final_structure)

            log += f"\n--- Scan Point {i}: {val} ---\n{output.logs}"

        return ScanData(values=vals, trajectory=trajectory), log
