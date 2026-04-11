"""autopilot tests."""

from collections.abc import Iterator

import numpy as np
import pytest
from automol import Geometry
from autostore import CalculationRow, Database
from autostore.models import EnergyRow, GeometryRow, StationaryPointRow
from sqlmodel import select

import autopilot


@pytest.fixture
def database() -> Iterator[Database]:
    """In-memory database fixture."""
    db = Database(":memory:")
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def water() -> Geometry:
    """Water geometry fixture."""
    return Geometry(
        symbols=["O", "H", "H"],
        coordinates=[[0, 0, 0], [1, 0, 0], [0, 1, 0]],  # ty:ignore[invalid-argument-type]
    )


@pytest.fixture
def xtb_calculation() -> CalculationRow:
    """XTB calculation fixture."""
    return CalculationRow(program="crest", method="gfnff")


def test_energy(
    water: Geometry, xtb_calculation: CalculationRow, database: Database
) -> None:
    """Test single-point energy calculation."""
    ene_ids = autopilot.compute.energy(database, calc=xtb_calculation, geom=water)
    ene_row = database.get(model=EnergyRow, row_id=ene_ids[0])
    assert np.isclose(ene_row.value, -0.320207546368996)

    # Second attempt should yield existing ids
    old_ene_ids = autopilot.compute.energy(database, calc=xtb_calculation, geom=water)
    assert old_ene_ids == ene_ids


def test_initial_geometry(
    water: Geometry, xtb_calculation: CalculationRow, database: Database
) -> None:
    """Test initial geometry optimization."""
    stp_ids = autopilot.compute.initial_geometry(
        database, calc=xtb_calculation, geom=water
    )
    assert len(stp_ids) == 1
    stp_id = stp_ids[0]
    with database.session() as session:
        statement = (
            select(StationaryPointRow)
            .join(StationaryPointRow.geometry)  # ty:ignore[invalid-argument-type]
            .join(GeometryRow.energies)  # ty:ignore[invalid-argument-type]
            .where(StationaryPointRow.id == stp_id)
        )

        stp_row = session.exec(statement).first()
        # Assert corresponding StationaryPointRow exists
        assert stp_row is not None
        # Assert geometry has been optimized
        assert water != stp_row.geometry
        # Assert energy has been logged
        assert len(stp_row.geometry.energies) > 0

    # Second attempt should yield existing ids
    old_stp_ids = autopilot.compute.initial_geometry(
        database, calc=xtb_calculation, geom=water
    )
    assert old_stp_ids == stp_ids


def test_conformers(
    water: Geometry, xtb_calculation: CalculationRow, database: Database
) -> None:
    """Test conformer search."""
    stp_ids = autopilot.compute.conformers(database, calc=xtb_calculation, geom=water)
    assert len(stp_ids) == 1
    stp_id = stp_ids[0]
    with database.session() as session:
        statement = (
            select(StationaryPointRow)
            .join(StationaryPointRow.geometry)  # ty:ignore[invalid-argument-type]
            .join(GeometryRow.energies)  # ty:ignore[invalid-argument-type]
            .where(StationaryPointRow.id == stp_id)
        )

        stp_row = session.exec(statement).first()
        # Assert corresponding StationaryPointRow exists
        assert stp_row is not None
        # Assert geometry has been optimized
        assert water != stp_row.geometry
        # Assert energy has been logged
        assert len(stp_row.geometry.energies) > 0

    # Second attempt should yield existing ids
    old_stp_ids = autopilot.compute.conformers(
        database, calc=xtb_calculation, geom=water
    )
    assert old_stp_ids == stp_ids
