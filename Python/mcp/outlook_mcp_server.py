"""Standalone FastMCP Server for Microsoft Outlook.

This server provides Outlook email automation tools using win32com and FastMCP,
completely independent of Django or pyhub internal frameworks.
"""

import asyncio
import base64
import datetime
import enum
import logging
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from typing import Callable, Generator, List, Literal, Optional, TypeVar, Union

from pydantic import Field

try:
    from fastmcp import FastMCP
except ImportError:
    from mcp.server.fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP("Outlook-MCP-Server")
logger = logging.getLogger("outlook_mcp_server")

# Windows COM thread pool for isolating single-threaded apartment COM operations
_com_thread_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="Outlook-COM-Thread")
T = TypeVar("T")


# ==============================================================================
# Enums and Data Structures
# ==============================================================================

class OutlookFolderType(enum.IntEnum):
    olFolderDeletedItems = 3
    olFolderOutbox = 4
    olFolderSentMail = 5
    olFolderInbox = 6
    olFolderCalendar = 9
    olFolderContacts = 10
    olFolderJournal = 11
    olFolderNotes = 12
    olFolderTasks = 13
    olFolderDrafts = 16


class OutlookItemType(enum.IntEnum):
    olMailItem = 0
    olAppointmentItem = 1
    olContactItem = 2
    olTaskItem = 3
    olJournalItem = 4
    olNoteItem = 5
    olPostItem = 6
    olDistributionListItem = 7


class OutlookBodyFormat(enum.IntEnum):
    olFormatUnspecified = 0
    olFormatPlain = 1
    olFormatHTML = 2
    olFormatRichText = 3


@dataclass
class EmailAttachment:
    filename: str
    content_base64: str


@dataclass
class Email:
    identifier: str
    subject: str
    sender_name: str
    sender_email: str
    to: str
    cc: str
    received_at: Optional[datetime.datetime]
    body: Optional[str] = None
    attachments: Optional[List[EmailAttachment]] = None


@dataclass
class OutlookFolderInfo:
    name: str
    entry_id: str


# ==============================================================================
# Helper Utilities
# ==============================================================================

def html_to_text(html: str) -> str:
    """Convert HTML string to plain text."""
    if not html:
        return ""
    text = re.sub(r"<[^>]+>", "", html)
    text = text.replace("&nbsp;", " ")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&amp;", "&")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")
    return text.strip()


def parse_email_list(emails: Optional[Union[str, List[str]]]) -> List[str]:
    """Parse comma- or semicolon-separated string into a list of emails."""
    if not emails:
        return []
    if isinstance(emails, list):
        return [e.strip() for e in emails if e and e.strip()]
    return [e.strip() for e in re.split(r"[,;]", emails) if e.strip()]


async def run_in_com_thread(func: Callable[..., T], *args, **kwargs) -> T:
    """Execute a function inside a dedicated COM-initialized worker thread."""
    def _wrapper():
        import pythoncom
        pythoncom.CoInitialize()
        try:
            return func(*args, **kwargs)
        finally:
            pythoncom.CoUninitialize()

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_com_thread_pool, _wrapper)


# ==============================================================================
# Windows COM Connection Manager
# ==============================================================================

@contextmanager
def get_outlook_app():
    """Context manager to obtain Outlook.Application and MAPI namespace."""
    import pythoncom
    import pywintypes
    import win32com.client

    app = None
    try:
        for attempt in range(3):
            try:
                app = win32com.client.Dispatch("Outlook.Application")
                break
            except pywintypes.com_error as e:
                if attempt == 2:
                    raise RuntimeError(f"Failed to connect to Outlook: {e}")
                time.sleep(1)

        namespace = app.GetNamespace("MAPI")
        yield app, namespace
    finally:
        if app:
            try:
                del app
            except Exception:
                pass


# ==============================================================================
# Core Outlook Functions (Synchronous, called via COM thread)
# ==============================================================================

def _get_folders_sync() -> List[dict]:
    with get_outlook_app() as (_, namespace):
        folders = []

        def walk(folder):
            try:
                if folder.DefaultItemType == OutlookItemType.olMailItem:
                    folders.append({"name": folder.Name, "entry_id": folder.EntryID})
                for subfolder in folder.Folders:
                    walk(subfolder)
            except Exception:
                pass

        for root in namespace.Folders:
            walk(root)
        return folders


