"""VyaparRakshak AI - main FastAPI application."""
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent / ".env")

import os
import logging
from datetime import datetime, timezone
from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

from auth import router as auth_router, seed_users, ensure_indexes as ensure_auth_indexes
from routers.vendors import router as vendors_router
from routers.payments import router as payments_router
from routers.invoices import router as invoices_router
from routers.beneficiaries import router as ben_router
from routers.incidents import router as incidents_router
from routers.comms import router as comms_router
from routers.voice import router as voice_router
from routers.audit import router as audit_router
from routers.reports import router as reports_router
from routers.dashboard import router as dashboard_router
from routers.approvals import router as approvals_router
from routers.notifications import router as notif_router
from routers.vendor_portal import router as vendor_portal_router
from routers.settings import router as settings_router, bootstrap_integrations
from seed import seed_all
from deps import get_db_conn

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("vyaparrakshak")

mongo_url = os.environ["MONGO_URL"]
db_name = os.environ["DB_NAME"]
client = AsyncIOMotorClient(mongo_url)
db = client[db_name]

app = FastAPI(title="VyaparRakshak AI", version="1.0.0")

api = APIRouter(prefix="/api")

@api.get("/")
async def root():
    return {"app": "VyaparRakshak AI", "tagline": "Verify identity. Validate evidence. Protect every payment.",
            "version": "1.0.0", "server_time": datetime.now(timezone.utc).isoformat()}

@api.get("/health")
async def health():
    return {"status": "ok"}

# Register module routers
for r in (auth_router, dashboard_router, vendors_router, payments_router, invoices_router,
          ben_router, incidents_router, comms_router, voice_router, audit_router,
          reports_router, approvals_router, notif_router,
          vendor_portal_router, settings_router):
    api.include_router(r)

app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_origin_regex=".*",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    # Inject db into deps
    get_db_conn.db = db
    await ensure_auth_indexes(db)
    await seed_users(db)
    await seed_all(db)
    await bootstrap_integrations(db)
    logger.info("VyaparRakshak AI startup complete.")


@app.on_event("shutdown")
async def on_shutdown():
    client.close()
