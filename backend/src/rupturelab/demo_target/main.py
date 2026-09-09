from fastapi import FastAPI

from rupturelab.demo_target.routes import router


def create_demo_app() -> FastAPI:
    app = FastAPI(
        title="RuptureLab Demo Target",
        version="0.1.0",
    )

    app.include_router(router)

    return app


app = create_demo_app()
