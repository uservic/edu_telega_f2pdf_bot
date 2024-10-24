import smtplib

from email.message import EmailMessage
from io import BytesIO


class EmailSender:
    def __init__(self, conn_config: 'MailServerConnectionConfig'):
        self.smtp_socket = conn_config.smtp_socket
        self.from_addr = conn_config.from_addr
        self.login = conn_config.login
        self.passw = conn_config.passw

    async def try_send(self, mail_data: 'MailMessageData'):
        mail_data.from_addr = self.from_addr
        m = self.create_msg(mail_data)

        self.attach_pdf(m, mail_data)
        serv = smtplib.SMTP_SSL(self.smtp_socket)
        try:
            serv.login(self.login, self.passw)
            serv.send_message(m)
        finally:
            serv.quit()

    @staticmethod
    def create_msg(data: 'MailMessageData') -> EmailMessage:
        msg = EmailMessage()

        msg.set_content(data.text)
        msg['Subject'] = data.subject
        msg['From'] = data.from_addr
        msg['To'] = data.to_addr

        return msg

    @staticmethod
    def attach_pdf(m: 'EmailMessage', msg_data: 'MailMessageData'):
        bytes_obj = msg_data.data_to_send
        m.add_attachment(bytes_obj.getvalue(),
                         maintype='application/pdf',
                         subtype='pdf',
                         filename=msg_data.result_file_name)


class MailMessageData:
    def __init__(self, to_addr: str, data_to_send: BytesIO, from_addr=None,
                 main_text='Sample text', subject='Some email', attach=None, result_file_name=None):
        self.to_addr = to_addr.strip()
        self.data_to_send = data_to_send
        self.from_addr = from_addr
        self.text = main_text
        self.subject = subject
        self.attach = attach
        self.result_file_name = result_file_name


class MailServerConnectionConfig:
    def __init__(self, smtp_socket=None, from_addr=None, login=None, passw=None):
        self.smtp_socket = smtp_socket
        self.from_addr = from_addr
        self.login = login
        self.passw = passw
