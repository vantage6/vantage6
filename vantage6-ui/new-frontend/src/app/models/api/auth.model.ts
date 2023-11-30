export interface Login {
  access_token: string;
  refresh_token: string;
  user_url: string;
}

export interface SetupMFA {
  qr_uri: string;
  otp_secret: string;
}

export interface ChangePassword {
  msg: string;
}

export enum AuthResult {
  Success = 'success',
  Failure = 'failure',
  RedirectMFA = 'redirect_mfa'
}