def _get_emails_sync(
    max_hours: int = 24,
    query: Optional[str] = None,
    folder_name: str = "inbox",
) -> List[dict]:
    with get_outlook_app() as (_, namespace):
        now = datetime.datetime.now()
        threshold_at = now - datetime.timedelta(hours=max_hours)

        # Select folder
        if folder_name.lower() == "inbox":
            folder = namespace.GetDefaultFolder(OutlookFolderType.olFolderInbox)
        elif folder_name.lower() == "sent":
            folder = namespace.GetDefaultFolder(OutlookFolderType.olFolderSentMail)
        elif folder_name.lower() == "drafts":
            folder = namespace.GetDefaultFolder(OutlookFolderType.olFolderDrafts)
        elif folder_name.lower() == "trash" or folder_name.lower() == "deleted":
            folder = namespace.GetDefaultFolder(OutlookFolderType.olFolderDeletedItems)
        else:
            # Custom folder search
            all_folders = _get_folders_sync()
            entry_id = next((f["entry_id"] for f in all_folders if f["name"].lower() == folder_name.lower()), None)
            if not entry_id:
                raise ValueError(f"Folder '{folder_name}' not found.")
            folder = namespace.GetFolderFromID(entry_id)

        items = folder.Items
        items.Sort("[ReceivedTime]", True)

        if query:
            filter_term = f'@SQL="urn:schemas:httpmail:subject" LIKE "%{query}%"'
            items.Restrict(filter_term)

        email_list = []
        for msg in items:
            try:
                received_at = getattr(msg, "ReceivedTime", None)
                if received_at:
                    received_at = received_at.replace(tzinfo=None)
                    if received_at >= threshold_at:
                        email_list.append(
                            {
                                "identifier": getattr(msg, "EntryID", ""),
                                "subject": getattr(msg, "Subject", ""),
                                "sender_name": getattr(msg, "SenderName", ""),
                                "sender_email": getattr(msg, "SenderEmailAddress", ""),
                                "to": getattr(msg, "To", ""),
                                "cc": getattr(msg, "CC", ""),
                                "received_at": received_at.isoformat(),
                            }
                        )
            except Exception:
                continue

        return email_list


def _get_email_detail_sync(identifier: str) -> dict:
    with get_outlook_app() as (_, namespace):
        msg = namespace.GetItemFromID(identifier)
        subject = getattr(msg, "Subject", "")
        sender_name = getattr(msg, "SenderName", "")
        sender_email = getattr(msg, "SenderEmailAddress", "")
        to = getattr(msg, "To", "")
        cc = getattr(msg, "CC", "")
        received_at = getattr(msg, "ReceivedTime", None)
        if received_at:
            received_at = received_at.replace(tzinfo=None).isoformat()

        html = getattr(msg, "HTMLBody", None)
        plain = getattr(msg, "Body", None)
        body = html_to_text(html) if html else (plain or "")

        attachments = []
        if hasattr(msg, "Attachments") and msg.Attachments.Count > 0:
            for i in range(1, msg.Attachments.Count + 1):
                att = msg.Attachments.Item(i)
                filename = att.FileName
                temp_path = os.path.join(os.getcwd(), filename)
                try:
                    att.SaveAsFile(temp_path)
                    with open(temp_path, "rb") as f:
                        content_b64 = base64.b64encode(f.read()).decode("utf-8")
                    attachments.append({"filename": filename, "content_base64": content_b64})
                finally:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)

        return {
            "identifier": identifier,
            "subject": subject,
            "sender_name": sender_name,
            "sender_email": sender_email,
            "to": to,
            "cc": cc,
            "received_at": received_at,
            "body": body,
            "attachments": attachments,
        }


def _send_email_sync(
    subject: str,
    message: str,
    from_email: Optional[str],
    recipient_list: Union[str, List[str]],
    html_message: Optional[str] = None,
    cc_list: Optional[Union[str, List[str]]] = None,
    bcc_list: Optional[Union[str, List[str]]] = None,
    compose_only: bool = False,
) -> str:
    with get_outlook_app() as (app, namespace):
        mail = app.CreateItem(OutlookItemType.olMailItem)
        mail.Subject = subject

        recipients = parse_email_list(recipient_list)
        if not recipients:
            raise ValueError("recipient_list must contain at least one valid email address.")
        mail.To = "; ".join(recipients)

        parsed_cc = parse_email_list(cc_list)
        if parsed_cc:
            mail.CC = "; ".join(parsed_cc)

        parsed_bcc = parse_email_list(bcc_list)
        if parsed_bcc:
            mail.BCC = "; ".join(parsed_bcc)

        # Set sending account if specified
        if from_email:
            for i in range(1, namespace.Session.Accounts.Count + 1):
                acc = namespace.Session.Accounts.Item(i)
                if acc.SmtpAddress.lower() == from_email.lower():
                    mail.SendUsingAccount = acc
                    break

        if html_message:
            mail.BodyFormat = OutlookBodyFormat.olFormatHTML
            mail.HTMLBody = html_message
            mail.Body = message
        else:
            mail.BodyFormat = OutlookBodyFormat.olFormatPlain
            mail.Body = message

        mail.Save()

        if compose_only:
            mail.Display()
            return "Email compose window opened successfully in Outlook."

        mail.Send()
        return "Email sent successfully via Outlook."


