from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

from clay import config

log = config.get_logger('clay.mail')


def sendmail(mailto, subject, message):
    mailfrom = config.get('mail.from')

    msg = MIMEMultipart('alternative')
    msg['subject'] = subject
    msg['From'] = mailfrom
    msg['To'] = mailto
    text = MIMEText(message, 'html')
    msg.attach(text)

    smtp = smtplib.SMTP(config.get('smtp.host'), config.get('smtp.port'))
    smtp.login(config.get('smtp.username'), config.get('smtp.password'))
    smtp.sendmail(mailfrom, mailto, msg.as_string())
    smtp.quit()
    log.info('Sent email to %s (Subject: %s)' % (mailto, subject))
