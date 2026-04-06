"""Core functions."""

import qcop
from automol import Geometry
from autostore.calcn import Calculation
from autostore.database import Database
from autostore.models import CalculationRow, EnergyRow, GeometryRow, StationaryPointRow
from autostore.qc import program, results, structure
from qcio import CalcType
from sqlmodel import select


def energy(db: Database, *, calc: Calculation, geom: Geometry) -> list[int]:
    """Compute energy.

    Parameters
    ----------
    db
        Database connection manager.
    calc
        Calculation metadata.
    geom
        Geometry.
    hash_name
        Calculation hash type.

    Returns
    -------
        List of EnergyRow ids.

    Raises
    ------
    IndexError
        If multiple GeometryRows correspond to input geo.
    RuntimeError
        If the calculation fails.
    """
    calc.calctype = CalcType.energy
    # Get initial GeometryRow
    input_geom_ids = db.query(model=GeometryRow, **geom.model_dump())

    if not input_geom_ids:
        input_geom_id = db.write(row=GeometryRow(**geom.model_dump()))

    elif len(input_geom_ids) > 1:  # can only yield one id due to hash uniqueness
        msg = f"{geom = } not unique in {GeometryRow.__tablename__}."
        raise IndexError(msg)

    else:  # Query existing EnergyRow instances
        input_geom_id = input_geom_ids[0]

        with db.session() as session:
            statement = (
                select(EnergyRow)
                .join(EnergyRow.calculation)  # ty:ignore[invalid-argument-type]
                .join(CalculationRow.input_geometry)  # ty:ignore[invalid-argument-type]
                .where(GeometryRow.id == input_geom_id)
            )

            calc_conditions = [
                getattr(CalculationRow, key) == value
                for key, value in calc.model_dump().items()
                if value is not None
            ]

            statement = statement.where(*calc_conditions)
            matches = session.exec(statement).all()

            if matches:
                return [row.id for row in matches]  # ty:ignore[invalid-return-type]

    # Compute results
    inp = program.from_rows(calc, geom, CalcType.energy)
    res = qcop.compute(calc.program, inp)

    if not res.success or res.data.energy is None:
        msg = f"Calculation failed: {res.traceback}"
        raise RuntimeError(msg)

    calc_row = results.calc_row(res)
    calc_row.input_geometry_id = input_geom_id
    calc_id = db.write(row=calc_row)  # ty:ignore[invalid-argument-type]

    # Use input geo id because structure does not change in energy calctype.
    ene_row = EnergyRow(
        geometry_id=input_geom_id, calculation_id=calc_id, value=res.data.energy
    )

    return [db.write(row=ene_row)]


def initial_geometry(db: Database, *, calc: Calculation, geom: Geometry) -> list[int]:
    """
    Compute stationary point initial geometry.

    Parameters
    ----------
    db
        Database connection manager.
    calc
        Calculation metadata.
    geom
        Geometry.

    Returns
    -------
        List of StationaryPointRow ids.

    Raises
    ------
    RuntimeError
        If the calculation fails.
    """
    calc.calctype = CalcType.optimization
    # Get initial GeometryRow
    input_geom_ids = db.query(model=GeometryRow, **geom.model_dump())

    if not input_geom_ids:
        input_geom_id = db.write(row=GeometryRow(**geom.model_dump()))

    elif len(input_geom_ids) > 1:  # can only yield one id due to hash uniqueness
        msg = f"{geom = } not unique in {GeometryRow.__tablename__}."
        raise IndexError(msg)

    else:  # Query existing EnergyRow instances
        input_geom_id = input_geom_ids[0]

        with db.session() as session:
            statement = (
                select(StationaryPointRow)
                .join(StationaryPointRow.calculation)  # ty:ignore[invalid-argument-type]
                .join(CalculationRow.input_geometry)  # ty:ignore[invalid-argument-type]
                .where(GeometryRow.id == input_geom_id)
            )

            calc_conditions = [
                getattr(CalculationRow, key) == value
                for key, value in calc.model_dump().items()
                if value is not None
            ]

            statement = statement.where(*calc_conditions)
            matches = session.exec(statement).all()

            if matches:
                return [row.id for row in matches]  # ty:ignore[invalid-return-type]

    # Compute results
    inp = program.from_rows(calc, geom, CalcType.optimization)
    res = qcop.compute(calc.program, inp)

    if not res.success or res.data.final_energy is None:
        msg = f"Calculation failed: {res.traceback}"
        raise RuntimeError(msg)

    calc_row = results.calc_row(res)
    calc_row.input_geometry_id = input_geom_id
    calc_id = db.write(row=calc_row)  # ty:ignore[invalid-argument-type]

    final_geom_row = results.geom_row(res)
    final_geom_id = db.write(row=final_geom_row)  # ty:ignore[invalid-argument-type]

    # Use input geo id because structure does not change in energy calctype.
    ene_row = EnergyRow(
        geometry_id=final_geom_id, calculation_id=calc_id, value=res.data.final_energy
    )

    db.write(row=ene_row)

    stp_row = StationaryPointRow(
        geometry_id=final_geom_id, calculation_id=calc_id, order=1
    )

    return [db.write(row=stp_row)]


