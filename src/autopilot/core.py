"""Core functions."""

import autostore
import qcop
from automol import Geometry, geom
from autostore import (
    Calculation,
    Database,
    EnergyRow,
    fetch,
    write,
)
from autostore.calcn import calculation_hash
from autostore.models import StationaryPointRow
from autostore.qc import program, structure
from qcio import CalcType


def conformer_search(
    calc: Calculation, geo: Geometry, *, hash_name: str = "minimal", db: Database
) -> None:
    """
    Conduct conformer search for given geometry.

    Parameters
    ----------
    geo
        Geometry.
    calc
        Calculation metadata.
    hash_name
        Calculation hash type.
    db
        Database connection manager.

    Returns
    -------
        test

    Raises
    ------
    RuntimeError
        If the calculation fails.
    """
    inp = program.prog_from_rows(calc, geo, CalcType.conformer_search)
    res = qcop.compute(calc.program, inp)

    calc_row, _ = autostore.qc.results.res_to_rows(res)

    for struc, ene in zip(
        res.data.conformers, res.data.conformer_energies, strict=True
    ):
        geo_row = structure.struc_to_row(struc)
        ene_row = write.energy(ene, calc_row=calc_row, geo_row=geo_row, db=db)
        write.stationary_point(
            1, ene_row=ene_row, calc_row=calc_row, geo_row=geo_row, db=db
        )


def energy(
    calc: Calculation, geo: Geometry, *, hash_name: str = "minimal", db: Database
) -> EnergyRow:
    """
    Compute energy.

    Parameters
    ----------
    geo
        Geometry.
    calc
        Calculation metadata.
    hash_name
        Calculation hash type.
    db
        Database connection manager.

    Returns
    -------
        Energy in Hartree.

    Raises
    ------
    RuntimeError
        If the calculation fails.
    """
    ene_row = fetch.energy(geo, calc, db=db, hash_name=hash_name)
    if ene_row is not None:
        return ene_row

    inp = program.prog_from_rows(calc, geo, CalcType.energy)
    res = qcop.compute(calc.program, inp)

    if not res.success or res.data.energy is None:
        msg = f"Calculation failed: {res.traceback}"
        raise RuntimeError(msg)

    calc_row, geo_row = autostore.qc.results.res_to_rows(res)
    val = res.data.energy

    return write.energy(val, calc_row=calc_row, geo_row=geo_row, db=db)


def init_geom(
    calc: Calculation,
    geo: Geometry,
    order: int,
    *,
    hash_name: str = "minimal",
    db: Database,
) -> StationaryPointRow:
    """
    Compute stationary point initial geometry.

    Parameters
    ----------
    geo
        Geometry.
    calc
        Calculation metadata.
    db
        Database connection manager.
    order
        Order of the stationary point.

    Returns
    -------
        Initial geometry.

    Raises
    ------
    RuntimeError
        If the calculation fails.
    """
    inchi = geom.geo_to_inchi(geo)
    calc_hash = calculation_hash(calc, hash_name)

    stp_row = fetch.stationary_point("InChI", inchi, calc_hash, db=db)
    if stp_row is not None:
        return stp_row

    inp = program.prog_from_rows(calc, geo, CalcType.optimization)
    res = qcop.compute(calc.program, inp)

    if not res.success or res.data.final_structure is None:
        msg = f"Calculation failed: {res.traceback}"
        raise RuntimeError(msg)

    calc_row, geo_row = autostore.qc.results.res_to_rows(res)
    val = res.data.final_energy
    ene_row = write.energy(val, calc_row=calc_row, geo_row=geo_row, db=db)

    return write.stationary_point(
        order, ene_row=ene_row, calc_row=calc_row, geo_row=geo_row, db=db
    )
