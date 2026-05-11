"""Higher-level run calls."""

from automol import Geometry
from autostore import (
    Calculation,
    CalculationGeometryLink,
    CalculationRow,
    Database,
    EnergyRow,
    GeometryRow,
    StationaryPointRow,
)
from autostore.types import Role, RowID, RowIDs
from qccompute import compute
from qcdata import CalcType

# --- Workflows ---------------------------------


def energy(
    db: Database, *, calc: Calculation, geo: Geometry
) -> tuple[CalculationRow, EnergyRow]:
    """
    Compute energy for geometry.

    Parameters
    ----------
    db
        Database connection manager.
    calc
        Calculation metadata.
    geo
        Geometry.

    Returns
    -------
    CalculationRow, EnergyRow
    """
    inp_calc_row = CalculationRow.from_calculation(calc)
    inp_calc_row.calc_type = CalcType.energy

    # --- Check for existing energy calculations
    existing_calc_rows = db.find(
        model=inp_calc_row.__class__, eager_load=True, **inp_calc_row.model_dump()
    )
    # Find the first match
    for calc_row in existing_calc_rows:
        if not calc_row.energies:
            continue
        for ene_row in calc_row.energies:
            if ene_row.value:
                return calc_row, ene_row

    # --- Compute
    inp_geo_rows = db.find_or_add(
        model=GeometryRow, eager_load=False, **geo.model_dump()
    )

    inp_geo_row = next(inp_geo_rows, None)

    if inp_geo_row is None:
        msg = f"No entry found for {geo = }."
        raise ValueError(msg)

    if next(inp_geo_rows, None) is not None:
        msg = f"Multiple database entries found matching {geo = }"
        raise ValueError(msg)

    prog = inp_calc_row.super_program or inp_calc_row.program
    prog_inp = inp_calc_row.program_input(input_geo=inp_geo_row)
    prog_out = compute(prog, prog_inp)

    # Instantiate output CalcRow (with Provenance) from prog_out
    out_calc_row = CalculationRow.from_program_output(prog_out=prog_out)
    db.add(row=out_calc_row)  # Adds and updates with row ID

    calc_geo_link = CalculationGeometryLink(
        geometry_id=inp_geo_row.id, calculation_id=out_calc_row.id, role=Role.input
    )
    db.add(row=calc_geo_link)

    ene_row = EnergyRow(
        calculation_id=out_calc_row.id,
        geometry_id=inp_geo_row.id,
        value=prog_out.data.energy,
    )
    db.add(row=ene_row)

    return out_calc_row, ene_row


def initial_geometry(
    db: Database, *, calc: Calculation, geo: Geometry, order: int = 0
) -> tuple[CalculationRow, StationaryPointRow]:
    """
    Optimize an initial geometry.

    Parameters
    ----------
    db
        Database connection manager.
    calc
        Calculation metadata.
    geo
        Geometry.
    order
        Order of the stationary point.

    Returns
    -------
    CalculationRow, StationaryPointRow
    """
    inp_calc_row = CalculationRow.from_calculation(calc)
    inp_calc_row.calc_type = CalcType.optimization

    # --- Check for existing energy calculations
    existing_calc_rows = db.find(
        model=inp_calc_row.__class__, eager_load=True, **inp_calc_row.model_dump()
    )
    # Find the first match
    for calc_row in existing_calc_rows:
        if not calc_row.stationary_points:
            continue
        for stp_row in calc_row.stationary_points:
            if stp_row.order == order and not stp_row.is_pseudo:
                return calc_row, stp_row

    # --- Compute
    inp_geo_rows = db.find_or_add(
        model=GeometryRow, eager_load=False, **geo.model_dump()
    )
    inp_geo_row = next(inp_geo_rows, None)

    if inp_geo_row is None:
        msg = f"No entry found for {geo = }."
        raise ValueError(msg)

    if next(inp_geo_rows, None) is not None:
        msg = f"Multiple database entries found matching {geo = }"
        raise ValueError(msg)

    prog = inp_calc_row.super_program or inp_calc_row.program
    prog_inp = inp_calc_row.program_input(input_geo=inp_geo_row)
    prog_out = compute(prog, prog_inp)

    # Instantiate output CalculationRow (with Provenance) from prog_out
    out_calc_row = CalculationRow.from_program_output(prog_out=prog_out)
    db.add(row=out_calc_row)  # Adds and updates with row ID

    calc_geo_link = CalculationGeometryLink(
        geometry_id=inp_geo_row.id, calculation_id=out_calc_row.id, role=Role.input
    )
    db.add(row=calc_geo_link)

    # Instantiate output GeometryRow
    out_geo = GeometryRow.from_structure(struc=prog_out.data.final_structure)
    out_geo_rows = db.find_or_add(
        model=GeometryRow, eager_load=False, **out_geo.model_dump()
    )

    out_geo_row = next(out_geo_rows, None)

    if out_geo_row is None:
        msg = f"No entry found for {geo = }."
        raise ValueError(msg)

    if next(out_geo_rows, None) is not None:
        msg = f"Multiple database entries found matching {out_geo = }"
        raise ValueError(msg)

    stp_row = StationaryPointRow(
        calculation_id=out_calc_row.id,
        geometry_id=out_geo_row.id,
        order=order,
        is_pseudo=False,
    )
    db.add(row=stp_row)

    return out_calc_row, stp_row


