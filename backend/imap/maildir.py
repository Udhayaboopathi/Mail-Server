from __future__ import annotations

import json
import mailbox
from email import message_from_bytes
from email.message import Message
from email.parser import BytesParser
from email.policy import default
from pathlib import Path
from typing import Any

from config import settings


class MaildirBackend:
    def __init__(self, base_path: str | None = None) -> None:
        self.base_path = Path(base_path or settings.maildir_base)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def mailbox_root(self, mailbox_id: str) -> Path:
        return self.base_path / mailbox_id

    def folder_root(self, mailbox_id: str, folder: str) -> Path:
        normalized = folder.replace("/", ".").strip(".")
        if normalized in {"", "inbox", "Inbox"}:
            return self.mailbox_root(mailbox_id)
        return self.mailbox_root(mailbox_id) / f".{normalized}"

    def ensure_folder(self, mailbox_id: str, folder: str) -> Path:
        root = self.folder_root(mailbox_id, folder)
        for child in ("cur", "new", "tmp"):
            (root / child).mkdir(parents=True, exist_ok=True)
        return root

    def open_folder(self, mailbox_id: str, folder: str) -> mailbox.Maildir:
        return mailbox.Maildir(str(self.ensure_folder(mailbox_id, folder)), create=True)

    def _uids_path(self, mailbox_id: str, folder: str) -> Path:
        return self.folder_root(mailbox_id, folder) / "uid-index.json"

    def _load_uid_index(self, mailbox_id: str, folder: str) -> dict[str, Any]:
        path = self._uids_path(mailbox_id, folder)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {"uidvalidity": 1, "next_uid": 1, "mapping": {}}

    def _save_uid_index(self, mailbox_id: str, folder: str, index: dict[str, Any]) -> None:
        path = self._uids_path(mailbox_id, folder)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(index), encoding="utf-8")

    def _base_key(self, key: str) -> str:
        return key.split(":", 1)[0]

    def _ensure_mapping(self, mailbox_id: str, folder: str, key: str) -> int:
        index = self._load_uid_index(mailbox_id, folder)
        mapping: dict[str, int] = index.setdefault("mapping", {})
        base = self._base_key(key)
        if base not in mapping:
            mapping[base] = int(index["next_uid"])
            index["next_uid"] = int(index["next_uid"]) + 1
            self._save_uid_index(mailbox_id, folder, index)
        return int(mapping[base])

    def uid_for_key(self, mailbox_id: str, folder: str, key: str) -> int:
        return self._ensure_mapping(mailbox_id, folder, key)

    def key_for_uid(self, mailbox_id: str, folder: str, uid: int) -> str | None:
        index = self._load_uid_index(mailbox_id, folder)
        mapping: dict[str, int] = index.get("mapping", {})
        for base, mapped_uid in mapping.items():
            if int(mapped_uid) == int(uid):
                folder_obj = self.open_folder(mailbox_id, folder)
                for key in folder_obj.iterkeys():
                    if self._base_key(key) == base:
                        return key
        return None

    def list_folders(self, mailbox_id: str) -> list[str]:
        root = self.mailbox_root(mailbox_id)
        if not root.exists():
            return ["Inbox"]
        folders = ["Inbox"]
        for path in root.iterdir():
            if path.is_dir() and path.name.startswith("."):
                folders.append(path.name.lstrip("."))
        return sorted(set(folders))

    def append(self, mailbox_id: str, folder: str, raw_message: bytes) -> int:
        folder_obj = self.open_folder(mailbox_id, folder)
        parsed = BytesParser(policy=default).parsebytes(raw_message)
        key = folder_obj.add(parsed)
        folder_obj.flush()
        return self.uid_for_key(mailbox_id, folder, key)

    def list_messages(self, mailbox_id: str, folder: str) -> list[dict[str, Any]]:
        folder_obj = self.open_folder(mailbox_id, folder)
        messages: list[dict[str, Any]] = []
        for key in folder_obj.iterkeys():
            msg = folder_obj.get_message(key)
            uid = self.uid_for_key(mailbox_id, folder, key)
            payload = msg.as_bytes(policy=default)
            messages.append(
                {
                    "uid": uid,
                    "key": key,
                    "subject": msg.get("Subject", ""),
                    "from": msg.get("From", ""),
                    "to": msg.get("To", ""),
                    "date": msg.get("Date", ""),
                    "flags": list(folder_obj.get_flags(key)),
                    "size": len(payload),
                    "raw": payload,
                }
            )
        return messages

    def read_message(self, mailbox_id: str, folder: str, uid: int) -> Message | None:
        key = self.key_for_uid(mailbox_id, folder, uid)
        if key is None:
            return None
        return self.open_folder(mailbox_id, folder).get_message(key)

    def set_flags(self, mailbox_id: str, folder: str, uid: int, flags: str) -> None:
        key = self.key_for_uid(mailbox_id, folder, uid)
        if key is None:
            return
        folder_obj = self.open_folder(mailbox_id, folder)
        folder_obj.set_flags(key, flags)
        folder_obj.flush()

    def remove(self, mailbox_id: str, folder: str, uid: int) -> None:
        key = self.key_for_uid(mailbox_id, folder, uid)
        if key is None:
            return
        folder_obj = self.open_folder(mailbox_id, folder)
        folder_obj.remove(key)
        folder_obj.flush()

    def copy(self, mailbox_id: str, source_folder: str, target_folder: str, uid: int) -> int | None:
        source_key = self.key_for_uid(mailbox_id, source_folder, uid)
        if source_key is None:
            return None
        source = self.open_folder(mailbox_id, source_folder)
        target = self.open_folder(mailbox_id, target_folder)
        message = source.get_message(source_key)
        new_key = target.add(message)
        target.flush()
        return self.uid_for_key(mailbox_id, target_folder, new_key)

    def move(self, mailbox_id: str, source_folder: str, target_folder: str, uid: int) -> int | None:
        copied = self.copy(mailbox_id, source_folder, target_folder, uid)
        if copied is not None:
            self.remove(mailbox_id, source_folder, uid)
        return copied
