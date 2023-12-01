export interface LoginForm {
  username: string;
  password: string;
  mfaCode?: string;
}

export interface ResetTokenForm {
  resetToken: string;
}