def conformer_search(
    db: Database, *, calc: Calculation, geo: Geometry, order: int = 0
) -> tuple[CalculationRow, list[StationaryPointRow]]:
    """
    Conduct a conformer search for the input geometry.

    Parameters
    ----------
    db
        Database connection manager.
    calc
        Calculation metadata.
    geo
        Geometry.
    order
        Order of the stationary point.

    Returns
    -------
    CalculationRowID, GeometryRowID
    """
    inp_calc_row = CalculationRow.from_calculation(calc)
    inp_calc_row.calc_type = CalcType.conformer_search

    # --- Check for existing energy calculations
    existing_calc_rows = db.find(
        model=inp_calc_row.__class__, eager_load=True, **inp_calc_row.model_dump()
    )
    # Find the first match
    stp_rows = []
    for calc_row in existing_calc_rows:
        if not calc_row.stationary_points:
            continue
        for stp_row in calc_row.stationary_points:
            if stp_row.order == order and not stp_row.is_pseudo:
                stp_rows.extend([stp_row])
        if stp_rows:
            return calc_row, stp_rows

    # --- Compute
    inp_geo_rows = db.find_or_add(
        model=GeometryRow, eager_load=False, **geo.model_dump()
    )
    inp_geo_row = next(inp_geo_rows, None)

    if inp_geo_row is None:
        msg = f"No entry found for {geo = }."
        raise ValueError(msg)

    if next(inp_geo_rows, None) is not None:
        msg = f"Multiple database entries found matching {geo = }"
        raise ValueError(msg)

    prog = inp_calc_row.super_program or inp_calc_row.program
    prog_inp = inp_calc_row.program_input(input_geo=inp_geo_row)
    prog_out = compute(prog, prog_inp)

    # Instantiate output CalculationRow (with Provenance) from prog_out
    out_calc_row = CalculationRow.from_program_output(prog_out=prog_out)
    db.add(row=out_calc_row)  # Adds and updates with row ID

    calc_geo_link = CalculationGeometryLink(
        geometry_id=inp_geo_row.id, calculation_id=out_calc_row.id, role=Role.input
    )
    db.add(row=calc_geo_link)

    stp_rows = []
    for struc in prog_out.data.conformers:
        out_geo = GeometryRow.from_structure(struc=struc)
        out_geo_rows = db.find_or_add(
            model=GeometryRow, eager_load=False, **out_geo.model_dump()
        )

        out_geo_row = next(out_geo_rows, None)

        if out_geo_row is None:
            msg = f"No entry found for {geo = }."
            raise ValueError(msg)

        if next(out_geo_rows, None) is not None:
            msg = f"Multiple database entries found matching {out_geo = }"
            raise ValueError(msg)

        calc_geo_link = CalculationGeometryLink(
            geometry_id=out_geo_row.id, calculation_id=out_calc_row.id, role=Role.output
        )
        db.add(row=calc_geo_link)

        stp_row = StationaryPointRow(
            calculation_id=out_calc_row.id,
            geometry_id=out_geo_row.id,
            order=order,
            is_pseudo=False,
        )
        stp_rows.extend([db.add(row=stp_row)])

    return out_calc_row, stp_rows


