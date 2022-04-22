from .models import *

def borrar_op_no_confirmadas(usuario):
	ops = OP.objects.filter(usuario=usuario, confirmado=False).delete()

def borrar_deudas_no_confirmadas(usuario):
	deudas = Deuda.objects.filter(usuario=usuario, confirmado=False).delete()

