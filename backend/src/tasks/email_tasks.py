"""Celery tasks for sending emails asynchronously.

Uses Mailpit (local dev) or Mailgun SMTP (production).
"""

import smtplib
from contextlib import contextmanager
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from src.core.celery_app import celery_app
from src.core.config import settings


@contextmanager
def get_smtp_connection():
    """Create SMTP connection. Uses TLS + auth in production, plain SMTP locally."""
    server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
    try:
        if settings.SMTP_USE_TLS:
            server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        yield server
    finally:
        server.quit()


@celery_app.task(name="send_verification_email", bind=True, max_retries=3)
def send_verification_email(self, email: str, token: str, user_name: str):
    """Send email verification link (expires in 24 hours)."""
    try:
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
        api_verify_url = f"{settings.API_BASE_URL}/api/v1/auth/verify-email"
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Verify your email address"
        msg["From"] = settings.SMTP_FROM_EMAIL
        msg["To"] = email

        text = f"""
        Welcome, {user_name}!
        
        Please verify your email address by visiting:
        {verification_url}
        
        This link expires in 24 hours.
        
        --- API Testing (Development) ---
        Token: {token}
        
        curl -X POST {api_verify_url} \\
          -H "Content-Type: application/json" \\
          -d '{{"token": "{token}"}}'
        
        If you didn't create this account, please ignore this email.
        
        Best regards,
        Identity Management Team
        """
        
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
              <h2 style="color: #2563eb;">Welcome, {user_name}!</h2>
              <p>Please verify your email address by clicking the button below:</p>
              <div style="text-align: center; margin: 30px 0;">
                <a href="{verification_url}" 
                   style="background-color: #2563eb; color: white; padding: 12px 30px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                  Verify Email Address
                </a>
              </div>
              <p style="color: #666; font-size: 14px;">
                Or copy and paste this link into your browser:<br>
                <a href="{verification_url}">{verification_url}</a>
              </p>
              <p style="color: #666; font-size: 14px;">
                This link expires in 24 hours.
              </p>
              <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
              <div style="background-color: #f8fafc; padding: 15px; border-radius: 5px; margin: 15px 0;">
                <p style="color: #475569; font-size: 12px; margin: 0 0 10px 0;">
                  <strong>API Testing (Development Only)</strong>
                </p>
                <p style="color: #64748b; font-size: 11px; margin: 0 0 5px 0;">
                  Token: <code style="background: #e2e8f0; padding: 2px 6px; border-radius: 3px;">{token}</code>
                </p>
                <p style="color: #64748b; font-size: 11px; margin: 0;">
                  API: <code style="background: #e2e8f0; padding: 2px 6px; border-radius: 3px;">{api_verify_url}</code>
                </p>
              </div>
              <p style="color: #999; font-size: 12px;">
                If you didn't create this account, please ignore this email.
              </p>
            </div>
          </body>
        </html>
        """
        
        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))
        
        with get_smtp_connection() as server:
            server.send_message(msg)
            
        return {"status": "sent", "email": email}
        
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(name="send_password_reset_email", bind=True, max_retries=3)
def send_password_reset_email(self, email: str, token: str):
    """Send password reset link (expires in 1 hour)."""
    try:
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        api_reset_url = f"{settings.API_BASE_URL}/api/v1/auth/reset-password"
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Reset your password"
        msg["From"] = settings.SMTP_FROM_EMAIL
        msg["To"] = email
        
        text = f"""
        Password Reset Request
        
        You requested to reset your password. Click the link below to proceed:
        {reset_url}
        
        This link expires in 1 hour.
        
        --- API Testing (Development) ---
        Token: {token}
        
        curl -X POST {api_reset_url} \\
          -H "Content-Type: application/json" \\
          -d '{{"token": "{token}", "new_password": "YourNewPassword123!"}}'
        
        If you didn't request this, please ignore this email. Your password will remain unchanged.
        
        Best regards,
        Identity Management Team
        """
        
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
              <h2 style="color: #dc2626;">Password Reset Request</h2>
              <p>You requested to reset your password. Click the button below to proceed:</p>
              <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_url}" 
                   style="background-color: #dc2626; color: white; padding: 12px 30px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                  Reset Password
                </a>
              </div>
              <p style="color: #666; font-size: 14px;">
                Or copy and paste this link into your browser:<br>
                <a href="{reset_url}">{reset_url}</a>
              </p>
              <p style="color: #666; font-size: 14px;">
                This link expires in 1 hour.
              </p>
              <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
              <div style="background-color: #fef2f2; padding: 15px; border-radius: 5px; margin: 15px 0;">
                <p style="color: #991b1b; font-size: 12px; margin: 0 0 10px 0;">
                  <strong>API Testing (Development Only)</strong>
                </p>
                <p style="color: #b91c1c; font-size: 11px; margin: 0 0 5px 0;">
                  Token: <code style="background: #fee2e2; padding: 2px 6px; border-radius: 3px;">{token}</code>
                </p>
                <p style="color: #b91c1c; font-size: 11px; margin: 0;">
                  API: <code style="background: #fee2e2; padding: 2px 6px; border-radius: 3px;">{api_reset_url}</code>
                </p>
              </div>
              <p style="color: #999; font-size: 12px;">
                If you didn't request this, please ignore this email. Your password will remain unchanged.
              </p>
            </div>
          </body>
        </html>
        """
        
        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))
        
        with get_smtp_connection() as server:
            server.send_message(msg)
            
        return {"status": "sent", "email": email}

    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(name="send_restoration_email", bind=True, max_retries=3)
