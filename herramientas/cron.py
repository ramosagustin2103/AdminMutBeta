from django.db import transaction
from mailer.engine import send_all
from mailer.models import *

def send_mail():
	"""
		Envio de mails de mailer
	"""
	send_all()

def retry_deferred():
	count = Message.objects.retry_deferred()


def purge_mail_log():
	days = 10
	count = MessageLog.objects.purge_old_entries(days)