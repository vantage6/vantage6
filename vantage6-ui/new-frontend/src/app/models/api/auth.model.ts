export interface Login {
  access_token: string;
  refresh_token: string;
  user_url: string;
}

export interface LoginSubmit {
  username: string;
  password: string;
  mfa_code?: string;
}

export interface SetupMFA {
  qr_uri: string;
  otp_secret: string;
}

export interface MFARecover {
  msg: string;
}

export interface ChangePassword {
  msg: string;
}

export enum AuthResult {
  Success = 'success',
  Failure = 'failure',
  SetupMFA = 'SetupMFA',
  MFACode = 'MFACode'
}
