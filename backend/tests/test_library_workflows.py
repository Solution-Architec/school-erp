from datetime import date
import pytest
from pydantic import ValidationError

from backend.app.schemas import LibraryBookIn, LibraryLoanIn


def test_library_book_requires_title_and_positive_copy_count():
    book = LibraryBookIn(title="The Blue Umbrella", author="Ruskin Bond", total_copies=3)
    assert book.total_copies == 3
    with pytest.raises(ValidationError):
        LibraryBookIn(title="", total_copies=1)
    with pytest.raises(ValidationError):
        LibraryBookIn(title="A valid title", total_copies=0)


def test_library_loan_requires_valid_book_student_and_due_date():
    loan = LibraryLoanIn(book_id=4, student_id=12, due_date=date(2026, 11, 20))
    assert loan.book_id == 4
    assert loan.student_id == 12
    with pytest.raises(ValidationError):
        LibraryLoanIn(book_id=0, student_id=12, due_date=date(2026, 11, 20))
