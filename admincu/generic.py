from django.views import generic
from django.core.paginator import Paginator
from .funciones import consorcio



class OrderQS(generic.ListView):
	filterset_class = None

	def get_queryset(self, **kwargs):
		datos = self.model.objects.filter(consorcio=consorcio(self.request), **kwargs).order_by('-id')
		self.filter = self.filterset_class(self.request.GET, queryset=datos)
		return self.filter.qs

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['filter'] = self.filter
		datos = self.filter.qs
		if len(self.request.GET) == 0 or self.request.GET.get('page'):
			paginador = Paginator(datos, self.paginate_by)
			pagina = self.request.GET.get('page')
			context['lista'] = paginador.get_page(pagina)
		else:
			context['is_paginated'] = False
			context['lista'] = datos

		return context
