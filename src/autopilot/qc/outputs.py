"""qc ProgramOutput interface."""

from autostore import CalculationRow
from qcdata import DualProgramInput, ProgramInput, ProgramOutput


def calculation_row(prog_out: ProgramOutput) -> CalculationRow:
    """
    Instantiate CalculationRow from ProgramOutput.

    Parameters
    ----------
    prog_out
        qc ProgramOutput object.

    Returns
    -------
        CalculationRow

    Raises
    ------
    NotImplementedError
        If instantiation from the given input data type is not implemented.
    """
    prog_input = prog_out.input_data
    prov = prog_out.provenance

    # Fields shared by all results
    data = {
        "files": prog_input.files,
        "scratch_dir": prov.scratch_dir,
        "wall_time": prov.wall_time,
        "hostname": prov.hostname,
        "hostcpus": prov.hostcpus,
        "hostmem": prov.hostmem,
        "extras": prog_input.extras,
        "input": None,  # Could store input file text here if desired
    }

    # Dual vs Single program inputs
    if isinstance(prog_input, DualProgramInput):
        calc_data = {
            **data,
            "program": prog_input.subprogram,
            "method": prog_input.subprogram_args.model.method,
            "basis": prog_input.subprogram_args.model.basis,
            "keywords": prog_input.subprogram_args.keywords,
            "superprogram_keywords": prog_input.keywords,
            "cmdline_args": prog_input.cmdline_args,
            "calctype": prog_input.calctype,
            "program_version": prov.extras.get("versions", {}).get(
                prog_input.subprogram
            ),
            "superprogram": prov.program,
            "superprogram_version": prov.program_version,
        }
    elif isinstance(prog_input, ProgramInput):
        calc_data = {
            **data,
            "program": prov.program,
            "method": prog_input.model.method,
            "basis": prog_input.model.basis,
            "keywords": prog_input.keywords,
            "cmdline_args": prog_input.cmdline_args,
            "calctype": prog_input.calctype,
            "program_version": prov.program_version,
        }

    # Validate and return
    return CalculationRow.model_validate(calc_data)