def send_restoration_email(self, email: str, token: str):
    """Send account restoration link (expires in 24 hours)."""
    try:
        restore_url = f"{settings.FRONTEND_URL}/restore-account/confirm?token={token}"
        api_restore_url = (
            f"{settings.API_BASE_URL}/api/v1/auth/restore-account/confirm"
        )

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Restore your account"
        msg["From"] = settings.SMTP_FROM_EMAIL
        msg["To"] = email

        text = f"""
        Account Restoration Request

        You requested to restore your deleted account. Click the link below to proceed:
        {restore_url}

        This link expires in 24 hours.

        You will be asked to set a new password during restoration.

        --- API Testing (Development) ---
        Token: {token}

        curl -X POST {api_restore_url} \\
          -H "Content-Type: application/json" \\
          -d '{{"token": "{token}", "new_password": "YourNewPassword123!"}}'

        If you didn't request this, please ignore this email.

        Best regards,
        Identity Management Team
        """

        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
              <h2 style="color: #059669;">Restore Your Account</h2>
              <p>You requested to restore your deleted account.
                 Click the button below to proceed:</p>
              <div style="text-align: center; margin: 30px 0;">
                <a href="{restore_url}"
                   style="background-color: #059669; color: white; padding: 12px 30px;
                          text-decoration: none; border-radius: 5px;
                          display: inline-block;">
                  Restore Account
                </a>
              </div>
              <p style="color: #666; font-size: 14px;">
                Or copy and paste this link into your browser:<br>
                <a href="{restore_url}">{restore_url}</a>
              </p>
              <p style="color: #666; font-size: 14px;">
                This link expires in 24 hours.
                You will be asked to set a new password.
              </p>
              <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
              <div style="background-color: #ecfdf5; padding: 15px;
                          border-radius: 5px; margin: 15px 0;">
                <p style="color: #065f46; font-size: 12px; margin: 0 0 10px 0;">
                  <strong>API Testing (Development Only)</strong>
                </p>
                <p style="color: #047857; font-size: 11px; margin: 0 0 5px 0;">
                  Token: <code style="background: #d1fae5; padding: 2px 6px;
                    border-radius: 3px;">{token}</code>
                </p>
                <p style="color: #047857; font-size: 11px; margin: 0;">
                  API: <code style="background: #d1fae5; padding: 2px 6px;
                    border-radius: 3px;">{api_restore_url}</code>
                </p>
              </div>
              <p style="color: #999; font-size: 12px;">
                If you didn't request this, please ignore this email.
              </p>
            </div>
          </body>
        </html>
        """

        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        with get_smtp_connection() as server:
            server.send_message(msg)

        return {"status": "sent", "email": email}

    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(name="send_rejection_email", bind=True, max_retries=3)
def send_rejection_email(
    self, email: str, user_name: str, context_name: str, rejection_reason: str
):
    """Send verification rejection notification with the reviewer's reason."""
    try:
        documents_url = f"{settings.FRONTEND_URL}/documents"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Verification request rejected"
        msg["From"] = settings.SMTP_FROM_EMAIL
        msg["To"] = email

        text = f"""
        Verification Request Rejected

        Hello {user_name},

        Your verification request for the context "{context_name}" has been rejected.

        Reason: {rejection_reason}

        You can upload a new document and try again at:
        {documents_url}

        If you believe this was an error, please contact support.

        Best regards,
        Identity Management Team
        """

        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
              <h2 style="color: #dc2626;">Verification Request Rejected</h2>
              <p>Hello {user_name},</p>
              <p>Your verification request for the context
                 <strong>{context_name}</strong> has been rejected.</p>
              <div style="background-color: #fef2f2; border-left: 4px solid #dc2626;
                          padding: 12px 16px; margin: 20px 0; border-radius: 4px;">
                <p style="margin: 0; color: #991b1b;">
                  <strong>Reason:</strong> {rejection_reason}
                </p>
              </div>
              <p>You can upload a new document and try again:</p>
              <div style="text-align: center; margin: 30px 0;">
                <a href="{documents_url}"
                   style="background-color: #dc2626; color: white; padding: 12px 30px;
                          text-decoration: none; border-radius: 5px;
                          display: inline-block;">
                  Upload New Document
                </a>
              </div>
              <p style="color: #666; font-size: 14px;">
                If you believe this was an error, please contact support.
              </p>
              <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
              <p style="color: #999; font-size: 12px;">
                This is an automated notification from the Identity Management System.
              </p>
            </div>
          </body>
        </html>
        """

        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        with get_smtp_connection() as server:
            server.send_message(msg)

        return {"status": "sent", "email": email}

    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(name="send_approval_email", bind=True, max_retries=3)
def send_approval_email(self, email: str, user_name: str, context_name: str):
    """Send verification approval notification. Account is promoted to verified."""
    try:
        contexts_url = f"{settings.FRONTEND_URL}/contexts"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Verification approved"
        msg["From"] = settings.SMTP_FROM_EMAIL
        msg["To"] = email

        text = f"""
        Verification Approved

        Hello {user_name},

        Your verification request for the context "{context_name}" has been approved.

        Your account has been promoted to verified status. The context is now
        active and ready to use.

        View your contexts at:
        {contexts_url}

        Best regards,
        Identity Management Team
        """

        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
              <h2 style="color: #059669;">Verification Approved</h2>
              <p>Hello {user_name},</p>
              <p>Your verification request for the context
                 <strong>{context_name}</strong> has been approved.</p>
              <div style="background-color: #ecfdf5; border-left: 4px solid #059669;
                          padding: 12px 16px; margin: 20px 0; border-radius: 4px;">
                <p style="margin: 0; color: #065f46;">
                  Your account has been promoted to <strong>verified</strong> status.
                  The context is now active and ready to use.
                </p>
              </div>
              <div style="text-align: center; margin: 30px 0;">
                <a href="{contexts_url}"
                   style="background-color: #059669; color: white; padding: 12px 30px;
                          text-decoration: none; border-radius: 5px;
                          display: inline-block;">
                  View Your Contexts
                </a>
              </div>
              <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
              <p style="color: #999; font-size: 12px;">
                This is an automated notification from the Identity Management System.
              </p>
            </div>
          </body>
        </html>
        """

        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        with get_smtp_connection() as server:
            server.send_message(msg)

        return {"status": "sent", "email": email}

    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(name="send_document_expiry_email", bind=True, max_retries=3)
