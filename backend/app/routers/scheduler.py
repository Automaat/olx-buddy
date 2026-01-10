"""Scheduler monitoring API endpoints."""

import logging
from typing import Any

from apscheduler.job import Job
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.crud import get_job_executions
from app.database import get_db
from app.scheduler import scheduler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])


class JobInfo(BaseModel):
    """Schema for job information."""

    id: str
    name: str
    next_run_time: str | None
    trigger: str


class JobExecutionResponse(BaseModel):
    """Schema for job execution response."""

    id: int
    job_id: str
    job_name: str
    status: str
    started_at: str
    completed_at: str | None
    error_message: str | None
    result_data: dict | None

    class Config:
        from_attributes = True


@router.get("/jobs", response_model=list[JobInfo])
async def list_jobs() -> list[JobInfo]:
    """List all scheduled jobs with status."""
    jobs: list[Job] = scheduler.get_jobs()

    return [
        JobInfo(
            id=job.id,
            name=job.name or job.id,
            next_run_time=job.next_run_time.isoformat() if job.next_run_time else None,
            trigger=str(job.trigger),
        )
        for job in jobs
    ]


@router.get("/jobs/{job_id}/history", response_model=list[JobExecutionResponse])
async def get_job_history(
    job_id: str, limit: int = Query(default=50, ge=1, le=1000), db: Session = Depends(get_db)
) -> list[Any]:
    """Get execution history for a specific job."""
    executions = get_job_executions(db, job_id=job_id, limit=limit)

    return [
        JobExecutionResponse(
            id=execution.id,
            job_id=execution.job_id,
            job_name=execution.job_name,
            status=execution.status,
            started_at=execution.started_at.isoformat(),
            completed_at=execution.completed_at.isoformat() if execution.completed_at else None,
            error_message=execution.error_message,
            result_data=execution.result_data,
        )
        for execution in executions
    ]


@router.get("/history", response_model=list[JobExecutionResponse])
async def get_all_history(
    limit: int = Query(default=100, ge=1, le=1000), db: Session = Depends(get_db)
) -> list[Any]:
    """Get execution history for all jobs."""
    executions = get_job_executions(db, limit=limit)

    return [
        JobExecutionResponse(
            id=execution.id,
            job_id=execution.job_id,
            job_name=execution.job_name,
            status=execution.status,
            started_at=execution.started_at.isoformat(),
            completed_at=execution.completed_at.isoformat() if execution.completed_at else None,
            error_message=execution.error_message,
            result_data=execution.result_data,
        )
        for execution in executions
    ]


@router.post("/jobs/{job_id}/run")
async def run_job_now(job_id: str) -> dict[str, str]:
    """Manually trigger a job to run immediately."""
    job = scheduler.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    job.modify(next_run_time=None)  # Run immediately
    logger.info("Manually triggered job %s", job_id)

    return {"status": "triggered", "job_id": job_id, "job_name": job.name or job_id}
