"""Types for compute."""

from collections.abc import Sequence
from enum import Enum

import numpy as np
import numpy.typing as npt
from pydantic import BaseModel, ConfigDict, model_validator


class ScanType(str, Enum):
    """Coordinate scan types."""

    distance = "distance"
    angle = "angle"
    dihedral = "dihedral"


class ScanParameters(BaseModel):
    """Container for coordinate scan parameters."""

    # Allow numpy types in the model
    model_config = ConfigDict(arbitrary_types_allowed=True)

    scan_type: ScanType
    scan_indices: Sequence[int]
    scan_values: npt.NDArray[np.float64] | Sequence[float | str]

    end_at_max: bool = False

    @model_validator(mode="after")
    def validate_indices_length(self) -> "ScanParameters":
        """Validate the number of indices matches geometric scan type."""
        mapping = {ScanType.distance: 2, ScanType.angle: 3, ScanType.dihedral: 4}

        required_len = mapping.get(self.scan_type)
        actual_len = len(self.scan_indices)

        if actual_len != required_len:
            msg = (
                f"Too many distance indices provided ({actual_len} != {required_len})."
            )
            raise ValueError(msg)

        return self
