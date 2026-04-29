"""Higher-level qc routines."""

from automol import Geometry, geom
from autostore import Calculation
from qccompute import compute
from qcdata import CalcType

from .types import ScanParameters


# def scan(*, calc: Calculation, geo: Geometry, pars: ScanParameters) -> ScanData:
#     """Perform a coordinate scan with qccompute.

#     Parameters
#     ----------
#     calc

#     geo

#     pars
#         ScanParameters model.
#     """
#     prog = calc.super_program or calc.program

#     if prog.casefold() != "geometric":
#         msg = f"{calc.super_program} not implemented."
#         raise NotImplementedError(msg)

#     if "constraints" in calc.super_keywords:
#         msg = "Restraints must be set through ScanParameters."
#         raise KeyError(msg)

#     if pars.end_at_max:
#         msg = "end_at_max not yet implemented."
#         raise NotImplementedError(msg)

#     curr_geo = geo.model_copy(deep=True)
#     curr_calc = calc.model_copy(deep=True)

#     traj = []

#     for val in pars.scan_values:
#         geom.set_distance(
#             geo=curr_geo, idxs=pars.scan_indices, val=float(val), in_place=True
#         )
#         curr_calc.super_keywords["constraints"] = {
#             "freeze": [
#                 {"type": pars.scan_type, "indices": pars.scan_indices, "value": val}
#             ]
#         }

#         inp = inputs.from_automech(
#             calc=curr_calc, geo=curr_geo, calctype=CalcType.optimization
#         )
#         out = compute(curr_calc.super_program, inp)
#         traj.append(out)

#     return ScanData(trajectory=traj)
