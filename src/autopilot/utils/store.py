"""Utility functions wrapping autostore."""

from automol import Geometry
from autostore import (
    Calculation,
    CalculationGeometryLink,
    CalculationRow,
    Database,
    GeometryRow,
)
from autostore.types import Role, RowID, SQLModelT
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

# Identity fields necessary for matching calc args to CalculationRows
IDENTITY_FIELDS = ["program", "superprogram", "method", "basis", "input", "calctype"]


def resolve_geo(db: Database, *, geo: Geometry | GeometryRow) -> RowID:
    """
    Query geometries table and add row if not present.

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
        CalculationRow id, or None if not found.
    """
    geo_ids = db.query(model=GeometryRow, hash=geo.hash)

    if geo_ids:
        if len(geo_ids) > 1:  # can only yield one id due to hash unique constraint
            msg = f"{geo = } not unique in {GeometryRow.__tablename__}."
            raise ValueError(msg)

        return geo_ids[0]

    geo_row = GeometryRow(**geo.model_dump())

    try:
        geo_id = db.add(row=geo_row)
        return verify_id(row=geo_row, row_id=geo_id)

    except IntegrityError:  # try to query again
        geo_ids = db.query(model=GeometryRow, hash=geo.hash)
        if geo_ids:
            return geo_ids[0]

        raise


def query_calc(
    db: Database, *, calc: Calculation | CalculationRow, inp_geo_id: RowID
) -> RowID | None:
    """
    Query for existing calculation.

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
        CalculationRow id, or None if not found.

    Raises
    ------
    IndexError
        Duplicate calculations found.
    """
    with db.session() as session:
        statement = (
            select(CalculationRow)
            .join(CalculationGeometryLink)
            .where(
                CalculationGeometryLink.geometry_id == inp_geo_id,
                CalculationGeometryLink.role == Role.input,
            )
        )

        for key in IDENTITY_FIELDS:
            val = getattr(calc, key, None)
            if val is not None:
                statement = statement.where(getattr(CalculationRow, key) == val)

        matches = session.exec(statement).all()

        if matches and matches[0].id is not None:
            if len(matches) > 1:
                msg = f"Duplicate calculations found with {inp_geo_id = } & {calc = }."
                raise IndexError(msg)

            return matches[0].id

    return None


def verify_id(*, row: SQLModelT, row_id: RowID | None) -> RowID:
    """Verify that RowID is not None."""
    if not hasattr(row, "id"):
        msg = f"Cannot verify id from {row.__tablename__} (no id attribute)."
        raise AttributeError(msg)

    if row_id is None:
        msg = f"id value not assigned to {row = }."
        raise ValueError(msg)

    return row_id
