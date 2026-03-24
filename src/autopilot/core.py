"""Core functions."""


from typing import TYPE_CHECKING

from automol import Geometry, mol
from autostore import Calculation, Database, fetch, read, write
from autostore.calcn import calculation_hash

from . import compute

if TYPE_CHECKING:
    from autostore.models import IdentityRow


def energy(
    geo: Geometry, calc: Calculation, *, db: Database, hash_name: str = "minimal"
) -> float:
    """
    Compute energy.

    Parameters
    ----------
    geo
        Geometry.
    calc
        Calculation metadata.
    db
        Database connection manager.
    hash_name
        Calculation hash type.

    Returns
    -------
        Energy in Hartree.

    Raises
    ------
    RuntimeError
        If the calculation fails.
    """
    ene = read.energy(geo, calc, db=db, hash_name=hash_name)
    if ene is not None:
        return ene

    res = compute.energy(geo, calc)
    if not res.success or res.data.energy is None:
        msg = f"Calculation failed: {res.traceback}"
        raise RuntimeError(msg)

    write.energy(res, db)
    return res.data.energy


def initial_geometry(
    geo: Geometry, calc: Calculation, *, db: Database, order: int
) -> Geometry:
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
    geo_mol = geo.to_mol()
    inchi_str = mol.inchi(geo_mol)

    calc_hash = calculation_hash(calc)

    existing_identity: IdentityRow | None = fetch.identity(
        algorithm="InChI", identifier=inchi_str, db=db
    )

    if existing_identity:
        for stp in existing_identity.stationary_points:
            for hash_row in stp.calculation.hashes:
                if hash_row.value == calc_hash:
                    return stp.geometry.to_geom()

    res = compute.stationary_point(geo, calc)

    if not res.success or res.data.final_structure is None:  # ty:ignore[unresolved-attribute]
        msg = f"Calculation failed: {res.traceback}"
        raise RuntimeError(msg)

    stp = write.stationary_point(res, db, order=order)

    return stp.geometry.to_geom()