def conformers(db: Database, *, calc: Calculation, geom: Geometry) -> list[int]:
    """
    Compute stationary point initial geometry.

    Parameters
    ----------
    db
        Database connection manager.
    calc
        Calculation metadata.
    geom
        Geometry.

    Returns
    -------
        List of StationaryPointRow ids.

    Raises
    ------
    RuntimeError
        If the calculation fails.
    """
    calc.calctype = CalcType.conformer_search
    # Get initial GeometryRow
    input_geom_ids = db.query(model=GeometryRow, **geom.model_dump())

    if not input_geom_ids:
        input_geom_id = db.write(row=GeometryRow(**geom.model_dump()))

    elif len(input_geom_ids) > 1:  # can only yield one id due to hash uniqueness
        msg = f"{geom = } not unique in {GeometryRow.__tablename__}."
        raise IndexError(msg)

    else:  # Query existing EnergyRow instances
        input_geom_id = input_geom_ids[0]

        with db.session() as session:
            statement = (
                select(StationaryPointRow)
                .join(StationaryPointRow.calculation)  # ty:ignore[invalid-argument-type]
                .join(CalculationRow.input_geometry)  # ty:ignore[invalid-argument-type]
                .where(GeometryRow.id == input_geom_id)
            )

            calc_conditions = [
                getattr(CalculationRow, key) == value
                for key, value in calc.model_dump().items()
                if value is not None
            ]

            statement = statement.where(*calc_conditions)
            matches = session.exec(statement).all()

            if matches:
                return [row.id for row in matches]  # ty:ignore[invalid-return-type]

    # Compute results
    inp = program.from_rows(calc, geom, CalcType.conformer_search)
    if calc.superprogram:
        res = qcop.compute(calc.superprogram, inp)
    else:
        res = qcop.compute(calc.program, inp)

    if not res.success or res.data.conformers is None:
        msg = f"Calculation failed: {res.traceback}"
        raise RuntimeError(msg)

    calc_row = results.calc_row(res)
    calc_row.input_geometry_id = input_geom_id
    calc_id = db.write(row=calc_row)  # ty:ignore[invalid-argument-type]

    stp_ids = []
    for struc, ene in zip(
        res.data.conformers, res.data.conformer_energies, strict=True
    ):
        conf_geom = structure.geom_row(struc)
        conf_geom_id = db.write(row=conf_geom)  # ty:ignore[invalid-argument-type]

        ene_row = EnergyRow(geometry_id=conf_geom_id, calculation_id=calc_id, value=ene)

        db.write(row=ene_row)

        stp_row = StationaryPointRow(
            geometry_id=conf_geom_id, calculation_id=calc_id, order=1
        )

        stp_ids.append(db.write(row=stp_row))

    return stp_ids