def send_document_expiry_email(
    self,
    email: str,
    user_name: str,
    context_names: list,
    expiry_date: str,
):
    """Send document expiry notification listing deactivated contexts."""
    try:
        documents_url = f"{settings.FRONTEND_URL}/documents"
        contexts_list = ", ".join(context_names)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Verification document expired"
        msg["From"] = settings.SMTP_FROM_EMAIL
        msg["To"] = email

        text = f"""
        Verification Document Expired

        Hello {user_name},

        Your verification document expired on {expiry_date}.

        The following context profiles have been deactivated:
        {contexts_list}

        To reactivate these contexts, upload a new valid document at:
        {documents_url}

        Best regards,
        Identity Management Team
        """

        contexts_html_items = "".join(
            f"<li>{name}</li>" for name in context_names
        )
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
              <h2 style="color: #d97706;">Verification Document Expired</h2>
              <p>Hello {user_name},</p>
              <p>Your verification document expired on
                 <strong>{expiry_date}</strong>.</p>
              <div style="background-color: #fffbeb; border-left: 4px solid #d97706;
                          padding: 12px 16px; margin: 20px 0; border-radius: 4px;">
                <p style="margin: 0 0 8px 0; color: #92400e;">
                  <strong>Deactivated contexts:</strong>
                </p>
                <ul style="margin: 0; padding-left: 20px; color: #92400e;">
                  {contexts_html_items}
                </ul>
              </div>
              <p>To reactivate these contexts, upload a new valid document:</p>
              <div style="text-align: center; margin: 30px 0;">
                <a href="{documents_url}"
                   style="background-color: #d97706; color: white; padding: 12px 30px;
                          text-decoration: none; border-radius: 5px;
                          display: inline-block;">
                  Upload New Document
                </a>
              </div>
              <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
              <p style="color: #999; font-size: 12px;">
                This is an automated notification from the Identity Management System.
              </p>
            </div>
          </body>
        </html>
        """

        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        with get_smtp_connection() as server:
            server.send_message(msg)

        return {"status": "sent", "email": email}

    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
