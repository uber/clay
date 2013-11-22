from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

from clay import config

log = config.get_logger('clay.mail')


def _string_or_list(obj):
    '''
    If obj is a string, it's converted to a single element list, otherwise
    it's just returned as-is under the assumption that it's already a list. No
    further type checking is performed.
    '''

    if isinstance(obj, basestring):
        return [obj]
    else:
        return obj


def sendmail(mailto, subject, message, subtype='html', charset='utf-8', **headers):
    '''
    Send an email to the given address. Additional SMTP headers may be specified
    as keyword arguments.
    '''

    # mailto arg is explicit to ensure that it's always set, but it's processed
    # mostly the same way as all other headers
    headers['To'] = _string_or_list(mailto)

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    for key, value in headers.iteritems():
        for val in _string_or_list(value):
            msg.add_header(key, val)

    text = MIMEText(message, subtype, charset)
    msg.attach(text)

    if not 'From' in msg:
        # we support both smtp.from and mail.from for legacy reasons
        # smtp.from is the correct usage.
        msg['From'] = config.get('smtp.from') or config.get('mail.from')
    mailfrom = msg['From']
    assert isinstance(mailfrom, basestring)

    recipients = []
    for toheader in ('To', 'CC', 'BCC'):
        recipients += msg.get_all(toheader, [])
    if 'BCC' in msg:
        del msg['BCC']

    smtp = smtplib.SMTP(config.get('smtp.host'), config.get('smtp.port'))
    if config.get('smtp.username') and config.get('smtp.password'):
        smtp.login(config.get('smtp.username'), config.get('smtp.password'))
    smtp.sendmail(mailfrom, recipients, msg.as_string())
    smtp.quit()
    log.info('Sent email to %s (Subject: %s)', recipients, subject)
