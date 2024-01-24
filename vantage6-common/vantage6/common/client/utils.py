import qrcode


def print_qr_code(json_data: dict) -> None:
    """
    Print the QR code for 2fa with additional info of how to use it.

    This function should work in any terminal or Python scripting environment.
    Therefore, all is printed regardless of log level

    Parameters
    ----------
    json_data: dict
        A dictionary containing the secret and URI to generate the QR code
    """
    print(
        "This server has obligatory two-factor authentication. Please scan "
        "the QR code below with your favorite authenticator app (we "
        "recommend the LastPass or Google Authenticator)."
    )
    print("After you have authenticated, please log in again.")
    show_qr_code_image(json_data.get("qr_uri"))
    print(
        "If you are having trouble scanning the QR code, you can also add "
        "the following code manually to your authenticator app: "
        f"{json_data.get('otp_secret')}"
    )


def show_qr_code_image(qr_uri: str) -> None:
    """
    Print a QR code image to the user's python enviroment

    Parameters
    ----------
    qr_uri: str
        An OTP-auth URI used to generate the QR code
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_uri)
    qr.make(fit=True)
    qr.print_ascii()
