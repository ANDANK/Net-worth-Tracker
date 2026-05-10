from fastapi import APIRouter, Depends
from models.schemas import ProjectionScenario, ProjectionResult
from services import projections as svc
from api.auth import verify_token

router = APIRouter(prefix="/projections", tags=["projections"])


@router.post("/run", response_model=ProjectionResult)
def run_projection(scenario: ProjectionScenario, user=Depends(verify_token)):
    return svc.run_projection(scenario)


@router.post("/save")
def save_projection(scenario: ProjectionScenario, user=Depends(verify_token)):
    result = svc.run_projection(scenario)
    svc.save_projection(scenario, result)
    return {"status": "saved", "result": result}


@router.get("/saved")
def list_saved(user=Depends(verify_token)):
    from google_sheets.client import sheets_client
    return sheets_client.get_all_records("projections")
