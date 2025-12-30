"""
Email Tasks

Celery tasks for sending emails asynchronously.
Uses Mailpit (local dev) or SMTP (production) for email delivery.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from src.core.celery_app import celery_app
from src.core.config import settings


@celery_app.task(name="send_verification_email", bind=True, max_retries=3)
def send_verification_email(self, email: str, token: str, user_name: str):
    """
    Send email verification email via SMTP.
    
    Email includes verification link that expires in 24 hours.
    Retries up to 3 times on failure with exponential backoff.
    
    Args:
        email: Recipient email address
        token: Verification token
        user_name: User's display name for personalization
        
    Raises:
        Exception: If email sending fails after retries
    """
    try:
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Verify your email address"
        msg["From"] = settings.SMTP_FROM_EMAIL
        msg["To"] = email
        
        # Plain text version
        text = f"""
        Welcome, {user_name}!
        
        Please verify your email address by visiting:
        {verification_url}
        
        This link expires in 24 hours.
        
        If you didn't create this account, please ignore this email.
        
        Best regards,
        Identity Management Team
        """
        
        # HTML version
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
              <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
              <p style="color: #999; font-size: 12px;">
                If you didn't create this account, please ignore this email.
              </p>
            </div>
          </body>
        </html>
        """
        
        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))
        
        # Send email via SMTP
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            # Note: Mailpit doesn't require authentication
            # Production SMTP would need: server.login(user, password)
            server.send_message(msg)
            
        return {"status": "sent", "email": email}
        
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(name="send_password_reset_email", bind=True, max_retries=3)
def send_password_reset_email(self, email: str, token: str):
    """
    Send password reset email via SMTP.
    
    Email includes reset link that expires in 1 hour.
    Retries up to 3 times on failure with exponential backoff.
    
    Args:
        email: Recipient email address
        token: Password reset token
        
    Raises:
        Exception: If email sending fails after retries
    """
    try:
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Reset your password"
        msg["From"] = settings.SMTP_FROM_EMAIL
        msg["To"] = email
        
        # Plain text version
        text = f"""
        Password Reset Request
        
        You requested to reset your password. Click the link below to proceed:
        {reset_url}
        
        This link expires in 1 hour.
        
        If you didn't request this, please ignore this email. Your password will remain unchanged.
        
        Best regards,
        Identity Management Team
        """
        
        # HTML version
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
              <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
              <p style="color: #999; font-size: 12px;">
                If you didn't request this, please ignore this email. Your password will remain unchanged.
              </p>
            </div>
          </body>
        </html>
        """
        
        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))
        
        # Send email via SMTP
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.send_message(msg)
            
        return {"status": "sent", "email": email}
        
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(name="send_guardian_notification_email", bind=True, max_retries=3)
def send_guardian_notification_email(self, email: str, minor_name: str, action: str):
    """
    Send guardian notification email for minor account actions.
    
    Future implementation for guardian management feature.
    
    Args:
        email: Guardian email address
        minor_name: Minor's display name
        action: Action that triggered notification
        
    Raises:
        Exception: If email sending fails after retries
    """
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Guardian Notification: {action}"
        msg["From"] = settings.SMTP_FROM_EMAIL
        msg["To"] = email
        
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
              <h2 style="color: #2563eb;">Guardian Notification</h2>
              <p>Action performed on {minor_name}'s account:</p>
              <p style="background-color: #f3f4f6; padding: 15px; border-radius: 5px;">
                <strong>{action}</strong>
              </p>
              <p style="color: #666; font-size: 14px;">
                This is an automated notification for guardian oversight.
              </p>
            </div>
          </body>
        </html>
        """
        
        msg.attach(MIMEText(html, "html"))
        
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.send_message(msg)
            
        return {"status": "sent", "email": email}
        
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)

