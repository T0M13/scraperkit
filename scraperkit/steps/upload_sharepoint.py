"""
upload_sharepoint step — uploads output files to SharePoint via Microsoft Graph API.

Credentials read from environment variables named in notify.sharepoint config.
NOTE: Does nothing unless explicitly in the workflow list.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import requests

from scraperkit.core.base import BaseStep
from scraperkit.core.context import RunContext
from scraperkit.core.registry import register_step

logger = logging.getLogger("scraperkit.steps.upload_sharepoint")


@register_step("upload_sharepoint")
class UploadSharePointStep(BaseStep):
    name = "upload_sharepoint"

    def execute(self, ctx: RunContext) -> dict[str, Any] | None:
        cfg = ctx.config.notify.sharepoint
        if cfg is None:
            logger.warning("upload_sharepoint: no sharepoint config — skipping")
            return {"skipped": True, "reason": "no_config"}

        tenant_id = os.environ.get(cfg.tenant_id_env)
        client_id = os.environ.get(cfg.client_id_env)
        client_secret = os.environ.get(cfg.client_secret_env)

        if not all([tenant_id, client_id, client_secret]):
            logger.warning("upload_sharepoint: missing credentials env vars — skipping")
            return {"skipped": True, "reason": "missing_credentials"}

        token = self._get_token(tenant_id, client_id, client_secret)
        uploaded: list[str] = []

        # Collect output files from all previous steps
        for result in ctx.step_results:
            for file_path in result.output_files:
                src = Path(file_path)
                if not src.exists():
                    continue
                remote_path = f"{cfg.remote_folder}/{src.name}"
                if cfg.keep_only_latest:
                    self._delete_existing(token, cfg, src.suffix)
                self._upload_file(token, cfg, src, remote_path)
                uploaded.append(remote_path)

        logger.info("upload_sharepoint: uploaded %d files", len(uploaded))
        return {"uploaded": uploaded}

    def _get_token(self, tenant_id: str, client_id: str, client_secret: str) -> str:
        url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        resp = requests.post(url, data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "https://graph.microsoft.com/.default",
        }, timeout=30)
        resp.raise_for_status()
        return resp.json()["access_token"]

    def _upload_file(self, token: str, cfg: Any, src: Path, remote_path: str) -> None:
        url = (
            f"https://graph.microsoft.com/v1.0/drives/{cfg.drive_id}"
            f"/root:/{remote_path}:/content"
        )
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/octet-stream",
        }
        with src.open("rb") as f:
            resp = requests.put(url, headers=headers, data=f, timeout=120)
        resp.raise_for_status()

    def _delete_existing(self, token: str, cfg: Any, suffix: str) -> None:
        """List and delete existing files with the same extension in the remote folder."""
        url = (
            f"https://graph.microsoft.com/v1.0/drives/{cfg.drive_id}"
            f"/root:/{cfg.remote_folder}:/children"
        )
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code == 404:
            return
        resp.raise_for_status()
        for item in resp.json().get("value", []):
            if item["name"].endswith(suffix):
                del_url = (
                    f"https://graph.microsoft.com/v1.0/drives/{cfg.drive_id}"
                    f"/items/{item['id']}"
                )
                requests.delete(del_url, headers=headers, timeout=30)
