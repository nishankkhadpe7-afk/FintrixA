"""
Router: simulation endpoint.
"""

import logging
from fastapi import APIRouter, HTTPException, Query

from api.schemas.simulate import SimulationRequest, SimulationResponse
from api.services import simulation_service
from api.core.exceptions import EngineError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Simulation"])


@router.post("/simulate", response_model=SimulationResponse)
def simulate_rules(
    request: SimulationRequest,
    debug: bool = Query(False, description="Include condition-level traces"),
):
    """
    Simulate multiple input scenarios against all active rules.
    Optionally include debug traces per input.
    """
    # Log incoming request
    logger.info(f"Simulation request received: {len(request.inputs)} inputs")
    logger.info(f"Request inputs: {request.inputs}")
    
    # Log each input for debugging
    for idx, input_data in enumerate(request.inputs):
        logger.info(f"Input {idx}: {input_data}")
    
    try:
        result = simulation_service.simulate(request.inputs, debug=debug)
        
        logger.info(f"Simulation completed: {result.get('total_matches', 0)} matches")
        
        return result

    except EngineError as e:
        logger.error(f"Simulation failed: {e}")
        raise HTTPException(status_code=500, detail=e.detail)