# ==============================================================================
# MCP Tools
# ==============================================================================

@mcp.tool()
async def outlook_list_folders() -> List[dict]:
    """List all available Outlook mail folders and their EntryIDs."""
    return await run_in_com_thread(_get_folders_sync)


@mcp.tool()
async def outlook_list_emails(
    max_hours: int = Field(default=24, description="Maximum number of hours to look back for emails"),
    query: Optional[str] = Field(default=None, description="Search query to filter emails by subject"),
    folder: str = Field(
        default="inbox",
        description="Folder to list (inbox, sent, drafts, trash, or custom folder name)",
    ),
) -> List[dict]:
    """List emails from a specified Outlook folder within the given time window."""
    return await run_in_com_thread(_get_emails_sync, max_hours=max_hours, query=query, folder_name=folder)


@mcp.tool()
async def outlook_get_email(
    identifier: str = Field(description="Unique EntryID of the email to retrieve"),
) -> dict:
    """Get full details, plain text body, and base64 attachments of a specific email."""
    return await run_in_com_thread(_get_email_detail_sync, identifier=identifier)


@mcp.tool()
async def outlook_send_email(
    subject: str = Field(description="Email subject"),
    message: str = Field(description="Plain text message content"),
    recipient_list: str = Field(description="Comma-separated recipient email addresses"),
    from_email: Optional[str] = Field(default=None, description="Sender email address (optional)"),
    html_message: Optional[str] = Field(default=None, description="HTML formatted email content (optional)"),
    cc_list: Optional[str] = Field(default=None, description="Comma-separated CC recipient addresses (optional)"),
    bcc_list: Optional[str] = Field(default=None, description="Comma-separated BCC recipient addresses (optional)"),
    compose_only: bool = Field(
        default=False,
        description="If True, opens Outlook compose window without sending immediately",
    ),
) -> str:
    """Send an email or open the compose window in Microsoft Outlook."""
    return await run_in_com_thread(
        _send_email_sync,
        subject=subject,
        message=message,
        from_email=from_email,
        recipient_list=recipient_list,
        html_message=html_message,
        cc_list=cc_list,
        bcc_list=bcc_list,
        compose_only=compose_only,
    )


@mcp.tool()
async def outlook(
    operation: Literal["list", "get", "send"] = Field(description="Operation to perform: 'list', 'get', or 'send'"),
    max_hours: int = Field(default=24, description="Lookback window in hours (for 'list')"),
    query: Optional[str] = Field(default=None, description="Subject filter query (for 'list')"),
    folder: str = Field(default="inbox", description="Folder name (for 'list')"),
    identifier: Optional[str] = Field(default=None, description="Email identifier/EntryID (for 'get')"),
    subject: Optional[str] = Field(default=None, description="Email subject (for 'send')"),
    message: Optional[str] = Field(default=None, description="Message body (for 'send')"),
    from_email: Optional[str] = Field(default=None, description="Sender email (for 'send')"),
    recipient_list: Optional[str] = Field(default=None, description="Recipients separated by comma (for 'send')"),
    html_message: Optional[str] = Field(default=None, description="HTML message body (for 'send')"),
    cc_list: Optional[str] = Field(default=None, description="CC recipients (for 'send')"),
    bcc_list: Optional[str] = Field(default=None, description="BCC recipients (for 'send')"),
    compose_only: bool = Field(default=False, description="Open compose window without sending (for 'send')"),
) -> Union[str, List[dict], dict]:
    """Unified Outlook tool for list, get, and send operations."""
    if operation == "list":
        return await outlook_list_emails(max_hours=max_hours, query=query, folder=folder)
    elif operation == "get":
        if not identifier:
            raise ValueError("'identifier' is required for get operation.")
        return await outlook_get_email(identifier=identifier)
    elif operation == "send":
        if not subject or not message or not recipient_list:
            raise ValueError("'subject', 'message', and 'recipient_list' are required for send operation.")
        return await outlook_send_email(
            subject=subject,
            message=message,
            recipient_list=recipient_list,
            from_email=from_email,
            html_message=html_message,
            cc_list=cc_list,
            bcc_list=bcc_list,
            compose_only=compose_only,
        )
    else:
        raise ValueError(f"Unknown operation: {operation}")


# ==============================================================================
# Server Entry Point
# ==============================================================================

if __name__ == "__main__":
    host = "127.0.0.1"
    port = 8002

    if hasattr(mcp, "run_sse"):
        mcp.run_sse(host=host, port=port)
    elif hasattr(mcp, "settings"):
        mcp.settings.host = host
        mcp.settings.port = port
        mcp.run(transport="sse")
    else:
        try:
            mcp.run(transport="sse", host=host, port=port)
        except TypeError:
            try:
                mcp.run(transport="sse", port=port)
            except TypeError:
                mcp.run(transport="sse")