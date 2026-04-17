"""Core compute functionality."""

from automol import Geometry
from autostore import (
    Calculation,
    CalculationGeometryLink,
    CalculationRow,
    Database,
    EnergyRow,
    StageRow,
    StationaryPointRow,
    StationaryStageLink,
    StepRow,
)
from autostore.types import Role, RowID
from qccompute import compute
from qcdata import CalcType, Structure

from . import qc
from .utils import store


def run(db: Database, *, calc: Calculation, geo: Geometry) -> RowID:
    """
    Run calculation.

    Parameters
    ----------
    db
        Database connection manager.
    calc
        Calculation metadata.
    geo
        Geometry.
    calctype
        Type of calculation to run.

    Returns
    -------
        CalculationRow id.

    Raises
    ------
    RuntimeError
        If calculation fails.
    NotImplementedError
        If calctype output parsing is not implemented.
    """
    # Resolve initial geometry
    geo_id = store.resolve_geo(db, geo=geo)
    # Query completed calculations
    existing = store.query_calc(db, calc=calc, inp_geo_id=geo_id)
    if existing:
        return existing

    # Run calculation
    prog = calc.superprogram or calc.program
    prog_inp = qc.inputs.from_automech(calc=calc, geo=geo, calctype=calc.calctype)
    prog_out = compute(prog, prog_inp)

    # Log calculation
    calc_out = qc.outputs.calculation_row(prog_out)
    calc_id = db.add(row=calc_out)
    calc_id = store.verify_id(row=calc_out, row_id=calc_id)  # RowID | None -> RowID

    # Link calculation to input geometry
    link_geometry(db, geo_id=geo_id, calc_id=calc_id, role=Role.input)

    if calc.calctype == CalcType.energy:
        write_energy(db, calc_id=calc_id, geo_id=geo_id, val=prog_out.data.energy)

    elif calc.calctype == CalcType.optimization:
        write_stationary(
            db,
            calc_id=calc_id,
            struc=prog_out.data.final_structure,
            ene=prog_out.data.final_energy,
            order=0,
            is_pseudo=False,
        )

    elif calc.calctype == CalcType.conformer_search:
        for conf, ene in zip(
            prog_out.data.conformers, prog_out.data.conformer_energies, strict=True
        ):
            write_stationary(
                db, calc_id=calc_id, struc=conf, ene=ene, order=0, is_pseudo=False
            )

    elif calc.calctype == CalcType.scan:
        raise ValueError(prog_out)
        traj = prog_out.data.extras["trajectory"]
        stp1 = write_stationary(
            db,
            calc_id=calc_id,
            struc=traj["path_structures"][0],
            ene=traj["path_energies"][0],
            order=0,
            is_pseudo=True,
        )
        stg1 = StageRow(is_ts=False)
        stg_id1 = db.add(row=stg1)
        stg_id1 = store.verify_id(row=stg1, row_id=stg_id1)
        stp_stg_1 = StationaryStageLink(stationary_id=stp1, stage_id=stg_id1)
        db.add(row=stp_stg_1)

        stp2 = write_stationary(
            db,
            calc_id=calc_id,
            struc=traj["path_structures"][-1],
            ene=traj["path_energies"][-1],
            order=0,
            is_pseudo=True,
        )
        stg2 = StageRow(is_ts=False)
        stg_id2 = db.add(row=stg2)
        stg_id2 = store.verify_id(row=stg2, row_id=stg_id2)
        stp_stg_2 = StationaryStageLink(stationary_id=stp2, stage_id=stg_id2)
        db.add(row=stp_stg_2)

        stp_ts = write_stationary(
            db,
            calc_id=calc_id,
            struc=prog_out.data.final_structure,
            ene=prog_out.data.final_energy,
            order=1,
            is_pseudo=True,
        )

        stg_ts = StageRow(is_ts=True)
        stg_id_ts = db.add(row=stg_ts)
        stg_id_ts = store.verify_id(row=stg_ts, row_id=stg_id_ts)
        stp_stg_ts = StationaryStageLink(stationary_id=stp_ts, stage_id=stg_id_ts)
        db.add(row=stp_stg_ts)

        step = StepRow(
            stage_id1=stg_id1,
            stage_id2=stg_id2,
            stage_id_ts=stg_id_ts,
            is_barrierless=False,
        )
        db.add(row=step)

    else:
        msg = f"Writing results from {calc.calctype} not yet implemented."
        db.delete(model=CalculationRow, row_id=calc_id)
        raise NotImplementedError(msg)

    return calc_id


def link_geometry(db: Database, *, geo_id: int, calc_id: int, role: Role) -> None:
    """
    Link geometry with calculation in database.

    Parameters
    ----------
    calc_id
        id corresponding to CalculationRow entry in model table.
    geo_id
        id corresponding to GeometryRow entry in model table.
    role
        Role of the geometry in the calculation.
    """
    link = CalculationGeometryLink(
        calculation_id=calc_id, geometry_id=geo_id, role=role
    )
    db.add(row=link)


def write_energy(db: Database, *, calc_id: int, geo_id: int, val: float) -> RowID:
    """
    Write energy results to database.

    Parameters
    ----------
    val
        Value of energy in Hartree.
    calc_id
        id corresponding to CalculationRow entry in model table.
    geo_id
        id corresponding to GeometryRow entry in model table.

    Returns
    -------
        EnergyRow id
    """
    row = EnergyRow(calculation_id=calc_id, geometry_id=geo_id, value=val)
    row_id = db.add(row=row)
    return store.verify_id(row=row, row_id=row_id)


def write_stationary(  # noqa: PLR0913
    db: Database,
    *,
    calc_id: int,
    struc: Structure,
    ene: float,
    order: int,
    is_pseudo: bool,
) -> RowID:
    """
    Write stationary point results to database.

    Parameters
    ----------
    calc_id
        id corresponding to CalculationRow entry in model table.
    struc
        qc optimized Structure.
    ene
        Value of energy in Hartree.
    order


    Returns
    -------
        StationaryPointRow id
    """
    # Write final geometry
    geo = qc.struc.geometry_row(struc)
    geo_id = store.resolve_geo(db, geo=geo)
    # Link calculation to final geometry
    link_geometry(db, geo_id=geo_id, calc_id=calc_id, role=Role.output)
    # Write final energy
    write_energy(db, calc_id=calc_id, geo_id=geo_id, val=ene)
    # Write stationary point
    row = StationaryPointRow(
        geometry_id=geo_id, calculation_id=calc_id, order=order, is_pseudo=is_pseudo
    )
    row_id = db.add(row=row)
    return store.verify_id(row=row, row_id=row_id)
