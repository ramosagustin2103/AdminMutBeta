from django.core.management import BaseCommand
from creditos.models import *
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from admincu.funciones import armar_link, emisor_mail
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

class Command(BaseCommand):
	# Show this when the user types help
	help = "Enviar mails a socios"

	def handle(self, *args, **options):
		mails = Mail.objects.all()
		if mails:

			for m in mails:
				if m.liquidacion.confirmado and m.liquidacion.consorcio.mails:
					liquidacion = m.liquidacion
					socio = m.socio
					numero = liquidacion.formatoAfip()
					link_expensas = armar_link(reverse('socio:expensas'))
					html_string = render_to_string('creditos/mail.html', locals())
					p, creado = PdfSocio.objects.get_or_create(
							socio=socio,
							liquidacion=liquidacion
						)
					if creado:
						pdf_liq = liquidacion.hacer_pdf(socio)
						ruta = "{}_{}_{}.pdf".format(
								str(liquidacion.consorcio.abreviatura),
								str(liquidacion.formatoAfip()),
								str(socio.numero)
							)
						p.pdf = SimpleUploadedFile(ruta, pdf_liq, content_type='application/pdf')
						p.save()
					pdfs = [p.pdf]
					if liquidacion.automatico:
						cierre = liquidacion.cierre_set.all()[0]
						for r in cierre.reportes.all():
							pdfs.append(r.ubicacion)


					lista_mails = []
					usuarios = socio.usuarios.all()
					if usuarios:
						for usuario in usuarios:
							lista_mails.append(usuario.email)
					else:
						lista_mails.append(socio.mail)
					for receptor in lista_mails:
						if receptor:
							msg = EmailMultiAlternatives(
								subject="Nueva liquidacion de expensas",
								body="",
								from_email=emisor_mail(liquidacion.consorcio),
								to=[receptor],
							)

							msg.attach_alternative(html_string, "text/html")
							for pdf in pdfs:
								msg.attach_file(pdf.path)
							msg.send()
							mensaje = "{} - {} enviado con exito".format(m, usuario.email)
					self.stdout.write(mensaje)
				m.delete()

		else:
			self.stdout.write("No hay mails para enviar")