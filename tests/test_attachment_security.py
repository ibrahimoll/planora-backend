import pytest
from fastapi import HTTPException

from app.services.attachment_service import (
    clean_original_file_name,
    get_stored_file_name,
)


def test_upload_file_name_uses_basename_only():
    assert clean_original_file_name(r"C:\fakepath\plan.pdf") == "plan.pdf"
    assert clean_original_file_name("../plan.pdf") == "plan.pdf"


def test_upload_file_name_rejects_blank_name():
    with pytest.raises(HTTPException):
        clean_original_file_name("   ")


def test_stored_file_name_rejects_path_traversal():
    assert get_stored_file_name("/uploads/attachments/report.pdf") == "report.pdf"
    assert get_stored_file_name("/uploads/attachments/../secret.txt") is None
    assert get_stored_file_name("/uploads/attachments/..\\secret.txt") is None
