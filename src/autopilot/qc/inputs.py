"""qc ProgramInput interface."""

from automol import Geometry
from autostore import Calculation, CalculationRow, GeometryRow
from qcdata import CalcType, DualProgramInput, Model, ProgramInput

from . import struc


def from_automech(
    calc: Calculation | CalculationRow,
    geo: Geometry | GeometryRow,
    calctype: CalcType | str,
) -> DualProgramInput | ProgramInput:
    """
    Instantiate qc (Dual)ProgramInput from AutoMech objects.

    Parameters
    ----------
    calc
        Calculation metadata.
    geo
        Geometry.

    Returns
    -------
        (Dual)ProgramInput.
    """
    model = Model(method=calc.method, basis=calc.basis)

    data = {
        "keywords": calc.keywords,
        "cmdline_args": calc.cmdline_args,
        "files": calc.files,
        "extras": calc.extras,
    }

    if calc.superprogram:
        return DualProgramInput.model_validate(
            {
                "structure": struc.from_geometry(geo),
                "calctype": calctype,
                "keywords": calc.superprogram_keywords,
                "subprogram": calc.program,
                "subprogram_args": {"model": model, **data},
            }
        )

    return ProgramInput.model_validate(
        {
            "structure": struc.from_geometry(geo),
            "calctype": calctype,
            "model": model,
            **data,
        }
    )


def calculation(prog: str, prog_inp: ProgramInput) -> Calculation:
    """
    Extract ProgramInput into a Calculation.

    Parameters
    ----------
    program
        Name of superprogram or program.
    prog_inp
        qc ProgramInput

    Returns
    -------
        Calculation
    """
    base_data = {
        "cmdline_args": prog_inp.cmdline_args,
        "files": prog_inp.files,
        "calctype": prog_inp.calctype.value,
        "extras": prog_inp.extras,
    }

    if isinstance(prog_inp, DualProgramInput):
        calc_data = {
            **base_data,
            "program": prog_inp.subprogram,
            "method": prog_inp.subprogram_args.model.method,
            "basis": prog_inp.subprogram_args.model.basis,
            "keywords": prog_inp.subprogram_args.keywords,
            "superprogram_keywords": prog_inp.keywords,
            "superprogram": prog,
        }
    else:
        calc_data = {
            **base_data,
            "program": prog,
            "method": prog_inp.model.method,
            "basis": prog_inp.model.basis,
            "keywords": prog_inp.keywords,
        }

    return CalculationRow.model_validate(calc_data)
