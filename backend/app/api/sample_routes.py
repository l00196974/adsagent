from fastapi import APIRouter, HTTPException
from typing import Dict, Optional
from app.services.sample_manager import SampleManager

router = APIRouter()
_sample_manager = SampleManager()

@router.post("/generate")
async def generate_samples(
    industry: str = "汽车",
    total_count: int = 1000,
    ratios: Optional[Dict] = None
):
    try:
        if ratios:
            clean_ratios = {}
            for key in ["positive", "churn", "weak", "control"]:
                if key in ratios:
                    try:
                        clean_ratios[key] = int(ratios[key])
                    except (ValueError, TypeError):
                        clean_ratios[key] = 1
            ratios = clean_ratios if clean_ratios else None
        samples = _sample_manager.generate_samples(
            industry=industry,
            ratios=ratios,
            total_count=total_count
        )
        return {"code": 0, "data": samples, "message": "样本生成成功"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/statistics")
async def compute_statistics(samples: Dict):
    try:
        stats = _sample_manager.compute_statistics(samples)
        return {"code": 0, "data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/typical-cases")
async def extract_typical_cases(samples: Dict):
    try:
        cases = _sample_manager.extract_typical_cases(samples)
        return {"code": 0, "data": cases}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
