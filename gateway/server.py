from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from providers.openai import OpenAIProvider
from gateway.routers.cost_aware import CostAwareRouter

app = FastAPI()

provider = OpenAIProvider()
router = CostAwareRouter()


class GenerateRequest(BaseModel):
    prompt: str


@app.post("/generate")
async def generate(request: GenerateRequest):
    try:
        model = router.select_model(request.dict())
        response = await provider.generate(request.prompt, model=model)

        return {
            "model": model,
            "response": response["output"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))