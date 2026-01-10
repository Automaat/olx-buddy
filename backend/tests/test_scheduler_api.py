"""Test scheduler API endpoints."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from apscheduler.job import Job
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from fastapi.testclient import TestClient

from app.main import app
from app.models import JobExecution

client = TestClient(app)


@pytest.fixture
def mock_scheduler():
    """Mock scheduler."""
    with patch("app.routers.scheduler.scheduler") as mock:
        yield mock


@pytest.fixture
def mock_db():
    """Mock database session."""
    with patch("app.routers.scheduler.get_db") as mock:
        db = MagicMock()
        mock.return_value.__enter__ = MagicMock(return_value=db)
        mock.return_value.__exit__ = MagicMock(return_value=False)
        yield db


class TestListJobsEndpoint:
    """Test GET /api/scheduler/jobs endpoint."""

    def test_list_jobs_success(self, mock_scheduler):
        """Test listing all scheduled jobs."""
        mock_job1 = MagicMock(spec=Job)
        mock_job1.id = "refresh_listings"
        mock_job1.name = "Refresh active listings"
        mock_job1.next_run_time = datetime(2026, 1, 10, 12, 0, 0)
        mock_job1.trigger = IntervalTrigger(minutes=30)

        mock_job2 = MagicMock(spec=Job)
        mock_job2.id = "competitor_prices"
        mock_job2.name = "Scrape competitor prices"
        mock_job2.next_run_time = datetime(2026, 1, 11, 3, 0, 0)
        mock_job2.trigger = CronTrigger(hour=3)

        mock_scheduler.get_jobs.return_value = [mock_job1, mock_job2]

        response = client.get("/api/scheduler/jobs")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        assert data[0]["id"] == "refresh_listings"
        assert data[0]["name"] == "Refresh active listings"
        assert data[0]["next_run_time"] == "2026-01-10T12:00:00"

        assert data[1]["id"] == "competitor_prices"
        assert data[1]["name"] == "Scrape competitor prices"

    def test_list_jobs_empty(self, mock_scheduler):
        """Test listing jobs when none exist."""
        mock_scheduler.get_jobs.return_value = []

        response = client.get("/api/scheduler/jobs")

        assert response.status_code == 200
        assert response.json() == []

    def test_list_jobs_no_next_run_time(self, mock_scheduler):
        """Test job with no next run time."""
        mock_job = MagicMock(spec=Job)
        mock_job.id = "cleanup"
        mock_job.name = "Cleanup old data"
        mock_job.next_run_time = None
        mock_job.trigger = CronTrigger(day_of_week="sun", hour=4)

        mock_scheduler.get_jobs.return_value = [mock_job]

        response = client.get("/api/scheduler/jobs")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["next_run_time"] is None


class TestGetJobHistoryEndpoint:
    """Test GET /api/scheduler/jobs/{job_id}/history endpoint."""

    def test_get_job_history_success(self, mock_db):
        """Test getting job execution history."""
        with patch("app.routers.scheduler.get_job_executions") as mock_get:
            mock_executions = [
                JobExecution(
                    id=1,
                    job_id="refresh_listings",
                    job_name="Refresh active listings",
                    status="success",
                    started_at=datetime(2026, 1, 10, 10, 0, 0),
                    completed_at=datetime(2026, 1, 10, 10, 5, 0),
                    error_message=None,
                    result_data={"total_listings": 10, "updated": 10, "errors": 0},
                ),
                JobExecution(
                    id=2,
                    job_id="refresh_listings",
                    job_name="Refresh active listings",
                    status="error",
                    started_at=datetime(2026, 1, 10, 9, 0, 0),
                    completed_at=datetime(2026, 1, 10, 9, 1, 0),
                    error_message="Database connection failed",
                    result_data=None,
                ),
            ]
            mock_get.return_value = mock_executions

            response = client.get("/api/scheduler/jobs/refresh_listings/history")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2

            assert data[0]["id"] == 1
            assert data[0]["status"] == "success"
            assert data[0]["result_data"]["total_listings"] == 10

            assert data[1]["id"] == 2
            assert data[1]["status"] == "error"
            assert data[1]["error_message"] == "Database connection failed"

    def test_get_job_history_empty(self, mock_db):
        """Test getting history for job with no executions."""
        with patch("app.routers.scheduler.get_job_executions") as mock_get:
            mock_get.return_value = []

            response = client.get("/api/scheduler/jobs/nonexistent/history")

            assert response.status_code == 200
            assert response.json() == []

    def test_get_job_history_with_limit(self, mock_db):
        """Test getting job history with custom limit."""
        with patch("app.routers.scheduler.get_job_executions") as mock_get:
            mock_get.return_value = []

            response = client.get("/api/scheduler/jobs/refresh_listings/history?limit=10")

            assert response.status_code == 200
            mock_get.assert_called_once()
            call_kwargs = mock_get.call_args[1]
            assert call_kwargs["limit"] == 10


class TestGetAllHistoryEndpoint:
    """Test GET /api/scheduler/history endpoint."""

    def test_get_all_history_success(self, mock_db):
        """Test getting all job execution history."""
        with patch("app.routers.scheduler.get_job_executions") as mock_get:
            mock_executions = [
                JobExecution(
                    id=1,
                    job_id="refresh_listings",
                    job_name="Refresh active listings",
                    status="success",
                    started_at=datetime(2026, 1, 10, 10, 0, 0),
                    completed_at=datetime(2026, 1, 10, 10, 5, 0),
                ),
                JobExecution(
                    id=2,
                    job_id="cleanup",
                    job_name="Cleanup old data",
                    status="success",
                    started_at=datetime(2026, 1, 9, 4, 0, 0),
                    completed_at=datetime(2026, 1, 9, 4, 2, 0),
                ),
            ]
            mock_get.return_value = mock_executions

            response = client.get("/api/scheduler/history")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["job_id"] == "refresh_listings"
            assert data[1]["job_id"] == "cleanup"

    def test_get_all_history_empty(self, mock_db):
        """Test getting history when no executions exist."""
        with patch("app.routers.scheduler.get_job_executions") as mock_get:
            mock_get.return_value = []

            response = client.get("/api/scheduler/history")

            assert response.status_code == 200
            assert response.json() == []

    def test_get_all_history_with_limit(self, mock_db):
        """Test getting all history with custom limit."""
        with patch("app.routers.scheduler.get_job_executions") as mock_get:
            mock_get.return_value = []

            response = client.get("/api/scheduler/history?limit=20")

            assert response.status_code == 200
            mock_get.assert_called_once()
            call_kwargs = mock_get.call_args[1]
            assert call_kwargs["limit"] == 20


class TestRunJobNowEndpoint:
    """Test POST /api/scheduler/jobs/{job_id}/run endpoint."""

    def test_run_job_now_success(self, mock_scheduler):
        """Test manually triggering a job."""
        mock_job = MagicMock(spec=Job)
        mock_job.id = "refresh_listings"
        mock_job.name = "Refresh active listings"
        mock_job.modify = MagicMock()
        mock_scheduler.get_job.return_value = mock_job

        response = client.post("/api/scheduler/jobs/refresh_listings/run")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "triggered"
        assert data["job_id"] == "refresh_listings"
        assert data["job_name"] == "Refresh active listings"

        mock_job.modify.assert_called_once_with(next_run_time=None)

    def test_run_job_now_not_found(self, mock_scheduler):
        """Test triggering non-existent job."""
        mock_scheduler.get_job.return_value = None

        response = client.post("/api/scheduler/jobs/nonexistent/run")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_run_job_now_all_jobs(self, mock_scheduler):
        """Test triggering each configured job."""
        job_ids = ["refresh_listings", "competitor_prices", "cleanup"]

        for job_id in job_ids:
            mock_job = MagicMock(spec=Job)
            mock_job.id = job_id
            mock_job.name = f"Job {job_id}"
            mock_job.modify = MagicMock()
            mock_scheduler.get_job.return_value = mock_job

            response = client.post(f"/api/scheduler/jobs/{job_id}/run")

            assert response.status_code == 200
            data = response.json()
            assert data["job_id"] == job_id
