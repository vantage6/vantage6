export interface LoginForm {
  username: string;
  password: string;
  mfaCode?: string;
}

export interface PasswordResetTokenForm {
  resetToken: string;
  password: string;
  passwordRepeat: string;
}

export interface MFAResetTokenForm {
  resetToken: string;
}

export interface LostPasswordForm {
  email?: string;
  username?: string;
}
