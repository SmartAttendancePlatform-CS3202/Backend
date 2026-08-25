import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "libs" / "shared-core"))
from shared_core.schemas.events import FaceVerificationTask
from uuid import uuid4
import pytest


def test_invalid_coordinates_rejected():
    with pytest.raises(ValueError):
        FaceVerificationTask(event_id=uuid4(),attempt_id=uuid4(),student_id=uuid4(),verification_window_id=uuid4(),face_image_base64="x"*100,latitude=100,longitude=0)
