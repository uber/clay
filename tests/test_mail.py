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