# def conformer_search(
#     db: Database, *, calc: Calculation, geo: Geometry, order: int
# ) -> tuple[RowID, RowID]:
#     """
#     Search conformer space.

#     Parameters
#     ----------
#     db
#         Database connection manager.
#     calc
#         Calculation metadata.
#     geo
#         Geometry.
#     order
#         Order of the stationary points (minimum = 0, transition = 1, ...)

#     Returns
#     -------
#     tuple[CalcRowID, GeoRowID]
#     """
#     conf_calc = calc.model_copy(
#         update={"calctype": CalcType.conformer_search}, deep=True
#     )
#     input_geo_id = get_or_add_geometry(db, geo=geo)
#     # Check for completed calculations
#     existing_calc_id = find_completed_calculation(
#         db, calc=conf_calc, inp_geo_id=input_geo_id
#     )
#     if existing_calc_id:
#         return existing_calc_id

#     output = execute_computation(calc=conf_calc, geo=geo)

#     calc_id = record_calculation(db, output=output, calctype=CalcType.conformer_search)
#     link_geometry_to_calculation(
#         db, calc_id=calc_id, geo_id=input_geo_id, role=Role.input
#     )

#     for conformer in output.data.conformers:
#         record_stationary(
#             db, calc_id=calc_id, struc=conformer, order=order, is_pseudo=False
#         )

#     return calc_id


# def scan(
#     db: Database, *, calc: Calculation, geo: Geometry, pars: ScanParameters
# ) -> RowID:
#     """
#     Scan reaction coordinate.

#     Parameters
#     ----------
#     db
#         Database connection manager.
#     calc
#         Calculation metadata.
#     geo
#         Geometry.
#     pars
#         Coordinate scan parameters.

#     Returns
#     -------
#     RowID
#         CalculationRow id.
#     """
#     scan_calc = calc.model_copy(
#         update={"calctype": CalcType.transition_state}, deep=True
#     )
#     input_geo_id = get_or_add_geometry(db, geo=geo)
#     # Check for completed calculations
#     existing_calc_id = find_completed_calculation(
#         db, calc=scan_calc, inp_geo_id=input_geo_id
#     )
#     if existing_calc_id:
#         return existing_calc_id

#     output = routines.scan(calc=scan_calc, geo=geo, pars=pars)

#     max_index = np.nanargmax(output.energies)
#     max_output = output.trajectory[max_index].model_copy(deep=True)
#     max_structure = output.structures[max_index]

#     calc_id = record_calculation(
#         db, output=max_output, calctype=CalcType.transition_state
#     )
#     link_geometry_to_calculation(
#         db, calc_id=calc_id, geo_id=input_geo_id, role=Role.input
#     )
#     record_stationary(
#         db, calc_id=calc_id, struc=max_structure, order=1, is_pseudo=False
#     )

#     return calc_id


# # --- Public Helpers ----------------------------
# def execute_computation(*, calc: Calculation, geo: Geometry) -> ProgramOutput:
#     """Execute program with qccompute."""
#     if calc.calctype is None:
#         msg = "CalcType must be provided by calc."
#         raise ValueError(msg)

#     # Run calculation
#     prog = calc.super_program or calc.program
#     inp = qc.inputs.from_automech(calc=calc, geo=geo, calctype=calc.calctype)
#     out = compute(prog, inp)

#     if not out.success:
#         msg = "Unsuccessful compute."
#         raise RuntimeError(msg)

#     return out


