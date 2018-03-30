from __future__ import absolute_import

import mock
import os
import unittest

os.environ['CLAY_CONFIG'] = 'config.json'

from clay import config, mail
log = config.get_logger('clay.tests.mail')


class TestMail(unittest.TestCase):

    @mock.patch("smtplib.SMTP")
    def test_sendmail(self, mock_SMTP):
        mock_SMTP_instance = mock_SMTP.return_value

        mailto = 'fake@email.com'
        subject = 'This is a subject'
        message = 'This is a message'
        mail.sendmail(mailto, subject, message)

        args, kwargs = mock_SMTP_instance.sendmail.call_args
        from_header = config.get('smtp.from')
        self.assertEqual(from_header, args[0])
        self.assertIn(mailto, args[1])
        self.assertIn('To: %s' % mailto, args[2])
        self.assertIn('From: %s' % from_header, args[2])
        self.assertIn('Subject: %s' % subject, args[2])
        self.assertIn('Content-Type: text/html', args[2])
        self.assertEqual(len(mock_SMTP_instance.elho.call_args_list), 0)
        self.assertFalse(mock_SMTP_instance.starttls.called)

    @mock.patch("smtplib.SMTP")
    def test_sendmail_with_other_smtpconfig(self, mock_SMTP):
        mock_SMTP_instance = mock_SMTP.return_value

        mailto = 'otherfake@email.com'
        subject = 'This is another subject'
        message = 'This is another message'
        mail.sendmail(
            mailto,
            subject,
            message,
            smtpconfig=config.get('othersmtp'))

        args, kwargs = mock_SMTP_instance.sendmail.call_args
        from_header = config.get('othersmtp.from')
        self.assertEqual(from_header, args[0])
        self.assertIn(mailto, args[1])
        self.assertIn('To: %s' % mailto, args[2])
        self.assertIn('From: %s' % from_header, args[2])
        self.assertIn('Subject: %s' % subject, args[2])
        self.assertIn('Content-Type: text/html', args[2])

    @mock.patch('smtplib.SMTP')
    def test_sendmail_starttls(self, mock_SMTP):
        """Test that when use_starttls is true, elho and starttls are called."""
        mock_SMTP_instance = mock_SMTP.return_value

        mailto = 'otherfake@email.com'
        subject = 'This is another subject'
        message = 'This is another message'
        mail.sendmail(mailto, subject, message, use_starttls=True)

        self.assertEqual(len(mock_SMTP_instance.elho.call_args_list), 2)
        self.assertTrue(mock_SMTP_instance.starttls.called)

    @mock.patch('smtplib.SMTP')
    @mock.patch('email.mime.base.MIMEBase.set_payload')
    def test_sendmail_attachments(self, mock_set_payload, mock_SMTP):
        """Test that whens sarttls is true, elho and starttls are called."""

        mailto = 'otherfake@email.com'
        subject = 'This is another subject'
        message = 'This is another message'
        file_name = 'my_file_name.txt'
        file_content = 'this is the content'
        mail.sendmail(
            mailto,
            subject,
            message,
            attachments={file_name: file_content}
        )

        # set_payload should be called on the file content.
        self.assertIn(file_content, [call[0][0] for call in mock_set_payload.call_args_list])
