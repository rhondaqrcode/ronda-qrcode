from backend.app.services.billing_notification import run_billing_notice_check


def main() -> None:
    sent = run_billing_notice_check()
    if sent:
        print("Aviso de cobranca enviado.")
    else:
        print("Nenhum aviso enviado hoje.")


if __name__ == "__main__":
    main()