# def get_or_add_geometry(db: Database, *, geo: Geometry | GeometryRow) -> RowID:
#     """Ensure a geometry exists in the database and return its id."""
#     # Check by hash
#     existing_ids = db.query(model=GeometryRow, hash=geo.hash)
#     if existing_ids:
#         return existing_ids[0]

#     # Create new
#     geo_row = GeometryRow(**geo.model_dump())
#     geo_id = db.add(row=geo_row)
#     return _ensure_id(row=geo_row, row_id=geo_id)


# def find_completed_calculation(
#     db: Database, *, calc: Calculation | CalculationRow, inp_geo_id: RowID
# ) -> tuple[RowID, RowID] | None:
#     """Query for existing calculation."""
#     # Identity fields necessary for matching calc args to CalculationRows
#     identity_fields = [
#         "calctype",
#         "program",
#         "method",
#         "basis",
#         "input",
#     ]

#     with db.session() as session:
#         statement = (
#             select(CalculationRow)
#             .join(CalculationGeometryLink)
#             .where(
#                 CalculationGeometryLink.geometry_id == inp_geo_id,
#                 CalculationGeometryLink.role == Role.input,
#             )
#         )

#         for key in identity_fields:
#             val = getattr(calc, key, None)
#             if val is not None:
#                 statement = statement.where(getattr(CalculationRow, key) == val)

#         matches = session.exec(statement).all()

#         if matches and matches[0].id is not None:
#             if len(matches) > 1:
#                 msg = f"Ambiguous matches found with {inp_geo_id = } & {calc = }."
#                 raise IndexError(msg)

#             return matches[0].id, output_geo_id

#     return None


# def record_calculation(
#     db: Database, *, output: ProgramOutput, calctype: CalcType
# ) -> RowID:
#     """Convert ProgramOutput to database row and persist it."""
#     calc_row = qc.outputs.calculation_row(program_output=output)
#     calc_row.calctype = calctype
#     row_id = db.add(row=calc_row)
#     return _ensure_id(row=calc_row, row_id=row_id)


# def record_energy(db: Database, *, calc_id: int, geo_id: int, val: float) -> RowID:
#     """Create an EnergyRow and persist it."""
#     row = EnergyRow(calculation_id=calc_id, geometry_id=geo_id, value=val)
#     row_id = db.add(row=row)
#     return _ensure_id(row=row, row_id=row_id)


# def record_stationary(
#     db: Database, *, calc_id: int, struc: Structure, order: int, is_pseudo: bool
# ) -> RowID:
#     """Create a StationaryPointRow and persist it."""
#     # Write final geometry
#     geo = qc.struc.geometry_row(struc)
#     geo_id = get_or_add_geometry(db, geo=geo)
#     # Link final geometry to calculation
#     link_geometry_to_calculation(db, geo_id=geo_id, calc_id=calc_id, role=Role.output)
#     stp_row = StationaryPointRow(
#         geometry_id=geo_id, calculation_id=calc_id, order=order, is_pseudo=is_pseudo
#     )
#     stp_row_id = db.add(row=stp_row)
#     # Verify that stp_row add was successful
#     _ensure_id(row=stp_row, row_id=stp_row_id)
#     # Return final GeometryRow id
#     return _ensure_id(row=geo, row_id=geo_id)


# def link_geometry_to_calculation(
#     db: Database, *, calc_id: RowID, geo_id: RowID, role: Role
# ) -> None:
#     """Link GeometryRow to CalculationRow."""
#     link = CalculationGeometryLink(
#         calculation_id=calc_id, geometry_id=geo_id, role=role
#     )
#     db.add(row=link)


# --- Private helpers ---------------------------
def _flatten_row_ids(*, row_ids: RowIDs) -> RowID:
    """Ensure RowIDs is singular and not None."""
    if not row_ids:
        msg = f"{row_ids = }."
        raise ValueError(msg)

    if len(row_ids) > 1:
        msg = f"{len(row_ids) = }"
        raise ValueError(msg)

    if not row_ids[0]:
        msg = f"{row_ids[0] = }."
        raise ValueError(msg)

    return row_ids[0]
