from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

from app.core.config import settings


GOOGLE_APP_EXPORT_MIME_TYPES = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
}
GOOGLE_DRIVE_FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"


@dataclass(frozen=True)
class DriveFile:
    id: str
    name: str
    mime_type: str
    web_view_link: str | None
    folder_id: str | None


class GoogleDriveKnowledgeClient:
    def __init__(self, key_path: str | None = None):
        self.key_path = key_path or settings.google_drive_service_account_key_path
        if not self.key_path:
            raise RuntimeError("GOOGLE_DRIVE_SERVICE_ACCOUNT_KEY_PATH is not configured")

    def _service(self):
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise RuntimeError(
                "Install google-api-python-client and google-auth to sync Google Drive"
            ) from exc

        credentials = service_account.Credentials.from_service_account_file(
            self.key_path,
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )
        return build("drive", "v3", credentials=credentials, cache_discovery=False)

    def list_files(self, folder_ids: list[str], max_files: int | None = None) -> list[DriveFile]:
        service = self._service()
        files: list[DriveFile] = []
        fields = "nextPageToken, files(id, name, mimeType, webViewLink)"
        folders_to_scan = [normalize_drive_folder_id(folder_id) for folder_id in folder_ids]
        scanned_folders: set[str] = set()

        while folders_to_scan:
            folder_id = folders_to_scan.pop(0)
            if folder_id in scanned_folders:
                continue
            scanned_folders.add(folder_id)
            page_token = None
            while True:
                response = (
                    service.files()
                    .list(
                        q=f"'{folder_id}' in parents and trashed = false",
                        fields=fields,
                        pageSize=min(100, max_files or 100),
                        pageToken=page_token,
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True,
                    )
                    .execute()
                )
                for item in response.get("files", []):
                    if item["mimeType"] == GOOGLE_DRIVE_FOLDER_MIME_TYPE:
                        folders_to_scan.append(item["id"])
                        continue
                    files.append(
                        DriveFile(
                            id=item["id"],
                            name=item["name"],
                            mime_type=item["mimeType"],
                            web_view_link=item.get("webViewLink"),
                            folder_id=folder_id,
                        )
                    )
                    if max_files and len(files) >= max_files:
                        return files

                page_token = response.get("nextPageToken")
                if not page_token:
                    break

        return files

    def download_file(self, file: DriveFile) -> bytes:
        service = self._service()
        if file.mime_type in GOOGLE_APP_EXPORT_MIME_TYPES:
            return (
                service.files()
                .export(fileId=file.id, mimeType=GOOGLE_APP_EXPORT_MIME_TYPES[file.mime_type])
                .execute()
            )
        if file.mime_type.startswith("application/vnd.google-apps."):
            raise RuntimeError(f"Unsupported Google Drive editor type: {file.mime_type}")
        return service.files().get_media(fileId=file.id, supportsAllDrives=True).execute()


def normalize_drive_folder_id(value: str) -> str:
    candidate = value.strip()
    if "://" not in candidate:
        return candidate

    parsed = urlparse(candidate)
    path_parts = [part for part in parsed.path.split("/") if part]
    if "folders" in path_parts:
        folder_index = path_parts.index("folders")
        if len(path_parts) > folder_index + 1:
            return path_parts[folder_index + 1]

    query_id = parse_qs(parsed.query).get("id")
    if query_id:
        return query_id[0]

    return candidate
