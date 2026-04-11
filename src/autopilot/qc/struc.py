"""qc Structure interface."""

import pint
from automol import Geometry, geometry_hash
from autostore import GeometryRow
from qcdata import Structure


def from_geometry(geo: Geometry | GeometryRow) -> Structure:
    """
    Generate qc Structure from Geometry.

    Parameters
    ----------
    geo
        Geometry.

    Returns
    -------
        qc Structure.
    """
    return Structure(
        symbols=geo.symbols,
        geometry=geo.coordinates * pint.Quantity("angstrom").m_as("bohr"),
        charge=geo.charge,
        multiplicity=geo.spin + 1,
    )


def geometry(struc: Structure) -> Geometry:
    """
    Generate Geometry from qc Structure.

    Parameters
    ----------
    struc
        qc Structure.

    Returns
    -------
        Geometry.
    """
    geo = Geometry(
        symbols=struc.symbols,
        coordinates=struc.geometry * pint.Quantity("bohr").m_as("angstrom"),
        charge=struc.charge,
        spin=struc.multiplicity - 1,
    )
    geo.hash = geometry_hash(geo, decimals=6)
    return geo


def geometry_row(struc: Structure) -> GeometryRow:
    """
    Generate GeometryRow from qc Structure.

    Parameters
    ----------
    struc
        qc Structure.

    Returns
    -------
        GeometryRow.
    """
    geo = geometry(struc)
    return GeometryRow(**geo.model_dump())
