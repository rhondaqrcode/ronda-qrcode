from datetime import date

from backend.app.services.billing_notification import should_send_billing_notice


def test_should_send_billing_notice_exactly_ten_days_before_due_date() -> None:
    assert should_send_billing_notice(
        due_date=date(2026, 6, 30),
        today=date(2026, 6, 20),
    )


def test_should_not_send_billing_notice_on_other_days() -> None:
    assert not should_send_billing_notice(
        due_date=date(2026, 6, 30),
        today=date(2026, 6, 19),
    )
